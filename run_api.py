"""
FitTrack Pro - Flask API Server Entry Point

Usage (development):
    python run_api.py

Usage (production via gunicorn):
    gunicorn "run_api:create_app('production')" --bind 0.0.0.0:5000 --workers 4

Environment variables:
    FLASK_ENV=development|production|testing
    DATABASE_URL=postgresql://user:pass@host:port/dbname
    SECRET_KEY=your-secret-key
    JWT_SECRET_KEY=your-jwt-secret
"""

import os
from api import create_app, db

app = create_app(os.environ.get("FLASK_ENV", "development"))


@app.cli.command("init-db")
def init_db():
    """Create all database tables."""
    db.create_all()
    print("✅ Database tables created.")


@app.cli.command("seed-db")
def seed_db():
    """Seed database with demo data."""
    from api.models import User, FitnessGoal, WorkoutSession, MealEntry, BodyMeasurement, Badge, Notification
    from datetime import date, timedelta, datetime

    if User.query.count() > 0:
        print("ℹ️  Database already has data. Skipping seed.")
        return

    # Coach
    coach = User(username="coach_sarah", email="sarah@fittrack.com",
                 full_name="Sarah Mitchell", role="coach", height_cm=168.0, gender="Female")
    coach.set_password("coach123")
    db.session.add(coach)
    db.session.flush()

    # Member
    user = User(username="john_doe", email="john@example.com",
                full_name="John Doe", role="user", height_cm=178.0, gender="Male",
                date_of_birth=date(1995, 6, 15), coach_id=coach.id)
    user.set_password("user123")
    db.session.add(user)
    db.session.flush()

    db.session.add(FitnessGoal(
        user_id=user.id, goal_type="Lose Weight",
        description="Lose 5kg in 3 months",
        target_value=75.0, current_value=82.0, unit="kg",
        start_date=date.today(),
        target_date=date.today() + timedelta(days=90),
    ))

    for i, (name, atype, dur, cals) in enumerate([
        ("Morning Run", "Cardio", 45, 380),
        ("Upper Body", "Strength Training", 60, 320),
        ("HIIT Circuit", "HIIT", 30, 420),
    ]):
        db.session.add(WorkoutSession(
            user_id=user.id, name=name, activity_type=atype,
            date=date.today() - timedelta(days=i),
            duration_minutes=dur, calories_burned=cals,
        ))

    for mtype, food, cals, prot, carbs, fat in [
        ("Breakfast", "Oatmeal with Berries", 350, 12, 58, 7),
        ("Lunch", "Grilled Chicken Salad", 480, 42, 22, 18),
        ("Dinner", "Salmon with Vegetables", 520, 38, 30, 22),
        ("Snack", "Protein Bar", 220, 20, 25, 6),
    ]:
        db.session.add(MealEntry(
            user_id=user.id, meal_type=mtype, date=date.today(),
            food_name=food, quantity=1, calories=cals,
            protein_g=prot, carbs_g=carbs, fat_g=fat,
        ))

    db.session.add(BodyMeasurement(
        user_id=user.id, date=date.today(),
        weight_kg=82.0, body_fat_percent=22.5,
        waist_cm=89.0,
    ))

    db.session.add(Badge(user_id=user.id, name="First Workout",
                         description="Completed your first workout!", icon="🏋️"))
    db.session.add(Notification(
        user_id=user.id, title="Workout Reminder",
        message="Time for your evening run!",
        reminder_type="Workout", scheduled_at=datetime.utcnow(),
    ))

    db.session.commit()
    print("✅ Demo data seeded.")
    print("   john_doe / user123  (member)")
    print("   coach_sarah / coach123  (coach)")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
