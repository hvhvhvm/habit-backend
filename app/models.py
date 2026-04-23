from sqlalchemy import Column,Time, Integer, String, ForeignKey,Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base
from sqlalchemy import JSON
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key = True, index = True)
    username = Column(String, nullable=False)
    email = Column(String, unique = True, index = True)
    password_hash = Column(String,nullable=False)
    habits = relationship("Habit", back_populates="user")
    
class Habit(Base):
    __tablename__ = "habits"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String, nullable=False)

    target_type = Column(String)  
    target_value = Column(Integer)
    scheduled_time = Column(Time, nullable=True)
    category = Column(String, nullable=True)
    points = Column(Integer, default=10)

    user_id = Column(Integer, ForeignKey("users.id"))


    created_at = Column(DateTime, default=datetime.now)
    repeat = Column(String)   
    days = Column(JSON)
    is_session = Column(Boolean, default=False)

    focus_time = Column(Integer, nullable=True)
    break_time = Column(Integer, nullable=True)
    total_sessions = Column(Integer, nullable=True)

    user = relationship("User", back_populates="habits")
    logs = relationship(
        "HabitLog",
        back_populates="habit",
        cascade="all, delete-orphan"
    )
    sub_habits = relationship(
        "SubHabit",
        back_populates="habit",
        cascade="all, delete-orphan"
    )

class SubHabit(Base):
    __tablename__ = "sub_habits"
    id = Column(Integer, primary_key=True, index=True)
    habit_id = Column(Integer, ForeignKey("habits.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    completed_today = Column(Boolean, default=False)
    last_completed_at = Column(DateTime, nullable=True)

    habit = relationship("Habit", back_populates="sub_habits")

class HabitLog(Base):
    __tablename__ = "habit_logs"

    id = Column(Integer, primary_key=True, index=True)
    habit_id = Column(
        Integer,
        ForeignKey("habits.id", ondelete="CASCADE"),
        nullable=False
    )

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    

    value_completed = Column(Integer, default=0)

    completed_at = Column(DateTime, default=datetime.now)

    habit = relationship("Habit", back_populates="logs")
