from pydantic import BaseModel
from datetime import datetime, time
from enum import Enum

from typing import List,Optional
class TargetType(str, Enum):
    count = "count"
    duration = "duration"
class UserCreate(BaseModel):
    username : str
    email : str
    
class UserResponse(BaseModel):
    id: int
    username: str
    email : str
    
    class Config:
        from_attributes = True
    
class HabitCreate(BaseModel):
    title: str
    target_type : TargetType
    target_value : int
    scheduled_time: Optional[time] = None
    category : str
    points: Optional[int] = 10
    repeat: str  
    days: Optional[List[str]] = []
    is_session: bool = False
    focus_time: Optional[int] = None
    break_time: Optional[int] = None
    total_sessions: Optional[int] = None
class SubHabitBase(BaseModel):
    title: str

class SubHabitCreate(SubHabitBase):
    pass

class SubHabitResponse(SubHabitBase):
    id: int
    habit_id: int
    completed_today: bool
    last_completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class HabitResponse(BaseModel):
    id : int
    title: str
    target_type : TargetType
    target_value : int
    effective_target_value: Optional[int] = 0
    scheduled_time: time | None = None
    category: Optional[str] = None
    points: Optional[int] = 10
    repeat: Optional[str] = "daily"
    days: Optional[List[str]] = []
    is_due_today: Optional[bool] = True
    completed_today: Optional[bool] = False
    completed_today_value: Optional[int] = 0
    progress_percent: Optional[int] = 0
    remaining_value: Optional[int] = 0
    is_session: bool = False
    focus_time: Optional[int] = None
    break_time: Optional[int] = None
    total_sessions: Optional[int] = None
    sub_habits: List[SubHabitResponse] = []

    class Config:
        from_attributes = True
        
class HabitLogCreate(BaseModel):
    habit_id : int
    value_completed : int
    
class HabitLogResponse(BaseModel):
    id: int
    habit_id : int
    value_completed : int
    completed_at : datetime
    
    class Config:
        from_attributes = True
        
class HabitUpdate(BaseModel):
    title: Optional[str]= None
    target_type : Optional[TargetType]= None
    target_value : Optional[int]= None
    scheduled_time: Optional[time]= None
    category : Optional[str]= None
    points: Optional[int]= None
    repeat: Optional[str] = None
    days: Optional[List[str]] = None
    is_session: Optional[bool] = None
    focus_time: Optional[int] = None
    break_time: Optional[int] = None
    total_sessions: Optional[int] = None
class MomentumResponse(BaseModel):
    score: float
    state: str
    message: str
    today: float
    yesterday: float
    delta: float
    window_average: float
class HabitDashboard(BaseModel):
    id: int
    title: str
    progress: float
class CategorySummary(BaseModel):
    name: str
    completed: int
    total: int
    percent: int
class DashboardResponse(BaseModel):
    momentum : MomentumResponse
    today_progress: float
    total_habits: int
    completed_today: int
    today_points: int = 0
    total_points: int 
    categories : List[CategorySummary]
    streak: int = 0
class StreakResponse(BaseModel):
    streak: int
class UserRegister(BaseModel):
    username: str
    email: str
    password: str
class UserLogin(BaseModel):
    email: str
    password : str
class RecentCompletedHabit(BaseModel):
    id: int
    habit_id: int
    habit_title: str
    value_completed: int
    completed_at: datetime
    target_type: str
    target_value: int
    points: Optional[int] = 10
    
    class Config:
        from_attributes = True
