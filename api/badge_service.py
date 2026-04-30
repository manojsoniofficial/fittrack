"""
FitTrack Pro - Badge Service (Flask/API layer)
Uses Flask-SQLAlchemy session instead of standalone SQLAlchemy.
"""

from datetime import date
from api import db
from api.models import Badge, WorkoutSession, FitnessGoal

BADGE_RULES = [
    ("First Workout",    "Completed your first workout!",     "🏋️", "workouts",          1),
    ("Workout Warrior",  "Logged 10 workouts!",               "💪", "workouts",          10),
    ("Iron Will",        "Logged 50 workouts!",               "🦾", "workouts",          50),
    ("Consistency Star", "7 workouts this month!",            "⭐", "monthly_workouts",   7),
    ("Goal Crusher",     "Completed a fitness goal!",         "🎯", "goals_completed",    1),
    ("Marathon Month",   "300+ minutes of exercise this month!", "🏃", "monthly_minutes", 300),
    ("Calorie Counter",  "Logged meals for 7 days straight!", "🥗", "meal_streak",        7),
]


def check_and_award_badges(user_id: int) -> list:
    existing = {b.name for b in Badge.query.filter_by(user_id=user_id).all()}

    total_workouts = WorkoutSession.query.filter_by(user_id=user_id).count()
    completed_goals = FitnessGoal.query.filter_by(user_id=user_id, is_completed=True).count()

    today = date.today()
    month_start = today.replace(day=1)
    monthly_ws = WorkoutSession.query.filter(
        WorkoutSession.user_id == user_id,
        WorkoutSession.date >= month_start,
    ).all()
    monthly_workouts = len(monthly_ws)
    monthly_minutes = sum(w.duration_minutes or 0 for w in monthly_ws)

    metrics = {
        "workouts": total_workouts,
        "monthly_workouts": monthly_workouts,
        "goals_completed": completed_goals,
        "monthly_minutes": monthly_minutes,
        "meal_streak": 0,
    }

    newly_awarded = []
    for name, desc, icon, metric_key, threshold in BADGE_RULES:
        if name not in existing and metrics.get(metric_key, 0) >= threshold:
            badge = Badge(user_id=user_id, name=name, description=desc, icon=icon)
            db.session.add(badge)
            newly_awarded.append(badge)

    if newly_awarded:
        db.session.commit()

    return newly_awarded
