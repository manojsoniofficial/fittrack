"""
FitTrack Pro - Database Migration Entry Point
migrations/env.py equivalent helper

Flask-Migrate (Alembic) is initialised automatically via:
    flask --app run_api db init        # run once to create migrations/ folder
    flask --app run_api db migrate -m "Initial schema"
    flask --app run_api db upgrade     # apply to DB

Or inside Docker:
    docker compose exec api flask --app run_api db upgrade

This file can also be run directly to create tables without migrations:
    python manage_db.py --create       # create all tables
    python manage_db.py --drop         # drop all tables (DANGER)
    python manage_db.py --seed         # seed demo data
    python manage_db.py --reset        # drop + create + seed
"""

import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(__file__))

os.environ.setdefault("FLASK_ENV", "development")


def get_app():
    from api import create_app
    return create_app(os.environ.get("FLASK_ENV", "development"))


def create_tables():
    app = get_app()
    from api import db
    with app.app_context():
        db.create_all()
        print("✅ All database tables created.")


def drop_tables():
    app = get_app()
    from api import db
    with app.app_context():
        db.drop_all()
        print("⚠️  All database tables dropped.")


def seed_data():
    app = get_app()
    from api import db
    from api.models import User, FitnessGoal, WorkoutSession, MealEntry, BodyMeasurement, Badge, Notification
    from datetime import date, timedelta, datetime

    with app.app_context():
        if User.query.count() > 0:
            print("ℹ️  Database already has users. Skipping seed.")
            return

        # Coach
        coach = User(username="coach_sarah", email="sarah@fittrack.com",
                     full_name="Sarah Mitchell", role="coach",
                     height_cm=168.0, gender="Female")
        coach.set_password("coach123")
        db.session.add(coach)
        db.session.flush()

        # Member
        user = User(username="john_doe", email="john@example.com",
                    full_name="John Doe", role="user",
                    height_cm=178.0, gender="Male",
                    date_of_birth=date(1995, 6, 15), coach_id=coach.id)
        user.set_password("user123")
        db.session.add(user)
        db.session.flush()

        # Goal
        db.session.add(FitnessGoal(
            user_id=user.id, goal_type="Lose Weight",
            description="Lose 5kg in 3 months",
            target_value=75.0, current_value=82.0, unit="kg",
            start_date=date.today(),
            target_date=date.today() + timedelta(days=90),
        ))

        # Workouts
        for i, (name, atype, dur, cals) in enumerate([
            ("Morning Run",    "Cardio",            45, 380),
            ("Upper Body",     "Strength Training", 60, 320),
            ("HIIT Circuit",   "HIIT",              30, 420),
            ("Evening Yoga",   "Yoga",              45, 180),
            ("5K Run",         "Cardio",            35, 310),
        ]):
            db.session.add(WorkoutSession(
                user_id=user.id, name=name, activity_type=atype,
                date=date.today() - timedelta(days=i),
                duration_minutes=dur, calories_burned=cals,
            ))

        # Meals
        for mtype, food, cals, prot, carbs, fat in [
            ("Breakfast", "Oatmeal with Berries",   350, 12, 58, 7),
            ("Lunch",     "Grilled Chicken Salad",  480, 42, 22, 18),
            ("Dinner",    "Salmon with Vegetables", 520, 38, 30, 22),
            ("Snack",     "Protein Bar",            220, 20, 25, 6),
        ]:
            db.session.add(MealEntry(
                user_id=user.id, meal_type=mtype, date=date.today(),
                food_name=food, quantity=1, unit="serving",
                calories=cals, protein_g=prot, carbs_g=carbs, fat_g=fat,
            ))

        # Measurements
        for i, (w, bf) in enumerate([(82.0, 22.5), (81.5, 22.2), (81.0, 22.0)]):
            db.session.add(BodyMeasurement(
                user_id=user.id, date=date.today() - timedelta(weeks=i),
                weight_kg=w, body_fat_percent=bf, waist_cm=89.0 - i,
            ))

        # Badges
        db.session.add(Badge(user_id=user.id, name="First Workout",
                             description="Completed your first workout!", icon="🏋️"))
        db.session.add(Badge(user_id=user.id, name="Consistency Star",
                             description="7 workouts in a row!", icon="⭐"))

        # Notifications
        db.session.add(Notification(
            user_id=user.id, title="Workout Reminder",
            message="Time for your evening run! Stay on track.",
            reminder_type="Workout", scheduled_at=datetime.utcnow(),
        ))

        db.session.commit()
        print("✅ Demo data seeded successfully.")
        print("   Login: john_doe / user123  (member)")
        print("   Login: coach_sarah / coach123  (coach)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FitTrack Pro DB management")
    parser.add_argument("--create", action="store_true", help="Create all tables")
    parser.add_argument("--drop",   action="store_true", help="Drop all tables (DANGER)")
    parser.add_argument("--seed",   action="store_true", help="Seed demo data")
    parser.add_argument("--reset",  action="store_true", help="Drop + create + seed")
    args = parser.parse_args()

    if args.reset:
        drop_tables()
        create_tables()
        seed_data()
    elif args.drop:
        drop_tables()
    elif args.create:
        create_tables()
    elif args.seed:
        seed_data()
    else:
        parser.print_help()
