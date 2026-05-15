from fastapi import FastAPI, Depends,HTTPException
from sqlalchemy.orm import Session
from app.routes import dashboard
from app.database import engine, get_db, Base
from app import models,schemas,crud
from app.routes import auth
from app.core.security import get_current_user
from app.models import User
from fastapi.middleware.cors import CORSMiddleware
from app.models import HabitLog
from datetime import datetime, date
from sqlalchemy import inspect, text
import os



app = FastAPI()

default_origins = [
    "http://localhost:5173",  # local dev
    "http://127.0.0.1:5173",  # local dev (127 host)
    "https://habit-frontend-3rz4-c9nniy5mg.vercel.app",  # your Vercel app
]
origins = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", ",".join(default_origins)).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.vercel\.app|http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
Base.metadata.create_all(bind=engine)


def ensure_points_column():
    inspector = inspect(engine)
    habit_columns = {column["name"] for column in inspector.get_columns("habits")}
    user_columns = {column["name"] for column in inspector.get_columns("users")}

    if "points" not in habit_columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE habits ADD COLUMN points INTEGER DEFAULT 10")
            )

    if "journey_start_date" not in user_columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE users ADD COLUMN journey_start_date DATE")
            )

    if "time_block" not in habit_columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE habits ADD COLUMN time_block VARCHAR DEFAULT 'default'")
            )

    if "routine_id" not in habit_columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE habits ADD COLUMN routine_id INTEGER")
            )


ensure_points_column()
app.include_router(auth.router)
app.include_router(dashboard.router)
@app.get("/")
def root():
    print("ROOT ENDPOINT HIT")
    return {"message": "Habit Tracker API is running"}

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Diagnostic endpoint to verify database connectivity and type."""
    from app.database import SQLALCHEMY_DATABASE_URL
    is_sqlite = SQLALCHEMY_DATABASE_URL.startswith("sqlite")
    user_count = db.query(User).count()
    return {
        "status": "ok",
        "database_type": "SQLite ⚠️ (ephemeral — data lost on restart!)" if is_sqlite else "PostgreSQL ✅ (persistent)",
        "user_count": user_count,
        "warning": "SQLite on Render = data loss on every restart/deploy!" if is_sqlite else None,
    }

@app.post("/habits")
def create_habit(
    habit: schemas.HabitCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    print(habit.dict())
    return crud.create_habit(db, habit, user_id=current_user.id)


@app.get("/habits",response_model = list[schemas.HabitResponse])
def get_habits(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) 
):
    return crud.get_habits(db, user_id=current_user.id)



@app.get("/logs")
def get_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    today = crud.today_in_app_timezone()
    start_of_day, end_of_day = crud.local_day_utc_bounds(today)
    logs = db.query(HabitLog).filter(
        HabitLog.user_id == current_user.id,
        HabitLog.completed_at >= start_of_day,
        HabitLog.completed_at < end_of_day
    ).all()

    return logs
@app.post("/logs")
def create_log(
    logs: schemas.HabitLogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) 
):
    return crud.create_log(db, logs, user_id=current_user.id)


# Sub-habit endpoints
@app.post("/habits/{habit_id}/subhabits", response_model=schemas.SubHabitResponse)
def add_sub_habit(
    habit_id: int,
    sub_habit: schemas.SubHabitCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify habit belongs to user
    habit = db.query(models.Habit).filter(models.Habit.id == habit_id, models.Habit.user_id == current_user.id).first()
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found")
    return crud.create_sub_habit(db, sub_habit, habit_id)

@app.post("/subhabits/{sub_habit_id}/toggle", response_model=schemas.SubHabitResponse)
def toggle_sub_habit(
    sub_habit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sub = db.query(models.SubHabit).join(models.Habit).filter(
        models.SubHabit.id == sub_habit_id,
        models.Habit.user_id == current_user.id
    ).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Sub-habit not found")
    return crud.toggle_sub_habit(db, sub_habit_id)

@app.delete("/subhabits/{sub_habit_id}")
def delete_sub_habit(
    sub_habit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sub = db.query(models.SubHabit).join(models.Habit).filter(
        models.SubHabit.id == sub_habit_id,
        models.Habit.user_id == current_user.id
    ).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Sub-habit not found")
    crud.delete_sub_habit(db, sub_habit_id)
    return {"message": "Sub-habit deleted"}


@app.get("/habits/recent-completed", response_model=list[schemas.RecentCompletedHabit])
def get_recent_completed_habits(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return crud.get_recent_completed_habits(db, current_user.id, limit)
@app.get("/habits/progress")
def daily_progress(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    progress = crud.get_momentum(db,current_user.id)
    return progress
@app.patch("/habits/{habit_id}")
def update_habit(
    habit_id: int,
    update_data: schemas.HabitUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    updated_habit = crud.update_habit(db, habit_id, update_data, current_user.id)
    if not updated_habit:
        raise HTTPException(status_code=404, detail="Habit not found")

    return updated_habit
@app.delete("/habits/{habit_id}")
def delete_habit(
    habit_id:int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    deleted_habit = crud.delete_habit(db,habit_id,current_user.id)
    if not deleted_habit:
        raise HTTPException(status_code=404, detail="Habit not found")

    return {"message": "Habit deleted successfully"}
@app.get("/heatmap")
def get_heatmap_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return crud.get_heatmap_data(db, current_user.id)
@app.post("/routines", response_model=schemas.RoutineResponse)
def post_routine(
    routine: schemas.RoutineCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return crud.create_routine(
        db=db,
        user_id=current_user.id,
        routine_data=routine
    )
@app.get(
    "/routines",
    response_model=list[schemas.RoutineResponse]
)
def get_routines(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return crud.get_routines(
        db=db,
        user_id=current_user.id
    )
@app.get("/routines/{routine_id}")
def get_routine_detail(
    routine_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return crud.get_routine_detail(
        db,
        routine_id,
        current_user.id
    )

@app.delete("/routines/{routine_id}")
def delete_routine(
    routine_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    deleted = crud.delete_routine(db, routine_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Routine not found")
    return {"message": "Routine and all its habits deleted successfully"}
