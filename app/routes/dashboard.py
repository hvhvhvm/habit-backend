from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.crud import get_dashboard_data
from app.schemas import DashboardResponse
from app.core.security import get_current_user   
from app.crud import get_last_7_days_data,get_heatmap_data
from sqlalchemy.orm import Session
from fastapi import Depends
from app.models import Habit
from app.crud import get_category_summary
from app.models import User


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/", response_model=DashboardResponse)
def get_dashboard(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return get_dashboard_data(db, current_user.id)
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
    habits = db.query(Habit).filter(Habit.user_id == current_user.id).all()

    return [
        {
            "id": h.id,
            "name": h.title
        }
        for h in habits
    ]
@router.get("/heatmap/")
def get_heatmap(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
    
):
    return get_heatmap_data(db,current_user.id)
    
