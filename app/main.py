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


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # your frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
Base.metadata.create_all(bind=engine)
app.include_router(auth.router)
app.include_router(dashboard.router)
@app.get("/")
def root():
    print("ROOT ENDPOINT HIT")
    return {"message": "Habit Tracker API is running"}

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
    today = date.today()
    logs = db.query(HabitLog).filter(
        HabitLog.user_id == current_user.id,
        HabitLog.completed_at >= datetime.combine(today,datetime.min.time()),
        HabitLog.completed_at <= datetime.combine(today,datetime.max.time())
    ).all()

    return logs
@app.post("/logs")
def create_log(
    logs: schemas.HabitLogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) 
):
    return crud.create_log(db, logs, user_id=current_user.id)
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
@app.get("/streak",response_model = schemas.StreakResponse)
def get_streak(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
    
):
    streak =  crud.get_streak(db,current_user.id)
    if not streak:
        raise HTTPException(status_code=404, detail="Habit not found")

    return streak

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
@app.get("/habits/progress")
def daily_progress(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    progress = crud.get_momentum(db,current_user.id)
    return progress

@app.get("/habits/recent-completed", response_model=list[schemas.RecentCompletedHabit])
def get_recent_completed_habits(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return crud.get_recent_completed_habits(db, current_user.id, limit)

@app.get("/heatmap")
def get_heatmap_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return crud.get_heatmap_data(db, current_user.id)


