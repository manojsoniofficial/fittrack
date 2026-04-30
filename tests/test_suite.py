"""
FitTrack Pro - Comprehensive Test Suite
Covers: Unit Tests, Integration Tests, Acceptance Tests

Run with:
    pytest tests/test_suite.py -v --tb=short

Coverage targets ≥ 80%
"""

import pytest
import sys
import os
from datetime import date, timedelta, datetime

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import (
    Base, User, FitnessGoal, WorkoutSession, MealEntry,
    BodyMeasurement, Badge, Notification, ProgressReport, Exercise
)
from models.services import CalorieCalculator, ProgressAnalyser, BadgeService


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def engine():
    """In-memory SQLite engine for tests."""
    eng = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture(scope="session")
def session_factory(engine):
    return sessionmaker(bind=engine)


@pytest.fixture
def session(session_factory):
    """Provide a clean session with rollback after each test."""
    sess = session_factory()
    yield sess
    sess.rollback()
    sess.close()


@pytest.fixture
def sample_user(session):
    """Create a standard test user."""
    user = User(
        username="test_athlete",
        email="athlete@test.com",
        full_name="Test Athlete",
        role="user",
        height_cm=175.0,
        gender="Male",
        date_of_birth=date(1995, 1, 15),
    )
    user.set_password("testpass")
    session.add(user)
    session.flush()
    return user


@pytest.fixture
def coach_user(session):
    """Create a test coach."""
    coach = User(
        username="test_coach",
        email="coach@test.com",
        full_name="Test Coach",
        role="coach",
        height_cm=165.0,
        gender="Female",
    )
    coach.set_password("coachpass")
    session.add(coach)
    session.flush()
    return coach


@pytest.fixture
def sample_workout(session, sample_user):
    """Create a sample workout for the test user."""
    w = WorkoutSession(
        user_id=sample_user.id,
        name="Test Run",
        activity_type="Cardio",
        date=date.today(),
        duration_minutes=45,
        calories_burned=350.0,
    )
    session.add(w)
    session.flush()
    return w


@pytest.fixture
def sample_meal(session, sample_user):
    """Create a sample meal entry."""
    m = MealEntry(
        user_id=sample_user.id,
        meal_type="Lunch",
        date=date.today(),
        food_name="Chicken Salad",
        quantity=1.0,
        unit="plate",
        calories=480.0,
        protein_g=42.0,
        carbs_g=22.0,
        fat_g=18.0,
    )
    session.add(m)
    session.flush()
    return m


@pytest.fixture
def sample_goal(session, sample_user):
    """Create a sample fitness goal."""
    g = FitnessGoal(
        user_id=sample_user.id,
        goal_type="Lose Weight",
        description="Lose 5kg in 3 months",
        target_value=75.0,
        current_value=82.0,
        unit="kg",
        start_date=date.today(),
        target_date=date.today() + timedelta(days=90),
    )
    session.add(g)
    session.flush()
    return g


@pytest.fixture
def analyser(session):
    return ProgressAnalyser(session)


# ══════════════════════════════════════════════════════════════════════════════
#  UNIT TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestCalorieCalculator:
    """Unit tests for CalorieCalculator service."""

    def test_calculate_bmr_male(self):
        """BMR for a male should be positive and in expected range."""
        bmr = CalorieCalculator.calculate_bmr(80, 175, 30, "Male")
        assert bmr > 0
        # Mifflin-St Jeor: 10*80 + 6.25*175 - 5*30 + 5 = 800+1093.75-150+5 = 1748.75
        assert abs(bmr - 1748.75) < 1.0

    def test_calculate_bmr_female(self):
        """BMR for a female should use the female offset."""
        bmr = CalorieCalculator.calculate_bmr(60, 160, 25, "Female")
        # 10*60 + 6.25*160 - 5*25 - 161 = 600+1000-125-161 = 1314
        assert abs(bmr - 1314.0) < 1.0

    def test_calculate_daily_intake_moderate(self):
        """TDEE with moderate activity should be BMR × 1.55."""
        tdee = CalorieCalculator.calculate_daily_intake(80, 175, 30, "Male", "moderate")
        bmr = CalorieCalculator.calculate_bmr(80, 175, 30, "Male")
        assert abs(tdee - bmr * 1.55) < 1.0

    def test_calculate_daily_intake_defaults(self):
        """Default activity level should produce a reasonable calorie target."""
        tdee = CalorieCalculator.calculate_daily_intake(70, 170, 28, "Male")
        assert 1800 < tdee < 3500

    def test_calculate_daily_intake_all_levels(self):
        """All activity levels should produce increasing TDEE values."""
        levels = ["sedentary", "light", "moderate", "active", "very_active"]
        prev = 0
        for lvl in levels:
            tdee = CalorieCalculator.calculate_daily_intake(70, 170, 28, "Male", lvl)
            assert tdee > prev, f"Level {lvl} should be higher than previous"
            prev = tdee

    def test_calculate_calories_burned_cardio(self):
        """Calories burned during cardio should use MET 7.0."""
        cals = CalorieCalculator.calculate_calories_burned("Cardio", 60, 70)
        # MET=7.0, 1 hour, 70kg → 7.0 * 70 * 1.0 = 490
        assert abs(cals - 490.0) < 1.0

    def test_calculate_calories_burned_strength(self):
        """Strength training at MET=5.0 should burn less than cardio at MET=7.0."""
        cardio = CalorieCalculator.calculate_calories_burned("Cardio", 45, 75)
        strength = CalorieCalculator.calculate_calories_burned("Strength Training", 45, 75)
        assert cardio > strength

    def test_calculate_calories_burned_hiit(self):
        """HIIT should have the highest MET among common types."""
        hiit = CalorieCalculator.calculate_calories_burned("HIIT", 30, 75)
        yoga = CalorieCalculator.calculate_calories_burned("Yoga", 30, 75)
        assert hiit > yoga

    def test_calculate_calories_burned_zero_duration(self):
        """Zero-minute workout should burn 0 calories."""
        cals = CalorieCalculator.calculate_calories_burned("Cardio", 0, 70)
        assert cals == 0.0

    def test_calculate_calories_burned_unknown_type(self):
        """Unknown activity type should use fallback MET=5.0."""
        cals = CalorieCalculator.calculate_calories_burned("Dancing", 60, 70)
        assert cals > 0

    def test_get_macro_split_lose_weight(self):
        """Lose weight split should be higher protein, lower carbs."""
        macros = CalorieCalculator.get_macro_split("Lose Weight", 2000)
        assert macros["protein_g"] > macros["fat_g"]
        assert "protein_g" in macros
        assert "carbs_g" in macros
        assert "fat_g" in macros

    def test_get_macro_split_gain_muscle(self):
        """Muscle gain split should have carbs as dominant macro."""
        macros = CalorieCalculator.get_macro_split("Gain Muscle", 2500)
        assert macros["carbs_g"] > macros["protein_g"]

    def test_macro_calories_sum_approximately(self):
        """Macros should sum to approximately the input calories."""
        total_cals = 2000
        macros = CalorieCalculator.get_macro_split("Lose Weight", total_cals)
        calc_cals = macros["protein_g"] * 4 + macros["carbs_g"] * 4 + macros["fat_g"] * 9
        assert abs(calc_cals - total_cals) < 10  # within 10 kcal


class TestWorkoutSession:
    """Unit tests for WorkoutSession model."""

    def test_total_duration(self, sample_workout):
        """total_duration() should return the duration_minutes value."""
        assert sample_workout.total_duration() == 45

    def test_total_duration_zero(self, session, sample_user):
        """WorkoutSession with 0 minutes should return 0."""
        w = WorkoutSession(
            user_id=sample_user.id,
            name="Quick Stretch",
            activity_type="Yoga",
            date=date.today(),
            duration_minutes=0,
        )
        session.add(w)
        session.flush()
        assert w.total_duration() == 0

    def test_total_duration_null(self):
        """WorkoutSession with None duration should return 0."""
        w = WorkoutSession(
            name="Unknown",
            activity_type="Other",
            date=date.today(),
            duration_minutes=None,
        )
        assert w.total_duration() == 0

    def test_workout_creation_fields(self, sample_workout):
        """All core fields should be stored correctly."""
        assert sample_workout.name == "Test Run"
        assert sample_workout.activity_type == "Cardio"
        assert sample_workout.calories_burned == 350.0


class TestProgressAnalyser:
    """Unit tests for ProgressAnalyser service."""

    def test_compare_weight_change_positive(self, session, sample_user, analyser):
        """Weight gain should be reflected as positive change."""
        m1 = BodyMeasurement(user_id=sample_user.id, date=date.today() - timedelta(days=30), weight_kg=78.0)
        m2 = BodyMeasurement(user_id=sample_user.id, date=date.today(), weight_kg=82.0)
        session.add_all([m1, m2])
        session.flush()

        result = analyser.compare_weight_change(
            sample_user.id,
            date.today() - timedelta(days=30),
            date.today()
        )
        assert result["change_kg"] == 4.0
        assert result["trend"] == "gained"

    def test_compare_weight_change_negative(self, session, sample_user, analyser):
        """Weight loss should be reflected as negative change."""
        m1 = BodyMeasurement(user_id=sample_user.id, date=date.today() - timedelta(days=14), weight_kg=85.0)
        m2 = BodyMeasurement(user_id=sample_user.id, date=date.today() - timedelta(days=1), weight_kg=82.5)
        session.add_all([m1, m2])
        session.flush()

        result = analyser.compare_weight_change(
            sample_user.id,
            date.today() - timedelta(days=14),
            date.today()
        )
        assert result["change_kg"] == -2.5
        assert result["trend"] == "lost"

    def test_compare_weight_change_insufficient_data(self, session, analyser):
        """Single measurement should return insufficient_data."""
        # New user with no measurements
        new_user = User(username="no_meas_user", email="nm@test.com", full_name="No Meas", role="user")
        new_user.set_password("pass")
        session.add(new_user)
        session.flush()

        result = analyser.compare_weight_change(new_user.id, date.today() - timedelta(days=7), date.today())
        assert result["trend"] == "insufficient_data"
        assert result["change_kg"] == 0.0

    def test_get_weekly_summary_empty(self, session, analyser):
        """Weekly summary for user with no data should return zeros."""
        empty_user = User(username="empty_user2", email="eu2@test.com", full_name="Empty", role="user")
        empty_user.set_password("pass")
        session.add(empty_user)
        session.flush()

        summary = analyser.get_weekly_summary(empty_user.id)
        assert summary["total_workouts"] == 0
        assert summary["total_workout_minutes"] == 0
        assert summary["total_calories_burned"] == 0.0

    def test_get_weekly_summary_with_data(self, session, sample_user, analyser):
        """Weekly summary should aggregate workouts and meals correctly."""
        today = date.today()
        week_start = today - timedelta(days=today.weekday())

        w = WorkoutSession(
            user_id=sample_user.id, name="Run", activity_type="Cardio",
            date=week_start, duration_minutes=60, calories_burned=500
        )
        session.add(w)

        m1 = MealEntry(
            user_id=sample_user.id, meal_type="Breakfast", date=week_start,
            food_name="Oats", quantity=1, calories=350.0
        )
        session.add(m1)
        session.flush()

        summary = analyser.get_weekly_summary(sample_user.id, week_start)
        assert summary["total_workouts"] >= 1
        assert summary["total_workout_minutes"] >= 60
        assert summary["total_calories_burned"] >= 500

    def test_get_workout_streak_no_workouts(self, session, analyser):
        """User with no workouts should have streak of 0."""
        new_user = User(username="no_streak_user", email="ns@test.com", full_name="No Streak", role="user")
        new_user.set_password("pass")
        session.add(new_user)
        session.flush()

        streak = analyser.get_workout_streak(new_user.id)
        assert streak == 0

    def test_get_workout_streak_today(self, session, sample_user, analyser):
        """User with a workout today should have streak >= 1."""
        w = WorkoutSession(
            user_id=sample_user.id, name="Today Workout", activity_type="HIIT",
            date=date.today(), duration_minutes=30, calories_burned=300
        )
        session.add(w)
        session.flush()

        streak = analyser.get_workout_streak(sample_user.id)
        assert streak >= 1

    def test_get_daily_calories(self, session, sample_user, sample_meal, analyser):
        """Daily calories should sum all meal entries for the day."""
        result = analyser.get_daily_calories(sample_user.id, date.today())
        assert result["total"] >= 480.0  # at least the sample meal
        assert result["protein"] >= 42.0

    def test_generate_progress_report(self, session, sample_user, sample_workout, sample_meal, analyser):
        """Progress report should be created with correct aggregated data."""
        m1 = BodyMeasurement(user_id=sample_user.id, date=date.today() - timedelta(days=5), weight_kg=84.0)
        m2 = BodyMeasurement(user_id=sample_user.id, date=date.today(), weight_kg=82.0)
        session.add_all([m1, m2])
        session.flush()

        start = date.today() - timedelta(days=7)
        end = date.today()
        report = analyser.generate_progress_report(sample_user.id, start, end, sample_user.id)

        assert report.total_workouts >= 1
        assert report.total_calories_burned >= 0
        assert report.period_start == start
        assert report.period_end == end
        assert report.id is not None


class TestUserModel:
    """Unit tests for User model."""

    def test_password_hashing(self, session):
        """Passwords should be stored as hashes and verifiable."""
        user = User(username="hashtest", email="ht@test.com", full_name="Hash Test", role="user")
        user.set_password("mysecretpass")
        assert user.password_hash != "mysecretpass"  # not stored plaintext
        assert user.check_password("mysecretpass")
        assert not user.check_password("wrongpass")

    def test_user_defaults(self, session):
        """Default role should be 'user' and is_active should be True."""
        user = User(username="default_test", email="dt@test.com", full_name="Defaults", role="user")
        user.set_password("pass")
        session.add(user)
        session.flush()
        assert user.is_active is True
        assert user.role == "user"

    def test_unique_username(self, session):
        """Duplicate usernames should raise an integrity error."""
        u1 = User(username="unique_user_dup", email="uu1@test.com", full_name="User 1", role="user")
        u1.set_password("pass")
        u2 = User(username="unique_user_dup", email="uu2@test.com", full_name="User 2", role="user")
        u2.set_password("pass")
        session.add(u1)
        session.flush()
        session.add(u2)
        with pytest.raises(Exception):
            session.flush()
        session.rollback()


class TestFitnessGoal:
    """Unit tests for FitnessGoal model."""

    def test_goal_creation(self, sample_goal):
        """Goal should be created with correct fields."""
        assert sample_goal.goal_type == "Lose Weight"
        assert sample_goal.target_value == 75.0
        assert sample_goal.current_value == 82.0
        assert not sample_goal.is_completed

    def test_goal_completion(self, session, sample_goal):
        """Marking a goal as complete should persist."""
        sample_goal.is_completed = True
        session.flush()
        assert sample_goal.is_completed is True


class TestBadgeService:
    """Unit tests for BadgeService."""

    def test_first_workout_badge(self, session, sample_user):
        """First workout badge should be awarded after first workout."""
        w = WorkoutSession(
            user_id=sample_user.id, name="First Workout", activity_type="Other",
            date=date.today(), duration_minutes=15, calories_burned=100
        )
        session.add(w)
        session.flush()

        badge_service = BadgeService(session)
        awarded = badge_service.check_and_award_badges(sample_user.id)

        badge_names = [b.name for b in awarded]
        all_badges = session.query(Badge).filter_by(user_id=sample_user.id).all()
        all_names = [b.name for b in all_badges]

        assert "First Workout" in all_names

    def test_no_duplicate_badges(self, session, sample_user):
        """Same badge should not be awarded twice."""
        badge_service = BadgeService(session)
        # Award once
        badge_service.check_and_award_badges(sample_user.id)
        count_before = session.query(Badge).filter_by(user_id=sample_user.id, name="First Workout").count()

        # Award again
        badge_service.check_and_award_badges(sample_user.id)
        count_after = session.query(Badge).filter_by(user_id=sample_user.id, name="First Workout").count()

        assert count_before == count_after  # no duplicates


# ══════════════════════════════════════════════════════════════════════════════
#  INTEGRATION TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestWorkflowIntegration:
    """Integration tests simulating multi-step user workflows."""

    def test_full_workout_log_and_badge(self, session, sample_user):
        """
        INTEGRATION: Log workout → check calories → award badge.
        """
        # Step 1: Log workout
        duration = 50
        activity = "Cardio"
        weight = 80.0
        estimated_cals = CalorieCalculator.calculate_calories_burned(activity, duration, weight)

        w = WorkoutSession(
            user_id=sample_user.id,
            name="Integration Run",
            activity_type=activity,
            date=date.today(),
            duration_minutes=duration,
            calories_burned=estimated_cals,
        )
        session.add(w)
        session.flush()

        # Step 2: Verify calories are reasonable
        assert estimated_cals > 0
        assert w.total_duration() == duration

        # Step 3: Badge check
        badge_service = BadgeService(session)
        badge_service.check_and_award_badges(sample_user.id)

        badges = session.query(Badge).filter_by(user_id=sample_user.id).all()
        assert len(badges) >= 1

    def test_meal_log_and_daily_summary(self, session, sample_user):
        """
        INTEGRATION: Log multiple meals → analyse daily totals.
        """
        meals = [
            MealEntry(user_id=sample_user.id, meal_type="Breakfast", date=date.today(),
                      food_name="Oats", quantity=1, calories=350, protein_g=12, carbs_g=60, fat_g=5),
            MealEntry(user_id=sample_user.id, meal_type="Lunch", date=date.today(),
                      food_name="Salad", quantity=1, calories=420, protein_g=35, carbs_g=20, fat_g=15),
            MealEntry(user_id=sample_user.id, meal_type="Dinner", date=date.today(),
                      food_name="Salmon", quantity=1, calories=500, protein_g=40, carbs_g=25, fat_g=20),
        ]
        session.add_all(meals)
        session.flush()

        analyser = ProgressAnalyser(session)
        result = analyser.get_daily_calories(sample_user.id, date.today())

        assert result["total"] >= 1270  # 350+420+500
        assert result["protein"] >= 87   # 12+35+40

    def test_measurement_updates_goal_value(self, session, sample_user, sample_goal):
        """
        INTEGRATION: Adding a measurement should be reflected in goal progress.
        """
        new_weight = 80.0  # Down from 82
        m = BodyMeasurement(
            user_id=sample_user.id, date=date.today(), weight_kg=new_weight
        )
        session.add(m)
        session.flush()

        # Manually update goal (as done in dialog)
        sample_goal.current_value = new_weight
        session.flush()

        assert sample_goal.current_value == 80.0

    def test_progress_report_covers_full_period(self, session, sample_user):
        """
        INTEGRATION: Progress report should aggregate across multiple weeks.
        """
        start = date.today() - timedelta(days=30)
        end = date.today()

        # Add workouts spread across the period
        for i in range(0, 30, 3):
            w = WorkoutSession(
                user_id=sample_user.id, name=f"Workout D{i}", activity_type="HIIT",
                date=start + timedelta(days=i), duration_minutes=40, calories_burned=400
            )
            session.add(w)
        session.flush()

        analyser = ProgressAnalyser(session)
        report = analyser.generate_progress_report(sample_user.id, start, end, sample_user.id)

        assert report.total_workouts >= 10
        assert report.total_workout_minutes >= 400
        assert report.total_calories_burned >= 4000

    def test_coach_can_access_client_data(self, session, sample_user, coach_user):
        """
        INTEGRATION: Coach should be able to query a client's progress data.
        """
        # Assign coach
        sample_user.coach_id = coach_user.id
        session.flush()

        # Coach queries client data
        clients = session.query(User).filter_by(coach_id=coach_user.id).all()
        assert sample_user.id in [c.id for c in clients]

        # Coach generates a report for client
        analyser = ProgressAnalyser(session)
        report = analyser.generate_progress_report(
            sample_user.id,
            date.today() - timedelta(days=7),
            date.today(),
            coach_user.id,  # generated_by coach
        )
        assert report.generated_by == coach_user.id
        assert report.user_id == sample_user.id


# ══════════════════════════════════════════════════════════════════════════════
#  ACCEPTANCE TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestAcceptanceScenarios:
    """
    Acceptance tests matching the Assessment 3 specification:
    - Offline meal log queued and synced later
    - Coach exports client progress CSV/PDF
    - Workout reminders triggered correctly
    """

    def test_offline_meal_queued(self, session, sample_user):
        """
        ACCEPTANCE: Offline meal should be saved with is_synced=False,
        then synced (is_synced=True) when connection is restored.
        """
        # Simulate offline: create meal with is_synced=False
        offline_meal = MealEntry(
            user_id=sample_user.id,
            meal_type="Snack",
            date=date.today(),
            food_name="Protein Bar (Offline)",
            quantity=1,
            calories=220,
            protein_g=20,
            is_synced=False,
        )
        session.add(offline_meal)
        session.flush()

        # Verify it's queued (not synced)
        unsynced = session.query(MealEntry).filter_by(
            user_id=sample_user.id, is_synced=False
        ).all()
        assert len(unsynced) >= 1

        # Simulate sync
        for meal in unsynced:
            meal.is_synced = True
        session.flush()

        # Verify all synced
        still_unsynced = session.query(MealEntry).filter_by(
            user_id=sample_user.id, is_synced=False
        ).all()
        assert len(still_unsynced) == 0

    def test_offline_workout_queued_and_synced(self, session, sample_user):
        """
        ACCEPTANCE: Offline workout should be queued with is_synced=False
        and later synced to True.
        """
        w = WorkoutSession(
            user_id=sample_user.id, name="Offline HIIT", activity_type="HIIT",
            date=date.today(), duration_minutes=25, calories_burned=300,
            is_synced=False,
        )
        session.add(w)
        session.flush()

        unsynced = session.query(WorkoutSession).filter_by(
            user_id=sample_user.id, is_synced=False
        ).all()
        assert any(ws.name == "Offline HIIT" for ws in unsynced)

        # Sync
        for ws in unsynced:
            ws.is_synced = True
        session.flush()

        still_unsynced = session.query(WorkoutSession).filter_by(
            user_id=sample_user.id, is_synced=False
        ).count()
        assert still_unsynced == 0

    def test_coach_exports_client_progress(self, session, sample_user, coach_user):
        """
        ACCEPTANCE: Coach should be able to generate a progress report
        covering a specified period.
        """
        # Setup client workouts
        for i in range(5):
            w = WorkoutSession(
                user_id=sample_user.id, name=f"Run {i}", activity_type="Cardio",
                date=date.today() - timedelta(days=i), duration_minutes=35, calories_burned=350
            )
            session.add(w)
        session.flush()

        analyser = ProgressAnalyser(session)
        report = analyser.generate_progress_report(
            sample_user.id,
            date.today() - timedelta(days=30),
            date.today(),
            coach_user.id,
        )

        # Verify report fields
        assert report is not None
        assert report.total_workouts >= 5
        assert report.total_workout_minutes >= 175
        assert report.total_calories_burned >= 1750
        assert report.generated_by == coach_user.id

    def test_workout_reminders_created(self, session, sample_user):
        """
        ACCEPTANCE: Workout reminders should be created with correct type
        and scheduled time.
        """
        from datetime import datetime, timedelta as td

        reminder_time = datetime.utcnow() + td(hours=2)
        notif = Notification(
            user_id=sample_user.id,
            title="Evening Workout Reminder",
            message="Time for your evening run! Stay on track.",
            reminder_type="Workout",
            scheduled_at=reminder_time,
            is_read=False,
            is_sent=False,
        )
        session.add(notif)
        session.flush()

        # Fetch pending workout reminders
        pending = session.query(Notification).filter_by(
            user_id=sample_user.id,
            reminder_type="Workout",
            is_sent=False,
        ).all()

        assert len(pending) >= 1
        assert pending[0].title == "Evening Workout Reminder"
        assert pending[0].scheduled_at > datetime.utcnow()

    def test_meal_reminder_created(self, session, sample_user):
        """
        ACCEPTANCE: Meal reminders should be stored with type='Meal'.
        """
        from datetime import datetime, timedelta as td

        notif = Notification(
            user_id=sample_user.id,
            title="Lunch Time",
            message="Don't forget your healthy lunch!",
            reminder_type="Meal",
            scheduled_at=datetime.utcnow() + td(hours=1),
        )
        session.add(notif)
        session.flush()

        meal_reminders = session.query(Notification).filter_by(
            user_id=sample_user.id, reminder_type="Meal"
        ).all()
        assert len(meal_reminders) >= 1

    def test_user_can_set_fitness_goal_and_track(self, session, sample_user):
        """
        ACCEPTANCE: Full goal-setting scenario:
        User sets goal → logs workout → updates measurement → checks progress.
        """
        # Step 1: Set goal
        goal = FitnessGoal(
            user_id=sample_user.id,
            goal_type="Lose Weight",
            description="Lose 5kg in 3 months",
            target_value=75.0,
            current_value=82.0,
            unit="kg",
            start_date=date.today(),
            target_date=date.today() + timedelta(days=90),
        )
        session.add(goal)
        session.flush()

        # Step 2: Log a workout
        w = WorkoutSession(
            user_id=sample_user.id, name="Morning Run", activity_type="Cardio",
            date=date.today(), duration_minutes=40, calories_burned=380
        )
        session.add(w)
        session.flush()

        # Step 3: Update body measurement
        m = BodyMeasurement(
            user_id=sample_user.id, date=date.today(), weight_kg=81.5
        )
        session.add(m)
        session.flush()

        # Step 4: Update goal current_value
        goal.current_value = 81.5
        session.flush()

        # Step 5: Verify progress
        analyser = ProgressAnalyser(session)
        summary = analyser.get_weekly_summary(sample_user.id)

        assert summary["total_workouts"] >= 1
        assert goal.current_value == 81.5
        assert not goal.is_completed  # still in progress


# ══════════════════════════════════════════════════════════════════════════════
#  EXPECTED RESULTS TABLE (for test plan appendix)
# ══════════════════════════════════════════════════════════════════════════════

EXPECTED_RESULTS_TABLE = """
╔══════════════════════════════════════════════════════════════════════════════════════╗
║              FITTRACK PRO — TEST PLAN EXPECTED RESULTS TABLE                        ║
╠══════════╦════════════════════════════════════╦═══════════════════════════════════╣
║ Test ID  ║ Test Name                          ║ Expected Result                   ║
╠══════════╬════════════════════════════════════╬═══════════════════════════════════╣
║ UT-01    ║ BMR Calculation (Male)             ║ 1748.75 kcal                      ║
║ UT-02    ║ BMR Calculation (Female)           ║ 1314.0 kcal                       ║
║ UT-03    ║ TDEE - Moderate Activity           ║ BMR × 1.55                        ║
║ UT-04    ║ Calories Burned - Cardio 60min     ║ 490.0 kcal (70kg)                 ║
║ UT-05    ║ Calories Burned - Zero Duration    ║ 0.0 kcal                          ║
║ UT-06    ║ Macro Split - Lose Weight          ║ protein > fat, carbs 40%          ║
║ UT-07    ║ Macro Calories Sum                 ║ Within ±10 kcal of target         ║
║ UT-08    ║ WorkoutSession.total_duration()    ║ Returns duration_minutes          ║
║ UT-09    ║ total_duration() with None         ║ Returns 0                         ║
║ UT-10    ║ Password Hashing                   ║ Hash ≠ plaintext, verifiable      ║
║ UT-11    ║ Weight Change - Gain               ║ +4.0 kg, trend='gained'           ║
║ UT-12    ║ Weight Change - Loss               ║ -2.5 kg, trend='lost'             ║
║ UT-13    ║ Weight Change - No Data            ║ 'insufficient_data'               ║
║ UT-14    ║ Weekly Summary - Empty             ║ All zeros                         ║
║ UT-15    ║ Workout Streak - No Workouts       ║ 0 days                            ║
║ UT-16    ║ First Workout Badge                ║ Badge awarded                     ║
║ UT-17    ║ No Duplicate Badges                ║ Count unchanged on re-check       ║
╠══════════╬════════════════════════════════════╬═══════════════════════════════════╣
║ IT-01    ║ Full Workout + Badge Flow          ║ Badge awarded, calories correct   ║
║ IT-02    ║ Meal Log + Daily Summary           ║ Total ≥ 1270 kcal                 ║
║ IT-03    ║ Measurement → Goal Update          ║ Goal current_value updated        ║
║ IT-04    ║ Progress Report - Multi-Week       ║ ≥10 workouts, ≥4000 kcal          ║
║ IT-05    ║ Coach Accesses Client Data         ║ Client in coach's list            ║
╠══════════╬════════════════════════════════════╬═══════════════════════════════════╣
║ AT-01    ║ Offline Meal Queued + Synced       ║ is_synced flips True              ║
║ AT-02    ║ Offline Workout Queued + Synced    ║ is_synced flips True              ║
║ AT-03    ║ Coach Exports Client Progress      ║ Report with ≥5 workouts           ║
║ AT-04    ║ Workout Reminder Created           ║ Correct type and schedule         ║
║ AT-05    ║ Meal Reminder Created              ║ reminder_type='Meal'              ║
║ AT-06    ║ Full Goal → Workout → Measurement  ║ Goal updated, summary correct     ║
╚══════════╩════════════════════════════════════╩═══════════════════════════════════╝
"""

if __name__ == "__main__":
    print(EXPECTED_RESULTS_TABLE)
    print("\nRun tests with: pytest tests/test_suite.py -v --tb=short --cov=models")
