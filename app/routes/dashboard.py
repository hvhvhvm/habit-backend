from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import DashboardResponse, StreakResponse ,HabitCreate
from app.core.security import get_current_user
from datetime import datetime, timedelta, date, timezone   
from app.models import Habit,HabitLog
from datetime import date, timedelta
from sqlalchemy import func
from app.crud import (
    get_dashboard_data, 
    get_last_7_days_data, 
    get_heatmap_data, 
    get_category_summary, 
    get_global_streak,
    get_habits,
    get_habit_progress_snapshot,
    is_habit_due_on_day,
    today_in_app_timezone
)
from app.models import User
from datetime import date


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/", response_model=DashboardResponse)
def get_dashboard(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    
    data = get_dashboard_data(db, current_user.id)

    return data
    
@router.get("/habits/{habit_id}/test")
def test_habit(habit_id: int, db: Session = Depends(get_db)):
    data = get_last_7_days_data(db, habit_id)
    return data

@router.get("/category/{category_name}")
def get_category_routine_summary(
    category_name: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return get_category_summary(db, current_user.id, category_name)

@router.get("/my-habits")
def get_my_habits(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_habits(db, current_user.id)
@router.get("/heatmap/")
def get_heatmap(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
    
):
    return get_heatmap_data(db,current_user.id)
@router.get("/streak",response_model=StreakResponse)
def get_streak_api(db:Session = Depends(get_db),current_user = Depends(get_current_user)):
    return get_global_streak(db,current_user.id,today_in_app_timezone())

@router.get("/journey")
def get_journey(
    current_user: User = Depends(get_current_user)
):
    return {
        "started": current_user.journey_start_date is not None,
        "start_date": str(current_user.journey_start_date) if current_user.journey_start_date else None
    }

@router.post("/journey/start")
def start_journey(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.journey_start_date is None:
        current_user.journey_start_date = today_in_app_timezone()
        db.commit()
        db.refresh(current_user)

    return {
        "started": True,
        "start_date": str(current_user.journey_start_date)
    }

@router.post("/habits")
def create_habit(
    habit: HabitCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    new_habit = Habit(
        title=habit.title,
        category=habit.category,
        user_id=current_user.id
    )

    db.add(new_habit)
    db.commit()
    db.refresh(new_habit)

    return new_habit




@router.get("/progress-history/")
async def get_progress_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    days: int = Query(90, ge=1, le=365),
):
    if current_user.journey_start_date is None:
        return {
            "journey_started": False,
            "journey_start_date": None,
            "days": []
        }

    today = today_in_app_timezone()
    start_date = current_user.journey_start_date
    window_start = max(start_date, today - timedelta(days=days - 1))
    result = []
    previous_completed_count = 0

    previous_day = window_start - timedelta(days=1)
    previous_habits = db.query(Habit).filter(
        Habit.user_id == current_user.id,
        func.date(Habit.created_at) <= previous_day
    ).all()
    previous_due_habits = [
        habit
        for habit in previous_habits
        if is_habit_due_on_day(habit, previous_day)
    ]
    for habit in previous_due_habits:
        progress = get_habit_progress_snapshot(
            db,
            habit,
            current_user.id,
            previous_day
        )
        if progress["completed"]:
            previous_completed_count += 1

    day_count = (today - window_start).days + 1

    for i in range(day_count):
        day = window_start + timedelta(days=i)

        active_habits = db.query(Habit).filter(
            Habit.user_id == current_user.id,
            func.date(Habit.created_at) <= day
        ).all()
        due_habits = [
            habit
            for habit in active_habits
            if is_habit_due_on_day(habit, day)
        ]

        due_habit_count = len(due_habits)

        if due_habit_count == 0:
            result.append({
                "date": str(day),
                "completion_percent": 0,
                "completed_habits": 0,
                "total_habits": 0,
                "streak_alive": False,
                "recovered": False,
            })
            previous_completed_count = 0
            continue

        progress_total = 0
        completed_count = 0

        for habit in due_habits:
            progress = get_habit_progress_snapshot(
                db,
                habit,
                current_user.id,
                day
            )
            progress_total += progress["progress_percent"]
            if progress["completed"]:
                completed_count += 1

        completion_percent = round(progress_total / due_habit_count)
        streak_alive = completed_count > 0
        recovered = previous_completed_count == 0 and completed_count > 0

        result.append({
            "date": str(day),
            "completion_percent": completion_percent,
            "completed_habits": completed_count,
            "total_habits": due_habit_count,
            "streak_alive": streak_alive,
            "recovered": recovered,
        })
        previous_completed_count = completed_count

    return {
        "journey_started": True,
        "journey_start_date": str(start_date),
        "days": result
    }
