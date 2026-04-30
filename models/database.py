"""
FitTrack Pro - Database Models
Uses SQLAlchemy ORM with SQLite for local storage
"""

from datetime import datetime, date
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, DateTime,
    Date, Boolean, ForeignKey, Text, Enum
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, backref
import enum
import hashlib
import os

Base = declarative_base()

# ─── Enumerations ────────────────────────────────────────────────────────────

class GoalType(enum.Enum):
    LOSE_WEIGHT = "Lose Weight"
    GAIN_MUSCLE = "Gain Muscle"
    IMPROVE_ENDURANCE = "Improve Endurance"
    MAINTAIN_WEIGHT = "Maintain Weight"
    GENERAL_FITNESS = "General Fitness"

class ActivityType(enum.Enum):
    STRENGTH = "Strength Training"
    CARDIO = "Cardio"
    YOGA = "Yoga"
    HIIT = "HIIT"
    SPORTS = "Sports"
    OTHER = "Other"

class MealType(enum.Enum):
    BREAKFAST = "Breakfast"
    LUNCH = "Lunch"
    DINNER = "Dinner"
    SNACK = "Snack"

class ReminderType(enum.Enum):
    WORKOUT = "Workout"
    MEAL = "Meal"
    MEASUREMENT = "Measurement"
    GENERAL = "General"

# ─── Models ──────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    full_name = Column(String(100))
    date_of_birth = Column(Date)
    gender = Column(String(10))
    height_cm = Column(Float)
    role = Column(String(10), default="user")  # "user" or "coach"
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # Relationships
    fitness_goals = relationship("FitnessGoal", back_populates="user", cascade="all, delete-orphan")
    workout_sessions = relationship("WorkoutSession", back_populates="user", cascade="all, delete-orphan")
    meal_entries = relationship("MealEntry", back_populates="user", cascade="all, delete-orphan")
    body_measurements = relationship("BodyMeasurement", back_populates="user", cascade="all, delete-orphan")
    badges = relationship("Badge", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    progress_reports = relationship("ProgressReport", back_populates="user", cascade="all, delete-orphan", foreign_keys="ProgressReport.user_id")

    # Coach relationship
    coach_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    clients = relationship("User", foreign_keys=[coach_id], backref=backref("coach", remote_side=[id]))

    def set_password(self, password: str):
        self.password_hash = hashlib.sha256(password.encode()).hexdigest()

    def check_password(self, password: str) -> bool:
        return self.password_hash == hashlib.sha256(password.encode()).hexdigest()

    def __repr__(self):
        return f"<User(username={self.username}, role={self.role})>"


class FitnessGoal(Base):
    __tablename__ = "fitness_goals"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    goal_type = Column(String(30), nullable=False)
    description = Column(Text)
    target_value = Column(Float)        # e.g., target weight in kg
    current_value = Column(Float)       # e.g., current weight in kg
    unit = Column(String(20))           # e.g., "kg", "km", "minutes"
    start_date = Column(Date, default=date.today)
    target_date = Column(Date)
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="fitness_goals")

    @property
    def progress_percent(self) -> float:
        """Calculate progress as a percentage towards the goal."""
        if self.target_value is None or self.current_value is None:
            return 0.0
        if self.goal_type in ["Lose Weight", "Reduce Body Fat"]:
            # Lower is better
            start = self.current_value  # approximate start
            total = abs(self.target_value - start) or 1
            done = abs(self.current_value - start)
            return min(100.0, (done / total) * 100)
        else:
            # Higher is better
            if self.target_value == 0:
                return 0.0
            return min(100.0, (self.current_value / self.target_value) * 100)

    def __repr__(self):
        return f"<FitnessGoal({self.goal_type}, target={self.target_value})>"


class WorkoutSession(Base):
    __tablename__ = "workout_sessions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    activity_type = Column(String(30), nullable=False)
    date = Column(Date, nullable=False, default=date.today)
    duration_minutes = Column(Integer, nullable=False)
    calories_burned = Column(Float)
    notes = Column(Text)
    is_synced = Column(Boolean, default=True)   # for offline support
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="workout_sessions")
    exercises = relationship("Exercise", back_populates="workout_session", cascade="all, delete-orphan")

    def total_duration(self) -> int:
        """Return total duration in minutes."""
        return self.duration_minutes or 0

    def __repr__(self):
        return f"<WorkoutSession({self.name}, {self.date})>"


class Exercise(Base):
    __tablename__ = "exercises"

    id = Column(Integer, primary_key=True)
    workout_session_id = Column(Integer, ForeignKey("workout_sessions.id"), nullable=False)
    name = Column(String(100), nullable=False)
    sets = Column(Integer)
    reps = Column(Integer)
    weight_kg = Column(Float)
    duration_seconds = Column(Integer)
    distance_km = Column(Float)

    workout_session = relationship("WorkoutSession", back_populates="exercises")


class MealEntry(Base):
    __tablename__ = "meal_entries"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    meal_type = Column(String(20), nullable=False)
    date = Column(Date, nullable=False, default=date.today)
    food_name = Column(String(150), nullable=False)
    quantity = Column(Float, nullable=False, default=1.0)
    unit = Column(String(30), default="serving")
    calories = Column(Float, nullable=False, default=0.0)
    protein_g = Column(Float, default=0.0)
    carbs_g = Column(Float, default=0.0)
    fat_g = Column(Float, default=0.0)
    is_synced = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="meal_entries")

    def __repr__(self):
        return f"<MealEntry({self.food_name}, {self.calories} kcal)>"


class BodyMeasurement(Base):
    __tablename__ = "body_measurements"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False, default=date.today)
    weight_kg = Column(Float)
    body_fat_percent = Column(Float)
    muscle_mass_kg = Column(Float)
    chest_cm = Column(Float)
    waist_cm = Column(Float)
    hips_cm = Column(Float)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="body_measurements")

    def __repr__(self):
        return f"<BodyMeasurement({self.date}, weight={self.weight_kg})>"


class ProgressReport(Base):
    __tablename__ = "progress_reports"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    generated_by = Column(Integer, ForeignKey("users.id"))  # coach or self
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    total_workouts = Column(Integer, default=0)
    total_workout_minutes = Column(Integer, default=0)
    total_calories_burned = Column(Float, default=0.0)
    avg_daily_calories_in = Column(Float, default=0.0)
    weight_change_kg = Column(Float, default=0.0)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="progress_reports", foreign_keys=[user_id])

    def __repr__(self):
        return f"<ProgressReport({self.period_start} to {self.period_end})>"


class Badge(Base):
    __tablename__ = "badges"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    icon = Column(String(50))
    awarded_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="badges")

    def __repr__(self):
        return f"<Badge({self.name})>"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(150), nullable=False)
    message = Column(Text, nullable=False)
    reminder_type = Column(String(20), default="General")
    scheduled_at = Column(DateTime)
    is_read = Column(Boolean, default=False)
    is_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="notifications")

    def __repr__(self):
        return f"<Notification({self.title})>"


# ─── Database Setup ───────────────────────────────────────────────────────────

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fittrack.db")

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
SessionLocal = sessionmaker(bind=engine)


def init_db():
    """Create all tables and seed demo data if empty."""
    Base.metadata.create_all(engine)
    session = SessionLocal()
    try:
        if session.query(User).count() == 0:
            _seed_demo_data(session)
    finally:
        session.close()


def _seed_demo_data(session):
    """Insert demo users and sample data."""
    # Create coach
    coach = User(
        username="coach_sarah",
        email="sarah@fittrack.com",
        full_name="Sarah Mitchell",
        role="coach",
        height_cm=168.0,
        gender="Female",
    )
    coach.set_password("coach123")
    session.add(coach)
    session.flush()

    # Create user
    user = User(
        username="john_doe",
        email="john@example.com",
        full_name="John Doe",
        role="user",
        height_cm=178.0,
        gender="Male",
        date_of_birth=date(1995, 6, 15),
        coach_id=coach.id,
    )
    user.set_password("user123")
    session.add(user)
    session.flush()

    # Create fitness goal
    goal = FitnessGoal(
        user_id=user.id,
        goal_type="Lose Weight",
        description="Lose 5kg in 3 months",
        target_value=75.0,
        current_value=82.0,
        unit="kg",
        start_date=date.today(),
        target_date=date(date.today().year, date.today().month + 3 if date.today().month <= 9 else 1, 1),
    )
    session.add(goal)

    # Sample workouts
    workouts = [
        WorkoutSession(user_id=user.id, name="Morning Run", activity_type="Cardio",
                       date=date.today(), duration_minutes=45, calories_burned=380),
        WorkoutSession(user_id=user.id, name="Upper Body Strength", activity_type="Strength Training",
                       date=date.today(), duration_minutes=60, calories_burned=320),
        WorkoutSession(user_id=user.id, name="HIIT Circuit", activity_type="HIIT",
                       date=date(date.today().year, date.today().month, max(1, date.today().day - 2)),
                       duration_minutes=30, calories_burned=420),
    ]
    session.add_all(workouts)

    # Sample meals
    meals = [
        MealEntry(user_id=user.id, meal_type="Breakfast", date=date.today(),
                  food_name="Oatmeal with Berries", quantity=1, unit="bowl",
                  calories=350, protein_g=12, carbs_g=58, fat_g=7),
        MealEntry(user_id=user.id, meal_type="Lunch", date=date.today(),
                  food_name="Grilled Chicken Salad", quantity=1, unit="plate",
                  calories=480, protein_g=42, carbs_g=22, fat_g=18),
        MealEntry(user_id=user.id, meal_type="Dinner", date=date.today(),
                  food_name="Salmon with Vegetables", quantity=1, unit="plate",
                  calories=520, protein_g=38, carbs_g=30, fat_g=22),
        MealEntry(user_id=user.id, meal_type="Snack", date=date.today(),
                  food_name="Protein Bar", quantity=1, unit="bar",
                  calories=220, protein_g=20, carbs_g=25, fat_g=6),
    ]
    session.add_all(meals)

    # Sample measurement
    measurement = BodyMeasurement(
        user_id=user.id, date=date.today(),
        weight_kg=82.0, body_fat_percent=22.5,
        muscle_mass_kg=35.0, waist_cm=89.0,
    )
    session.add(measurement)

    # Sample badges
    badges = [
        Badge(user_id=user.id, name="First Workout", description="Completed your first workout!", icon="🏋️"),
        Badge(user_id=user.id, name="Consistency Star", description="7 workouts in a row!", icon="⭐"),
    ]
    session.add_all(badges)

    # Sample notifications
    notif = Notification(
        user_id=user.id,
        title="Workout Reminder",
        message="Time for your evening run! Stay on track with your goals.",
        reminder_type="Workout",
        scheduled_at=datetime.utcnow(),
    )
    session.add(notif)

    session.commit()
    print("✅ Demo data seeded successfully.")
