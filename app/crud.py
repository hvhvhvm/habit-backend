from sqlalchemy.orm import Session
from app.models import User,Habit,HabitLog,SubHabit
from app.schemas import HabitCreate,HabitLogCreate,HabitUpdate,SubHabitCreate
from datetime import datetime, date, timedelta
from sqlalchemy import func
from datetime import datetime, timedelta,date,timezone
from collections import defaultdict
from typing import Dict, Any


def get_effective_target_value(habit: Habit) -> int:
    if habit.is_session and habit.total_sessions:
        return habit.total_sessions

    return habit.target_value if habit.target_value else 1


def normalize_points(points: int | None) -> int:
    if points is None:
        return 10

    return max(int(points), 0)


def is_habit_due_on_day(habit: Habit, target_date: date) -> bool:
    repeat_type = (habit.repeat or "daily").strip().lower()

    if repeat_type == "custom":
        weekday = target_date.strftime("%a").lower()[:3]
        habit_days = [
            str(day).strip().lower()[:3]
            for day in (habit.days or [])
            if str(day).strip()
        ]
        return weekday in habit_days

    if repeat_type == "today":
        if not habit.created_at:
            return False
        return habit.created_at.date() == target_date

    return True


def get_habit_progress_snapshot(
    db: Session,
    habit: Habit,
    user_id: int,
    target_date: date
):

    effective_target_value = get_effective_target_value(habit)
    completed_value = db.query(func.sum(HabitLog.value_completed)).filter(
        HabitLog.habit_id == habit.id,
        HabitLog.user_id == user_id,
        func.date(HabitLog.completed_at) == target_date  
    ).scalar() or 0
    is_due = is_habit_due_on_day(habit, target_date)

    if effective_target_value > 0:
        progress_percent = min(int((completed_value / effective_target_value) * 100), 100)
    else:
        progress_percent = 0

    remaining_value = max(effective_target_value - completed_value, 0)

    return {
        "effective_target_value": effective_target_value,
        "completed_value": completed_value,
        "progress_percent": progress_percent,
        "remaining_value": remaining_value,
        "is_due": is_due,
        "completed": is_due and effective_target_value > 0 and completed_value >= effective_target_value
    }


def create_habit(db: Session,habit: HabitCreate, user_id: int):
    habit_data = habit.dict()
    habit_data["points"] = normalize_points(habit_data.get("points"))
    new_habit = Habit(
    **habit_data,
    user_id=user_id
    )
    db.add(new_habit)
    db.commit()
    db.refresh(new_habit)
    return new_habit
def update_habit(db: Session,habit_id: int,update_data: HabitUpdate,user_id: int):
    habit = db.query(Habit).filter(
        Habit.id == habit_id,
        Habit.user_id == user_id
    ).first()
    if not habit:
        return None
    update_dict = update_data.dict(exclude_unset=True)
    if "points" in update_dict:
        update_dict["points"] = normalize_points(update_dict["points"])
    for field, value in update_dict.items():
        setattr(habit, field, value)
    db.commit()
    db.refresh(habit)

    return habit
def delete_habit(db: Session,habit_id:int,user_id: int):
    habit = db.query(Habit).filter(
        Habit.id == habit_id,
        Habit.user_id == user_id
    ).first()
    if not habit:
        return None
    db.delete(habit)
    db.commit()
    return habit

def get_habits(db: Session, user_id: int):
    habits = db.query(Habit).filter(Habit.user_id == user_id).all()
    today = date.today()
    result = []

    for habit in habits:
        progress_snapshot = get_habit_progress_snapshot(db, habit, user_id, today)
        
        # Reset sub-habits if they were completed before today
        for sub in habit.sub_habits:
            if sub.completed_today and sub.last_completed_at and sub.last_completed_at.date() < today:
                sub.completed_today = False
                db.add(sub)

        result.append({
            "id": habit.id,
            "title": habit.title,
            "target_type": habit.target_type,
            "target_value": habit.target_value,
            "effective_target_value": progress_snapshot["effective_target_value"],
            "category": habit.category,
            "points": normalize_points(habit.points),
            "repeat": habit.repeat,        
            "days": habit.days,            
            "scheduled_time": habit.scheduled_time,
            "is_due_today": progress_snapshot["is_due"],
            "completed_today": progress_snapshot["completed"],
            "completed_today_value": progress_snapshot["completed_value"],
            "progress_percent": progress_snapshot["progress_percent"],
            "remaining_value": progress_snapshot["remaining_value"],
            "is_session": habit.is_session,
            "focus_time": habit.focus_time,
            "break_time": habit.break_time,
            "total_sessions": habit.total_sessions,
            "sub_habits": habit.sub_habits
        })
    db.commit()

    return result
def create_log(db: Session, log_data : HabitLogCreate,user_id:int):
    log = HabitLog(
        habit_id = log_data.habit_id,
        value_completed = log_data.value_completed,
        user_id = user_id 
    )
    print("LOG VALUE:", log_data.value_completed)
    db.add(log)
    db.commit()
    db.refresh(log)
    return log
def get_daily_progress(db: Session,user_id:int,target_date: date):
    habits = db.query(Habit).filter(Habit.user_id == user_id).all()
    if not habits:
        return {
            "daily_progress": 0,
            "total_habits": 0,
            "completed_habits": 0
        }

    total_progress = 0
    due_habit_count = 0
    completed_habits = 0

    for habit in habits:
        progress_snapshot = get_habit_progress_snapshot(db, habit, user_id, target_date)
        if not progress_snapshot["is_due"]:
            continue

        total_progress += progress_snapshot["progress_percent"]
        due_habit_count += 1

        if progress_snapshot["completed"]:
            completed_habits += 1

    daily_progress = total_progress / due_habit_count if due_habit_count else 0

    return {
        "daily_progress": round(daily_progress, 2),
        "total_habits": due_habit_count,
        "completed_habits": completed_habits
    }
def get_heatmap_data(db: Session, user_id: int, days: int = 365):
    """Get daily progress data for heatmap visualization"""
    today = date.today()
    
    # Calculate start date to align with Monday
    # today.weekday() returns 0 for Monday, 6 for Sunday
    # We want to go back 'days' days, and then further back to the nearest Monday
    start_date = today - timedelta(days=days - 1)
    monday_offset = start_date.weekday()
    start_date = start_date - timedelta(days=monday_offset)
    
    num_days = (today - start_date).days + 1
    
    heatmap_data = []
    for i in range(num_days):
        check_date = start_date + timedelta(days=i)
        progress_data = get_daily_progress(db, user_id, check_date)
        
        heatmap_data.append({
            "date": check_date.isoformat(),
            "count": progress_data["daily_progress"],
            "completed_habits": progress_data["completed_habits"],
            "total_habits": progress_data["total_habits"]
        })
    
    return heatmap_data

def get_momentum(db: Session,user_id: int):
    today = date.today()
    yesterday = today - timedelta(days=1)
    two_days_ago = today - timedelta(days=2)
    
    today_progress = get_daily_progress(db,user_id,today)["daily_progress"]
    yesterday_progress = get_daily_progress(db,user_id,yesterday)["daily_progress"]
    two_days_progress = get_daily_progress(db,user_id,two_days_ago)["daily_progress"]
    
    momentum_score = (
        today_progress * 0.5 + 
        yesterday_progress * 0.3 +
        two_days_progress * 0.2
    )

    delta = today_progress - yesterday_progress
    window_average = (
        today_progress + yesterday_progress + two_days_progress
    ) / 3

    if momentum_score >= 75:
        state = "RISING"
    elif momentum_score >= 45:
        state = "STEADY"
    else:
        state = "RESET"

    if today_progress >= 85:
        if delta >= 10:
            message = "Excellent push today. You are accelerating."
        else:
            message = "Strong day. Keep the momentum warm and finish clean."
    elif today_progress >= 55:
        if delta >= 10:
            message = "Nice rebound today. You are moving in the right direction."
        elif state == "RISING":
            message = "Momentum is healthy. One more win today will lock it in."
        else:
            message = "Solid progress today. Finish one more habit to lift the day."
    elif today_progress > 0:
        if state == "RISING":
            message = "Recent momentum is still on your side. A small win keeps it alive."
        elif delta >= 0:
            message = "You are back in motion. One focused habit can turn today around."
        else:
            message = "Today is lighter than yesterday. Start with the easiest habit first."
    else:
        if momentum_score >= 70:
            message = "You built momentum recently. Do not let today stay empty."
        elif yesterday_progress >= 50:
            message = "Yesterday had energy. One quick habit today keeps the chain alive."
        else:
            message = "Today can be your reset. One small completion is enough to restart."
        
    return{
        "momentum_score": round(momentum_score,2),
        "momentum_state": state,
        "message": message,
        "today_progress": round(today_progress,2),
        "yesterday_progress": round(yesterday_progress,2),
        "delta": round(delta,2),
        "window_average": round(window_average,2)
    }
def get_last_7_days_data(db, habit_id):
    today = date.today()
    start_date = today - timedelta(days=6)
    habit = db.query(Habit).filter(Habit.id == habit_id).first()

    logs = (
        db.query(
            func.date(HabitLog.completed_at).label("day"),
            func.sum(HabitLog.value_completed).label("total")
        )
        .filter(HabitLog.habit_id == habit_id)
        .filter(HabitLog.completed_at >= start_date)
        .group_by(func.date(HabitLog.completed_at))
        .all()
    )
    day_map = {str(day): total for day, total in logs}
    week_data = []

    for i in range(7):
        date = start_date + timedelta(days=i)
        key = str(date)

        week_data.append({
            "date": key,
            "value": day_map.get(key, 0)
        })
    completed_days = 0

    for day in week_data:
        if day["value"] >= habit.target:
            completed_days += 1

    consistency = (completed_days / 7) * 100
    return {
        "week": week_data,
        "consistency": consistency
    }
from collections import defaultdict
from datetime import date

def get_dashboard_data(db: Session, user_id: int):
    habits = db.query(Habit).filter(Habit.user_id == user_id).all()
    total_possible_points = 0 

    today_progress_data = get_daily_progress(db, user_id, date.today())
    completed_today = today_progress_data["completed_habits"]
    today_progress = int(today_progress_data["daily_progress"])
    total_habits = today_progress_data["total_habits"]
    today_points = 0

    if len(habits) == 0:
        return {
            "today_progress": 0,
            "total_habits": 0,
            "completed_today": 0,
            "today_points": 0,
            "categories": [],
            "momentum": {
                "score": 0.0,
                "state": "STEADY",
                "message": "Start tracking habits to build momentum.",
                "today": 0.0,
                "yesterday": 0.0,
                "delta": 0.0,
                "window_average": 0.0
            }
        }

    category_map = defaultdict(lambda: {"completed": 0, "total": 0, "progress_sum": 0})

    today = date.today()

    # 🔁 LOOP THROUGH EACH HABIT
    for habit in habits:
        progress = get_habit_progress_snapshot(db, habit, user_id, today)
        
        if not progress["is_due"]:
            continue
        points = normalize_points(habit.points or 10)   # 👈 ADD THIS
        total_possible_points += points      

        category = (habit.category or "Uncategorized").strip()

        # ➕ count total habits
        category_map[category]["total"] += 1
        category_map[category]["progress_sum"] += progress["progress_percent"]

        # ✅ check if THIS habit is completely finished today
        if progress["completed"]:
            category_map[category]["completed"] += 1
            today_points += points

    # 📊 convert to list
    categories = [
        {
            "name": name,
            "completed": data["completed"],
            "total": data["total"],
            "percent": int(data["progress_sum"] / data["total"]) if data["total"] > 0 else 0
        }
        for name, data in category_map.items()
    ]

    if not categories:
        categories = [
            {"name": "No Data", "completed": 0, "total": 0, "percent": 0}
        ]

    momentum_data = get_momentum(db, user_id)

    return {
        "today_progress": today_progress,
        "total_habits": total_habits,
        "completed_today": completed_today,
        "today_points": today_points,
        "total_points": total_possible_points,
        "categories": categories,
        "momentum": {
            "score": momentum_data["momentum_score"],
            "state": momentum_data["momentum_state"],
            "message": momentum_data["message"],
            "today": momentum_data["today_progress"],
            "yesterday": momentum_data["yesterday_progress"],
            "delta": momentum_data["delta"],
            "window_average": momentum_data["window_average"]
        }
    }
def get_recent_completed_habits(db: Session, user_id: int, limit: int = 10):
    from sqlalchemy import desc
    
    recent_logs = db.query(HabitLog).join(Habit).filter(
        HabitLog.user_id == user_id,
        Habit.user_id == user_id
    ).order_by(desc(HabitLog.completed_at)).limit(limit).all()
    
    result = []
    for log in recent_logs:
        result.append({
            "id": log.id,
            "habit_id": log.habit_id,
            "habit_title": log.habit.title,
            "value_completed": log.value_completed,
            "completed_at": log.completed_at,
            "target_type": log.habit.target_type,
            "target_value": log.habit.target_value,
            "points": normalize_points(log.habit.points)
        })
    return result

def get_category_summary(db: Session, user_id: int, category: str):
    habits = db.query(Habit).filter(
        Habit.user_id == user_id, 
        func.lower(func.trim(Habit.category)) == category.strip().lower()
    ).all()
    
    if not habits:
        return {"week": [], "consistency": 0, "habits": []}

    habit_ids = [h.id for h in habits]
    today = date.today()
    start_date = today - timedelta(days=6)

    logs = (
        db.query(
            func.date(HabitLog.completed_at).label("day"),
            func.sum(HabitLog.value_completed).label("total")
        )
        .filter(HabitLog.habit_id.in_(habit_ids))
        .filter(HabitLog.completed_at >= start_date)
        .group_by(func.date(HabitLog.completed_at))
        .all()
    )
    
    day_map = {str(day): total for day, total in logs}
    week_data = []
    
    for i in range(7):
        date_iter = start_date + timedelta(days=i)
        key = str(date_iter)
        week_data.append({
            "date": key,
            "value": day_map.get(key, 0)
        })

    # Since it's a category, let's do a simple metric: 
    # Did you do *anything* in this category for the day?
    completed_days = sum(1 for d in week_data if d["value"] > 0)
    consistency = (completed_days / 7) * 100


    habit_data = []
    for h in habits:
        progress = get_habit_progress_snapshot(db, h, user_id, today)
        
        # Reset sub-habits if they were completed before today
        for sub in h.sub_habits:
            if sub.completed_today and sub.last_completed_at and sub.last_completed_at.date() < today:
                sub.completed_today = False
                db.add(sub)

        habit_data.append({
            "id": h.id,
            "title": h.title,
            "target_type": h.target_type,
            "target_value": h.target_value,
            "points": normalize_points(h.points),
            "remaining_value": progress["remaining_value"],
            "completed_today": progress["completed"],
            "is_due_today": progress["is_due"],
            "sub_habits": h.sub_habits
        })
    db.commit()

    return {
        "week": week_data,
        "consistency": consistency,
        "habits": habit_data
    }

def create_sub_habit(db: Session, sub_habit: SubHabitCreate, habit_id: int):
    new_sub = SubHabit(
        title=sub_habit.title,
        habit_id=habit_id
    )
    db.add(new_sub)
    db.commit()
    db.refresh(new_sub)
    return new_sub

def toggle_sub_habit(db: Session, sub_habit_id: int):
    sub = db.query(SubHabit).filter(SubHabit.id == sub_habit_id).first()
    if not sub:
        return None
    
    sub.completed_today = not sub.completed_today
    if sub.completed_today:
        sub.last_completed_at = datetime.now()
    
    db.commit()
    db.refresh(sub)
    return sub

def delete_sub_habit(db: Session, sub_habit_id: int):
    sub = db.query(SubHabit).filter(SubHabit.id == sub_habit_id).first()
    if not sub:
        return None
    db.delete(sub)
    db.commit()
    return sub
    
