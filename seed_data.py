#!/usr/bin/env python3
"""
FitTrack Pro - CLI Data Seeder
Seeds exercise presets and food library data.

Usage:
    python seed_data.py                  # Seed all data
    python seed_data.py --users          # Seed demo users only
    python seed_data.py --reset          # Drop tables and re-seed everything
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from models.database import (
    Base, engine, SessionLocal, User, WorkoutSession,
    MealEntry, FitnessGoal, BodyMeasurement, Badge, Notification
)
from datetime import date, datetime, timedelta
import random


def reset_database():
    print("⚠️  Dropping all tables...")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    print("✅ Tables recreated.")


def seed_users():
    session = SessionLocal()
    try:
        if session.query(User).count() > 0:
            print("ℹ️  Users already exist. Skipping.")
            return

        coach = User(username="coach_sarah", email="sarah@fittrack.com",
                     full_name="Sarah Mitchell", role="coach", height_cm=168.0, gender="Female")
        coach.set_password("coach123")
        session.add(coach)
        session.flush()

        users_data = [
            ("john_doe", "john@example.com", "John Doe", "Male", 178, 80.0),
            ("jane_smith", "jane@example.com", "Jane Smith", "Female", 165, 62.0),
            ("mike_jones", "mike@example.com", "Mike Jones", "Male", 182, 90.0),
        ]

        for uname, email, name, gender, height, weight in users_data:
            u = User(username=uname, email=email, full_name=name, role="user",
                     height_cm=height, gender=gender, coach_id=coach.id)
            u.set_password("user123")
            session.add(u)
            session.flush()

            # Seed goals
            g = FitnessGoal(
                user_id=u.id, goal_type="Lose Weight",
                description=f"Lose 5kg in 3 months",
                target_value=weight - 5, current_value=weight,
                unit="kg", start_date=date.today(),
                target_date=date.today() + timedelta(days=90)
            )
            session.add(g)

            # Seed measurements
            for i in range(5):
                m = BodyMeasurement(
                    user_id=u.id,
                    date=date.today() - timedelta(days=i * 7),
                    weight_kg=weight - (i * 0.3),
                    body_fat_percent=22.0 - (i * 0.2),
                    waist_cm=85 - (i * 0.5)
                )
                session.add(m)

            # Seed workouts (last 30 days)
            activities = ["Cardio", "Strength Training", "HIIT", "Yoga"]
            names_map = {
                "Cardio": ["Morning Run", "Evening Jog", "Cycling"],
                "Strength Training": ["Upper Body", "Lower Body", "Full Body Strength"],
                "HIIT": ["HIIT Circuit", "Tabata", "Interval Training"],
                "Yoga": ["Morning Yoga", "Restorative Yoga"],
            }
            for i in range(20):
                act = random.choice(activities)
                duration = random.randint(25, 75)
                w = WorkoutSession(
                    user_id=u.id,
                    name=random.choice(names_map[act]),
                    activity_type=act,
                    date=date.today() - timedelta(days=random.randint(0, 30)),
                    duration_minutes=duration,
                    calories_burned=round(duration * random.uniform(5.5, 9.0), 0)
                )
                session.add(w)

            # Seed meal entries (today)
            meals = [
                ("Breakfast", "Oatmeal", 1, 350, 12, 58, 7),
                ("Lunch", "Grilled Chicken Salad", 1, 480, 42, 22, 18),
                ("Dinner", "Salmon & Veggies", 1, 520, 38, 30, 22),
                ("Snack", "Protein Bar", 1, 220, 20, 25, 6),
            ]
            for meal_type, food, qty, cals, prot, carbs, fat in meals:
                me = MealEntry(
                    user_id=u.id, meal_type=meal_type, date=date.today(),
                    food_name=food, quantity=qty, unit="serving",
                    calories=cals, protein_g=prot, carbs_g=carbs, fat_g=fat
                )
                session.add(me)

            # Badges
            session.add(Badge(user_id=u.id, name="First Workout",
                              description="Completed your first workout!", icon="🏋️"))

        session.commit()
        print(f"✅ Seeded {len(users_data) + 1} users with full demo data.")
    except Exception as e:
        session.rollback()
        print(f"❌ Error seeding users: {e}")
    finally:
        session.close()


def print_summary():
    session = SessionLocal()
    try:
        print("\n📊 Database Summary:")
        print(f"   Users:        {session.query(User).count()}")
        print(f"   Workouts:     {session.query(WorkoutSession).count()}")
        print(f"   Meals:        {session.query(MealEntry).count()}")
        print(f"   Goals:        {session.query(FitnessGoal).count()}")
        print(f"   Measurements: {session.query(BodyMeasurement).count()}")
        print(f"   Badges:       {session.query(Badge).count()}")
        print(f"\n🔑 Login credentials:")
        for u in session.query(User).all():
            print(f"   {u.username:20} / {'coach123' if u.role == 'coach' else 'user123':12} ({u.role})")
    finally:
        session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FitTrack Pro Data Seeder")
    parser.add_argument("--reset", action="store_true", help="Drop all tables and reseed")
    parser.add_argument("--users", action="store_true", help="Seed users only")
    args = parser.parse_args()

    Base.metadata.create_all(engine)

    if args.reset:
        reset_database()

    seed_users()
    print_summary()
