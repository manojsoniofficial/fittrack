"""
FitTrack Pro - Business Logic Services
Core domain layer: CalorieCalculator, ProgressAnalyser
"""

from datetime import date, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from models.database import (
    User, WorkoutSession, MealEntry, BodyMeasurement,
    FitnessGoal, Badge, Notification, ProgressReport, SessionLocal
)


# ─── Calorie Calculator ───────────────────────────────────────────────────────

class CalorieCalculator:
    """
    Handles all calorie-related calculations using
    Mifflin-St Jeor equation for BMR.
    """

    ACTIVITY_MULTIPLIERS = {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725,
        "very_active": 1.9,
    }

    MET_VALUES = {
        "Cardio": 7.0,
        "Strength Training": 5.0,
        "HIIT": 8.5,
        "Yoga": 3.0,
        "Sports": 7.5,
        "Other": 5.0,
    }

    @staticmethod
    def calculate_bmr(weight_kg: float, height_cm: float, age: int, gender: str) -> float:
        """Calculate Basal Metabolic Rate using Mifflin-St Jeor equation."""
        if gender.lower() in ("male", "m"):
            return (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5
        else:
            return (10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161

    @staticmethod
    def calculate_daily_intake(
        weight_kg: float,
        height_cm: float,
        age: int,
        gender: str,
        activity_level: str = "moderate"
    ) -> float:
        """
        Calculate recommended daily calorie intake (TDEE).
        TDEE = BMR × Activity Multiplier
        """
        bmr = CalorieCalculator.calculate_bmr(weight_kg, height_cm, age, gender)
        multiplier = CalorieCalculator.ACTIVITY_MULTIPLIERS.get(activity_level, 1.55)
        return round(bmr * multiplier, 1)

    @staticmethod
    def calculate_calories_burned(
        activity_type: str,
        duration_minutes: int,
        weight_kg: float
    ) -> float:
        """
        Estimate calories burned during a workout.
        Formula: Calories = MET × weight_kg × duration_hours
        """
        met = CalorieCalculator.MET_VALUES.get(activity_type, 5.0)
        duration_hours = duration_minutes / 60
        return round(met * weight_kg * duration_hours, 1)

    @staticmethod
    def get_macro_split(goal_type: str, daily_calories: float) -> dict:
        """Return protein/carb/fat grams based on goal type."""
        if goal_type == "Lose Weight":
            protein_pct, carb_pct, fat_pct = 0.35, 0.40, 0.25
        elif goal_type == "Gain Muscle":
            protein_pct, carb_pct, fat_pct = 0.30, 0.50, 0.20
        else:
            protein_pct, carb_pct, fat_pct = 0.25, 0.50, 0.25

        return {
            "protein_g": round((daily_calories * protein_pct) / 4, 1),
            "carbs_g": round((daily_calories * carb_pct) / 4, 1),
            "fat_g": round((daily_calories * fat_pct) / 9, 1),
        }


# ─── Progress Analyser ────────────────────────────────────────────────────────

class ProgressAnalyser:
    """
    Analyses user progress data and generates insights.
    """

    def __init__(self, session: Session):
        self.session = session

    def compare_weight_change(
        self,
        user_id: int,
        start_date: date,
        end_date: date
    ) -> dict:
        """
        Compare weight measurements between two dates.
        Returns weight change and trend direction.
        """
        measurements = (
            self.session.query(BodyMeasurement)
            .filter(
                BodyMeasurement.user_id == user_id,
                BodyMeasurement.date >= start_date,
                BodyMeasurement.date <= end_date,
                BodyMeasurement.weight_kg.isnot(None),
            )
            .order_by(BodyMeasurement.date)
            .all()
        )

        if len(measurements) < 2:
            return {"change_kg": 0.0, "trend": "insufficient_data", "start_weight": None, "end_weight": None}

        start_weight = measurements[0].weight_kg
        end_weight = measurements[-1].weight_kg
        change = round(end_weight - start_weight, 2)

        return {
            "change_kg": change,
            "start_weight": start_weight,
            "end_weight": end_weight,
            "trend": "lost" if change < 0 else ("gained" if change > 0 else "stable"),
            "data_points": len(measurements),
        }

    def get_weekly_summary(self, user_id: int, week_start: Optional[date] = None) -> dict:
        """Summarise workout and nutrition data for a given week."""
        if week_start is None:
            today = date.today()
            week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)

        workouts = (
            self.session.query(WorkoutSession)
            .filter(
                WorkoutSession.user_id == user_id,
                WorkoutSession.date >= week_start,
                WorkoutSession.date <= week_end,
            )
            .all()
        )

        meals = (
            self.session.query(MealEntry)
            .filter(
                MealEntry.user_id == user_id,
                MealEntry.date >= week_start,
                MealEntry.date <= week_end,
            )
            .all()
        )

        total_workout_mins = sum(w.total_duration() for w in workouts)
        total_calories_burned = sum(w.calories_burned or 0 for w in workouts)
        total_calories_in = sum(m.calories for m in meals)
        num_days_with_meals = len({m.date for m in meals}) or 1

        return {
            "week_start": week_start,
            "week_end": week_end,
            "total_workouts": len(workouts),
            "total_workout_minutes": total_workout_mins,
            "total_calories_burned": round(total_calories_burned, 1),
            "avg_daily_calories_in": round(total_calories_in / num_days_with_meals, 1),
            "total_calories_in": round(total_calories_in, 1),
            "net_calories": round(total_calories_in - total_calories_burned, 1),
        }

    def get_workout_streak(self, user_id: int) -> int:
        """Calculate current consecutive workout days streak."""
        today = date.today()
        streak = 0
        check_date = today

        for _ in range(365):
            has_workout = self.session.query(WorkoutSession).filter(
                WorkoutSession.user_id == user_id,
                WorkoutSession.date == check_date,
            ).first()

            if has_workout:
                streak += 1
                check_date = check_date - timedelta(days=1)
            else:
                break

        return streak

    def generate_progress_report(
        self,
        user_id: int,
        period_start: date,
        period_end: date,
        generated_by: int
    ) -> ProgressReport:
        """Create and persist a ProgressReport for a user over a date range."""
        workouts = (
            self.session.query(WorkoutSession)
            .filter(
                WorkoutSession.user_id == user_id,
                WorkoutSession.date >= period_start,
                WorkoutSession.date <= period_end,
            )
            .all()
        )

        meals = (
            self.session.query(MealEntry)
            .filter(
                MealEntry.user_id == user_id,
                MealEntry.date >= period_start,
                MealEntry.date <= period_end,
            )
            .all()
        )

        weight_data = self.compare_weight_change(user_id, period_start, period_end)
        num_days = (period_end - period_start).days or 1

        report = ProgressReport(
            user_id=user_id,
            generated_by=generated_by,
            period_start=period_start,
            period_end=period_end,
            total_workouts=len(workouts),
            total_workout_minutes=sum(w.total_duration() for w in workouts),
            total_calories_burned=sum(w.calories_burned or 0 for w in workouts),
            avg_daily_calories_in=sum(m.calories for m in meals) / num_days,
            weight_change_kg=weight_data.get("change_kg", 0.0),
        )
        self.session.add(report)
        self.session.flush()
        return report

    def get_daily_calories(self, user_id: int, target_date: date) -> dict:
        """Get calorie breakdown for a specific day."""
        meals = (
            self.session.query(MealEntry)
            .filter(MealEntry.user_id == user_id, MealEntry.date == target_date)
            .all()
        )
        return {
            "total": round(sum(m.calories for m in meals), 1),
            "protein": round(sum(m.protein_g for m in meals), 1),
            "carbs": round(sum(m.carbs_g for m in meals), 1),
            "fat": round(sum(m.fat_g for m in meals), 1),
            "meal_count": len(meals),
        }


# ─── Badge Service ────────────────────────────────────────────────────────────

class BadgeService:
    """Awards badges based on user activity."""

    BADGE_RULES = [
        ("First Workout", "Completed your first workout!", "🏋️", "workouts", 1),
        ("Workout Warrior", "Logged 10 workouts!", "💪", "workouts", 10),
        ("Iron Will", "Logged 50 workouts!", "🦾", "workouts", 50),
        ("Consistency Star", "7 workouts this month!", "⭐", "monthly_workouts", 7),
        ("Goal Crusher", "Completed a fitness goal!", "🎯", "goals_completed", 1),
        ("Calorie Counter", "Logged meals for 7 days straight!", "🥗", "meal_streak", 7),
        ("Marathon Month", "300+ minutes of exercise this month!", "🏃", "monthly_minutes", 300),
    ]

    def __init__(self, session: Session):
        self.session = session

    def check_and_award_badges(self, user_id: int) -> list:
        """Check badge criteria and award any newly earned badges."""
        newly_awarded = []
        existing = {b.name for b in self.session.query(Badge).filter_by(user_id=user_id).all()}

        total_workouts = self.session.query(WorkoutSession).filter_by(user_id=user_id).count()
        completed_goals = self.session.query(FitnessGoal).filter_by(user_id=user_id, is_completed=True).count()

        today = date.today()
        month_start = today.replace(day=1)
        monthly_workouts = (
            self.session.query(WorkoutSession)
            .filter(WorkoutSession.user_id == user_id, WorkoutSession.date >= month_start)
            .count()
        )
        monthly_minutes = (
            self.session.query(WorkoutSession)
            .filter(WorkoutSession.user_id == user_id, WorkoutSession.date >= month_start)
            .all()
        )
        monthly_minutes_total = sum(w.duration_minutes or 0 for w in monthly_minutes)

        metrics = {
            "workouts": total_workouts,
            "monthly_workouts": monthly_workouts,
            "goals_completed": completed_goals,
            "monthly_minutes": monthly_minutes_total,
            "meal_streak": 0,  # simplified
        }

        for name, desc, icon, metric_key, threshold in self.BADGE_RULES:
            if name not in existing and metrics.get(metric_key, 0) >= threshold:
                badge = Badge(user_id=user_id, name=name, description=desc, icon=icon)
                self.session.add(badge)
                newly_awarded.append(badge)

        if newly_awarded:
            self.session.flush()
        return newly_awarded
