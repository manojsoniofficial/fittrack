"""
FitTrack Pro - Flask/PostgreSQL ORM Models
api/models.py

These models use the Flask-SQLAlchemy instance (db) instead of the
standalone SQLAlchemy used by the PyQt6 desktop client.
Both share identical schema — only the db binding differs.
"""

import hashlib
from datetime import datetime, date
from api import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(100))
    date_of_birth = db.Column(db.Date)
    gender = db.Column(db.String(10))
    height_cm = db.Column(db.Float)
    role = db.Column(db.String(10), default="user")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    coach_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    # Relationships
    fitness_goals = db.relationship("FitnessGoal", back_populates="user", cascade="all, delete-orphan",
                                    foreign_keys="FitnessGoal.user_id")
    workout_sessions = db.relationship("WorkoutSession", back_populates="user", cascade="all, delete-orphan")
    meal_entries = db.relationship("MealEntry", back_populates="user", cascade="all, delete-orphan")
    body_measurements = db.relationship("BodyMeasurement", back_populates="user", cascade="all, delete-orphan")
    badges = db.relationship("Badge", back_populates="user", cascade="all, delete-orphan")
    notifications = db.relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    progress_reports = db.relationship("ProgressReport", back_populates="user", cascade="all, delete-orphan",
                                       foreign_keys="ProgressReport.user_id")
    clients = db.relationship("User", backref=db.backref("coach", remote_side=[id]), foreign_keys=[coach_id])

    def set_password(self, password: str):
        self.password_hash = hashlib.sha256(password.encode()).hexdigest()

    def check_password(self, password: str) -> bool:
        return self.password_hash == hashlib.sha256(password.encode()).hexdigest()

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "gender": self.gender,
            "height_cm": self.height_cm,
            "role": self.role,
            "date_of_birth": self.date_of_birth.isoformat() if self.date_of_birth else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_active": self.is_active,
        }


class FitnessGoal(db.Model):
    __tablename__ = "fitness_goals"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    goal_type = db.Column(db.String(30), nullable=False)
    description = db.Column(db.Text)
    target_value = db.Column(db.Float)
    current_value = db.Column(db.Float)
    unit = db.Column(db.String(20))
    start_date = db.Column(db.Date, default=date.today)
    target_date = db.Column(db.Date)
    is_completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="fitness_goals", foreign_keys=[user_id])

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "goal_type": self.goal_type,
            "description": self.description,
            "target_value": self.target_value,
            "current_value": self.current_value,
            "unit": self.unit,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "target_date": self.target_date.isoformat() if self.target_date else None,
            "is_completed": self.is_completed,
        }


class WorkoutSession(db.Model):
    __tablename__ = "workout_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    activity_type = db.Column(db.String(30), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    duration_minutes = db.Column(db.Integer, nullable=False)
    calories_burned = db.Column(db.Float)
    notes = db.Column(db.Text)
    is_synced = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="workout_sessions")
    exercises = db.relationship("Exercise", back_populates="workout_session", cascade="all, delete-orphan")

    def total_duration(self) -> int:
        return self.duration_minutes or 0

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "activity_type": self.activity_type,
            "date": self.date.isoformat() if self.date else None,
            "duration_minutes": self.duration_minutes,
            "calories_burned": self.calories_burned,
            "notes": self.notes,
            "is_synced": self.is_synced,
            "exercises": [e.to_dict() for e in self.exercises],
        }


class Exercise(db.Model):
    __tablename__ = "exercises"

    id = db.Column(db.Integer, primary_key=True)
    workout_session_id = db.Column(db.Integer, db.ForeignKey("workout_sessions.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    sets = db.Column(db.Integer)
    reps = db.Column(db.Integer)
    weight_kg = db.Column(db.Float)
    duration_seconds = db.Column(db.Integer)
    distance_km = db.Column(db.Float)

    workout_session = db.relationship("WorkoutSession", back_populates="exercises")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "sets": self.sets,
            "reps": self.reps,
            "weight_kg": self.weight_kg,
            "duration_seconds": self.duration_seconds,
            "distance_km": self.distance_km,
        }


class MealEntry(db.Model):
    __tablename__ = "meal_entries"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    meal_type = db.Column(db.String(20), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    food_name = db.Column(db.String(150), nullable=False)
    quantity = db.Column(db.Float, nullable=False, default=1.0)
    unit = db.Column(db.String(30), default="serving")
    calories = db.Column(db.Float, nullable=False, default=0.0)
    protein_g = db.Column(db.Float, default=0.0)
    carbs_g = db.Column(db.Float, default=0.0)
    fat_g = db.Column(db.Float, default=0.0)
    is_synced = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="meal_entries")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "meal_type": self.meal_type,
            "date": self.date.isoformat() if self.date else None,
            "food_name": self.food_name,
            "quantity": self.quantity,
            "unit": self.unit,
            "calories": self.calories,
            "protein_g": self.protein_g,
            "carbs_g": self.carbs_g,
            "fat_g": self.fat_g,
            "is_synced": self.is_synced,
        }


class BodyMeasurement(db.Model):
    __tablename__ = "body_measurements"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    weight_kg = db.Column(db.Float)
    body_fat_percent = db.Column(db.Float)
    muscle_mass_kg = db.Column(db.Float)
    chest_cm = db.Column(db.Float)
    waist_cm = db.Column(db.Float)
    hips_cm = db.Column(db.Float)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="body_measurements")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "date": self.date.isoformat() if self.date else None,
            "weight_kg": self.weight_kg,
            "body_fat_percent": self.body_fat_percent,
            "muscle_mass_kg": self.muscle_mass_kg,
            "chest_cm": self.chest_cm,
            "waist_cm": self.waist_cm,
            "hips_cm": self.hips_cm,
            "notes": self.notes,
        }


class ProgressReport(db.Model):
    __tablename__ = "progress_reports"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    generated_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    period_start = db.Column(db.Date, nullable=False)
    period_end = db.Column(db.Date, nullable=False)
    total_workouts = db.Column(db.Integer, default=0)
    total_workout_minutes = db.Column(db.Integer, default=0)
    total_calories_burned = db.Column(db.Float, default=0.0)
    avg_daily_calories_in = db.Column(db.Float, default=0.0)
    weight_change_kg = db.Column(db.Float, default=0.0)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="progress_reports", foreign_keys=[user_id])

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "generated_by": self.generated_by,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "total_workouts": self.total_workouts,
            "total_workout_minutes": self.total_workout_minutes,
            "total_calories_burned": self.total_calories_burned,
            "avg_daily_calories_in": self.avg_daily_calories_in,
            "weight_change_kg": self.weight_change_kg,
            "notes": self.notes,
        }


class Badge(db.Model):
    __tablename__ = "badges"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    icon = db.Column(db.String(50))
    awarded_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="badges")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "awarded_at": self.awarded_at.isoformat() if self.awarded_at else None,
        }


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    reminder_type = db.Column(db.String(20), default="General")
    scheduled_at = db.Column(db.DateTime)
    is_read = db.Column(db.Boolean, default=False)
    is_sent = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="notifications")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "message": self.message,
            "reminder_type": self.reminder_type,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "is_read": self.is_read,
            "is_sent": self.is_sent,
        }
