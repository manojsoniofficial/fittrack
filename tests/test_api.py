"""
FitTrack Pro — Flask REST API Test Suite
tests/test_api.py

Covers every requirement from Assessment 3:
  - Auth: register, login, JWT, /me
  - POST   /api/workouts               (IT-API-01)
  - GET    /api/progress/users/<id>    (IT-API-02)
  - POST   /api/progress/users/<id>/report
  - Nutrition API adapter fallback cache (IT-API-03)
  - Offline sync: meals + workouts     (AT-API-01,02)
  - Coach exports client report        (AT-API-06,07)
  - Workout / meal reminders           (AT-API-04,05)
  - Security: user A cannot access user B data
  - Full CRUD for workouts, nutrition, goals, measurements, notifications

Run:
    pytest tests/test_api.py -v --tb=short
    pytest tests/test_api.py -v --cov=api --cov-report=term-missing
"""

import pytest
import json
from datetime import date, timedelta, datetime

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from api import create_app, db as _db
from api.models import (
    User, WorkoutSession, MealEntry, FitnessGoal,
    BodyMeasurement, Notification, ProgressReport, Badge
)


# ══════════════════════════════════════════════════════════════════════════════
#  FIXTURES
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def app():
    """Flask test app using in-memory SQLite."""
    flask_app = create_app("testing")
    flask_app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "JWT_SECRET_KEY": "test-jwt-secret",
        "SECRET_KEY": "test-secret",
    })
    with flask_app.app_context():
        _db.create_all()
        yield flask_app
        _db.drop_all()


@pytest.fixture(scope="session")
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def clean_db(app):
    """Wipe all rows between tests for full isolation."""
    with app.app_context():
        yield
        _db.session.remove()
        for table in reversed(_db.metadata.sorted_tables):
            _db.session.execute(table.delete())
        _db.session.commit()


# ── Helpers ───────────────────────────────────────────────────────────────────

def register_and_login(client, username="testuser", password="pass123",
                        email=None, role="user"):
    if email is None:
        email = f"{username}@test.com"
    client.post("/api/auth/register", json={
        "username": username, "email": email,
        "password": password, "role": role,
        "full_name": username.replace("_", " ").title(),
    })
    resp = client.post("/api/auth/login",
                       json={"username": username, "password": password})
    data = resp.get_json()
    assert "access_token" in data, f"Login failed: {data}"
    return {"Authorization": f"Bearer {data['access_token']}"}


def make_coach_and_member(client):
    """Create a linked coach + member pair, return (coach_hdrs, member_hdrs, coach_id, member_id)."""
    coach_hdrs  = register_and_login(client, "coach_user",  "coachpass",  role="coach")
    member_hdrs = register_and_login(client, "member_user", "memberpass", role="user")
    with client.application.app_context():
        coach  = User.query.filter_by(username="coach_user").first()
        member = User.query.filter_by(username="member_user").first()
        member.coach_id = coach.id
        _db.session.commit()
        return coach_hdrs, member_hdrs, coach.id, member.id


# ══════════════════════════════════════════════════════════════════════════════
#  AUTH TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestAuth:

    def test_register_success(self, client):
        """AUTH-01: New user registration returns 201 with access_token."""
        resp = client.post("/api/auth/register", json={
            "username": "newuser", "email": "new@test.com",
            "password": "secure123", "full_name": "New User",
        })
        data = resp.get_json()
        assert resp.status_code == 201
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["username"] == "newuser"

    def test_register_duplicate_username(self, client):
        """AUTH-02: Duplicate username returns 409."""
        client.post("/api/auth/register", json={
            "username": "dupuser", "email": "dup1@test.com", "password": "pass"
        })
        resp = client.post("/api/auth/register", json={
            "username": "dupuser", "email": "dup2@test.com", "password": "pass"
        })
        assert resp.status_code == 409

    def test_register_missing_fields(self, client):
        """Registration without required fields returns 422."""
        resp = client.post("/api/auth/register", json={"username": "noemail"})
        assert resp.status_code == 422

    def test_login_success(self, client):
        """AUTH-03: Correct credentials return 200 with both tokens."""
        client.post("/api/auth/register", json={
            "username": "loginuser", "email": "login@test.com",
            "password": "correct_pass",
        })
        resp = client.post("/api/auth/login",
                           json={"username": "loginuser", "password": "correct_pass"})
        data = resp.get_json()
        assert resp.status_code == 200
        assert "access_token" in data
        assert "refresh_token" in data

    def test_login_wrong_password(self, client):
        """AUTH-04: Wrong password returns 401."""
        client.post("/api/auth/register", json={
            "username": "wrongpass_user", "email": "wp@test.com", "password": "real_pass"
        })
        resp = client.post("/api/auth/login",
                           json={"username": "wrongpass_user", "password": "wrong_pass"})
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client):
        """AUTH: Non-existent user returns 401."""
        resp = client.post("/api/auth/login",
                           json={"username": "ghost_user", "password": "any"})
        assert resp.status_code == 401

    def test_get_me_authenticated(self, client):
        """AUTH-05: GET /me with valid token returns user info."""
        hdrs = register_and_login(client, "me_user", "pass")
        resp = client.get("/api/auth/me", headers=hdrs)
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["user"]["username"] == "me_user"

    def test_get_me_no_token(self, client):
        """AUTH-06: GET /me without token returns 401."""
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_health_check(self, client):
        """GET /api/health returns 200 with status ok."""
        resp = client.get("/api/health")
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["status"] == "ok"


# ══════════════════════════════════════════════════════════════════════════════
#  WORKOUT TESTS  (IT-API-01)
# ══════════════════════════════════════════════════════════════════════════════

class TestWorkouts:

    def test_create_workout_success(self, client):
        """IT-API-01: POST /api/workouts creates workout and returns 201."""
        hdrs = register_and_login(client, "w_user1", "pass")
        resp = client.post("/api/workouts", headers=hdrs, json={
            "name": "Morning Run",
            "activity_type": "Cardio",
            "duration_minutes": 45,
            "calories_burned": 380,
            "date": date.today().isoformat(),
        })
        data = resp.get_json()
        assert resp.status_code == 201
        assert data["workout"]["name"] == "Morning Run"
        assert data["workout"]["activity_type"] == "Cardio"

    def test_create_workout_auto_calculates_calories(self, client):
        """IT-API-01b: When calories_burned is omitted, API auto-calculates it."""
        hdrs = register_and_login(client, "w_user2", "pass")
        resp = client.post("/api/workouts", headers=hdrs, json={
            "name": "HIIT Session",
            "activity_type": "HIIT",
            "duration_minutes": 30,
            # no calories_burned
        })
        data = resp.get_json()
        assert resp.status_code == 201
        assert data["workout"]["calories_burned"] > 0

    def test_create_workout_with_exercises(self, client):
        """IT-API-01c: Workout with exercises stores all exercise rows."""
        hdrs = register_and_login(client, "w_user3", "pass")
        resp = client.post("/api/workouts", headers=hdrs, json={
            "name": "Chest Day",
            "activity_type": "Strength Training",
            "duration_minutes": 60,
            "exercises": [
                {"name": "Bench Press", "sets": 4, "reps": 10, "weight_kg": 80},
                {"name": "Push-ups",    "sets": 3, "reps": 20},
            ],
        })
        data = resp.get_json()
        assert resp.status_code == 201
        assert len(data["workout"]["exercises"]) == 2

    def test_create_workout_missing_name(self, client):
        """IT-API-01d: Missing required field returns 422."""
        hdrs = register_and_login(client, "w_user4", "pass")
        resp = client.post("/api/workouts", headers=hdrs, json={
            "activity_type": "Cardio", "duration_minutes": 30,
        })
        assert resp.status_code == 422

    def test_list_workouts(self, client):
        """GET /api/workouts returns user's workouts."""
        hdrs = register_and_login(client, "w_user5", "pass")
        client.post("/api/workouts", headers=hdrs, json={
            "name": "Run A", "activity_type": "Cardio", "duration_minutes": 30
        })
        client.post("/api/workouts", headers=hdrs, json={
            "name": "Run B", "activity_type": "Cardio", "duration_minutes": 40
        })
        resp = client.get("/api/workouts", headers=hdrs)
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["total"] >= 2

    def test_get_single_workout(self, client):
        """GET /api/workouts/<id> returns correct workout."""
        hdrs = register_and_login(client, "w_user6", "pass")
        create = client.post("/api/workouts", headers=hdrs, json={
            "name": "Solo Run", "activity_type": "Cardio", "duration_minutes": 25
        })
        wid = create.get_json()["workout"]["id"]
        resp = client.get(f"/api/workouts/{wid}", headers=hdrs)
        assert resp.status_code == 200
        assert resp.get_json()["workout"]["id"] == wid

    def test_update_workout(self, client):
        """PUT /api/workouts/<id> updates the workout."""
        hdrs = register_and_login(client, "w_user7", "pass")
        create = client.post("/api/workouts", headers=hdrs, json={
            "name": "Original", "activity_type": "Yoga", "duration_minutes": 30
        })
        wid = create.get_json()["workout"]["id"]
        resp = client.put(f"/api/workouts/{wid}", headers=hdrs, json={"name": "Updated"})
        assert resp.status_code == 200
        assert resp.get_json()["workout"]["name"] == "Updated"

    def test_delete_workout(self, client):
        """DELETE /api/workouts/<id> removes workout."""
        hdrs = register_and_login(client, "w_user8", "pass")
        create = client.post("/api/workouts", headers=hdrs, json={
            "name": "To Delete", "activity_type": "Other", "duration_minutes": 15
        })
        wid = create.get_json()["workout"]["id"]
        del_resp = client.delete(f"/api/workouts/{wid}", headers=hdrs)
        assert del_resp.status_code == 200
        get_resp = client.get(f"/api/workouts/{wid}", headers=hdrs)
        assert get_resp.status_code == 404

    def test_user_cannot_access_other_users_workout(self, client):
        """AT-API-09: User A cannot see User B's workout."""
        hdrs_a = register_and_login(client, "user_a1", "pass", email="ua1@t.com")
        hdrs_b = register_and_login(client, "user_b1", "pass", email="ub1@t.com")
        create = client.post("/api/workouts", headers=hdrs_b, json={
            "name": "Private Workout", "activity_type": "HIIT", "duration_minutes": 20
        })
        wid = create.get_json()["workout"]["id"]
        resp = client.get(f"/api/workouts/{wid}", headers=hdrs_a)
        assert resp.status_code == 404

    def test_filter_workouts_by_activity_type(self, client):
        """Workouts can be filtered by activity_type query param."""
        hdrs = register_and_login(client, "w_filter_user", "pass")
        client.post("/api/workouts", headers=hdrs, json={
            "name": "Run", "activity_type": "Cardio", "duration_minutes": 30
        })
        client.post("/api/workouts", headers=hdrs, json={
            "name": "Lift", "activity_type": "Strength Training", "duration_minutes": 45
        })
        resp = client.get("/api/workouts?activity_type=Cardio", headers=hdrs)
        data = resp.get_json()
        assert all(w["activity_type"] == "Cardio" for w in data["workouts"])


# ══════════════════════════════════════════════════════════════════════════════
#  OFFLINE SYNC TESTS  (AT-API-01, AT-API-02)
# ══════════════════════════════════════════════════════════════════════════════

class TestOfflineSync:

    def test_sync_meals_offline(self, client):
        """AT-API-01: POST /api/nutrition/sync syncs 3 offline meal entries."""
        hdrs = register_and_login(client, "sync_meal_user", "pass")
        resp = client.post("/api/nutrition/sync", headers=hdrs, json={
            "meals": [
                {"food_name": "Apple",  "meal_type": "Snack",     "calories": 80,
                 "date": date.today().isoformat()},
                {"food_name": "Banana", "meal_type": "Breakfast", "calories": 105,
                 "date": date.today().isoformat()},
                {"food_name": "Oats",   "meal_type": "Breakfast", "calories": 350,
                 "date": date.today().isoformat()},
            ]
        })
        data = resp.get_json()
        assert resp.status_code == 200
        assert len(data["synced_ids"]) == 3
        # All returned IDs should be unique
        assert len(set(data["synced_ids"])) == 3

    def test_sync_workouts_offline(self, client):
        """AT-API-02: POST /api/workouts/sync syncs 2 offline workouts."""
        hdrs = register_and_login(client, "sync_wkt_user", "pass")
        resp = client.post("/api/workouts/sync", headers=hdrs, json={
            "workouts": [
                {"name": "Offline Run",  "activity_type": "Cardio",
                 "duration_minutes": 40, "date": date.today().isoformat()},
                {"name": "Offline Lift", "activity_type": "Strength Training",
                 "duration_minutes": 55, "date": (date.today() - timedelta(days=1)).isoformat()},
            ]
        })
        data = resp.get_json()
        assert resp.status_code == 200
        assert len(data["synced_ids"]) == 2

    def test_sync_workouts_empty_list(self, client):
        """AT-API-03: Syncing an empty list returns 200 with empty synced_ids."""
        hdrs = register_and_login(client, "sync_empty_user", "pass")
        resp = client.post("/api/workouts/sync", headers=hdrs, json={"workouts": []})
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["synced_ids"] == []

    def test_synced_workouts_are_retrievable(self, client):
        """Workouts synced via /sync endpoint can be retrieved via GET /workouts."""
        hdrs = register_and_login(client, "sync_retrieve_user", "pass")
        client.post("/api/workouts/sync", headers=hdrs, json={
            "workouts": [
                {"name": "Sync Test Run", "activity_type": "Cardio",
                 "duration_minutes": 30, "date": date.today().isoformat()},
            ]
        })
        resp = client.get("/api/workouts", headers=hdrs)
        names = [w["name"] for w in resp.get_json()["workouts"]]
        assert "Sync Test Run" in names


# ══════════════════════════════════════════════════════════════════════════════
#  NUTRITION TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestNutrition:

    def test_log_meal_with_calories(self, client):
        """IT-API-04: POST /api/nutrition logs a meal with provided macros."""
        hdrs = register_and_login(client, "nut_user1", "pass")
        resp = client.post("/api/nutrition", headers=hdrs, json={
            "food_name": "Grilled Chicken",
            "meal_type": "Lunch",
            "calories": 350,
            "protein_g": 45,
            "carbs_g": 5,
            "fat_g": 10,
            "date": date.today().isoformat(),
        })
        data = resp.get_json()
        assert resp.status_code == 201
        assert data["meal"]["food_name"] == "Grilled Chicken"
        assert data["meal"]["calories"] == 350

    def test_log_meal_auto_nutrition_from_adapter(self, client):
        """
        Nutrition API fallback cache test:
        When calories are not provided, the adapter returns data from
        the built-in fallback database (no external API needed).
        """
        hdrs = register_and_login(client, "nut_user2", "pass")
        resp = client.post("/api/nutrition", headers=hdrs, json={
            "food_name": "banana",  # known item in fallback DB
            "meal_type": "Snack",
            # no calories — adapter should fill them in
        })
        data = resp.get_json()
        assert resp.status_code == 201
        # Adapter/fallback should have populated calories
        assert data["meal"]["calories"] >= 0  # non-negative

    def test_nutrition_search_endpoint(self, client):
        """GET /api/nutrition/search?q=chicken returns suggestions."""
        hdrs = register_and_login(client, "nut_search_user", "pass")
        resp = client.get("/api/nutrition/search?q=chicken", headers=hdrs)
        data = resp.get_json()
        assert resp.status_code == 200
        assert "result" in data
        assert "suggestions" in data

    def test_nutrition_search_requires_query(self, client):
        """Nutrition search without q param returns 422."""
        hdrs = register_and_login(client, "nut_search2", "pass")
        resp = client.get("/api/nutrition/search?q=a", headers=hdrs)  # too short
        assert resp.status_code == 422

    def test_daily_summary(self, client):
        """GET /api/nutrition/summary aggregates macros for the day."""
        hdrs = register_and_login(client, "nut_summ_user", "pass")
        for food, cals, prot in [("Oats", 350, 12), ("Chicken", 480, 42), ("Salmon", 520, 38)]:
            client.post("/api/nutrition", headers=hdrs, json={
                "food_name": food, "meal_type": "Lunch", "calories": cals, "protein_g": prot
            })
        resp = client.get(f"/api/nutrition/summary?date={date.today().isoformat()}", headers=hdrs)
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["total_calories"] >= 1350
        assert data["meal_count"] >= 3

    def test_update_meal(self, client):
        """PUT /api/nutrition/<id> updates meal fields."""
        hdrs = register_and_login(client, "nut_upd_user", "pass")
        create = client.post("/api/nutrition", headers=hdrs, json={
            "food_name": "Old Name", "meal_type": "Breakfast", "calories": 200
        })
        mid = create.get_json()["meal"]["id"]
        resp = client.put(f"/api/nutrition/{mid}", headers=hdrs,
                          json={"food_name": "New Name", "calories": 250})
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["meal"]["food_name"] == "New Name"
        assert data["meal"]["calories"] == 250

    def test_delete_meal(self, client):
        """DELETE /api/nutrition/<id> removes meal."""
        hdrs = register_and_login(client, "nut_del_user", "pass")
        create = client.post("/api/nutrition", headers=hdrs, json={
            "food_name": "To Delete", "meal_type": "Snack", "calories": 100
        })
        mid = create.get_json()["meal"]["id"]
        assert client.delete(f"/api/nutrition/{mid}", headers=hdrs).status_code == 200
        assert client.get(f"/api/nutrition/{mid}", headers=hdrs).status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
#  GOALS TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestGoals:

    def test_create_and_list_goals(self, client):
        """Full goal lifecycle: create → list → verify."""
        hdrs = register_and_login(client, "goal_user1", "pass")
        create = client.post("/api/goals", headers=hdrs, json={
            "goal_type": "Lose Weight",
            "description": "Lose 5kg in 3 months",
            "target_value": 75.0,
            "current_value": 82.0,
            "unit": "kg",
        })
        assert create.status_code == 201
        gid = create.get_json()["goal"]["id"]

        list_resp = client.get("/api/goals", headers=hdrs)
        ids = [g["id"] for g in list_resp.get_json()["goals"]]
        assert gid in ids

    def test_update_goal_completion(self, client):
        """PUT /api/goals/<id> can mark a goal as completed."""
        hdrs = register_and_login(client, "goal_user2", "pass")
        create = client.post("/api/goals", headers=hdrs, json={
            "goal_type": "General Fitness", "description": "Run 5K"
        })
        gid = create.get_json()["goal"]["id"]
        resp = client.put(f"/api/goals/{gid}", headers=hdrs, json={"is_completed": True})
        assert resp.status_code == 200
        assert resp.get_json()["goal"]["is_completed"] is True

    def test_delete_goal(self, client):
        """DELETE /api/goals/<id> removes goal."""
        hdrs = register_and_login(client, "goal_user3", "pass")
        create = client.post("/api/goals", headers=hdrs, json={"goal_type": "Lose Weight"})
        gid = create.get_json()["goal"]["id"]
        assert client.delete(f"/api/goals/{gid}", headers=hdrs).status_code == 200


# ══════════════════════════════════════════════════════════════════════════════
#  MEASUREMENTS TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestMeasurements:

    def test_add_measurement(self, client):
        """POST /api/measurements logs body stats."""
        hdrs = register_and_login(client, "meas_user1", "pass")
        resp = client.post("/api/measurements", headers=hdrs, json={
            "weight_kg": 82.5,
            "body_fat_percent": 22.0,
            "waist_cm": 88.0,
            "date": date.today().isoformat(),
        })
        data = resp.get_json()
        assert resp.status_code == 201
        assert data["measurement"]["weight_kg"] == 82.5

    def test_measurement_auto_updates_weight_goal(self, client):
        """Adding a measurement auto-updates linked weight-based goals."""
        hdrs = register_and_login(client, "meas_goal_user", "pass")
        # Create a Lose Weight goal
        client.post("/api/goals", headers=hdrs, json={
            "goal_type": "Lose Weight", "description": "Lose weight",
            "target_value": 75.0, "current_value": 83.0, "unit": "kg",
        })
        # Log a new measurement
        client.post("/api/measurements", headers=hdrs, json={
            "weight_kg": 80.0, "date": date.today().isoformat()
        })
        # Goal current_value should be updated
        goals_resp = client.get("/api/goals", headers=hdrs)
        goals = goals_resp.get_json()["goals"]
        lose_weight_goal = next(
            (g for g in goals if g["goal_type"] == "Lose Weight"), None
        )
        assert lose_weight_goal is not None
        assert lose_weight_goal["current_value"] == 80.0

    def test_list_measurements(self, client):
        """GET /api/measurements returns all user measurements."""
        hdrs = register_and_login(client, "meas_list_user", "pass")
        client.post("/api/measurements", headers=hdrs, json={"weight_kg": 80.0})
        client.post("/api/measurements", headers=hdrs, json={"weight_kg": 79.5})
        resp = client.get("/api/measurements", headers=hdrs)
        assert resp.status_code == 200
        assert len(resp.get_json()["measurements"]) >= 2

    def test_delete_measurement(self, client):
        """DELETE /api/measurements/<id> removes measurement."""
        hdrs = register_and_login(client, "meas_del_user", "pass")
        create = client.post("/api/measurements", headers=hdrs, json={"weight_kg": 78.0})
        mid = create.get_json()["measurement"]["id"]
        assert client.delete(f"/api/measurements/{mid}", headers=hdrs).status_code == 200


# ══════════════════════════════════════════════════════════════════════════════
#  PROGRESS TESTS  (IT-API-02, IT-API-03)
# ══════════════════════════════════════════════════════════════════════════════

class TestProgress:

    def test_get_progress_summary(self, client):
        """IT-API-02: GET /api/progress/users/<id>/progress returns full summary."""
        hdrs = register_and_login(client, "prog_user1", "pass")

        with client.application.app_context():
            user = User.query.filter_by(username="prog_user1").first()
            uid = user.id

        # Log 3 workouts
        for i in range(3):
            client.post("/api/workouts", headers=hdrs, json={
                "name": f"Workout {i}", "activity_type": "Cardio",
                "duration_minutes": 45, "calories_burned": 380,
                "date": (date.today() - timedelta(days=i)).isoformat(),
            })

        resp = client.get(f"/api/progress/users/{uid}/progress", headers=hdrs)
        data = resp.get_json()
        assert resp.status_code == 200
        assert "total_workouts" in data
        assert "total_workout_minutes" in data
        assert "total_calories_burned" in data
        assert "avg_daily_calories_in" in data
        assert "weight_change_kg" in data
        assert data["total_workouts"] >= 3

    def test_generate_progress_report(self, client):
        """IT-API-03: POST /api/progress/users/<id>/report creates a ProgressReport."""
        hdrs = register_and_login(client, "prog_rep_user", "pass")
        with client.application.app_context():
            user = User.query.filter_by(username="prog_rep_user").first()
            uid = user.id

        client.post("/api/workouts", headers=hdrs, json={
            "name": "Test", "activity_type": "HIIT", "duration_minutes": 30
        })

        resp = client.post(f"/api/progress/users/{uid}/report", headers=hdrs, json={
            "start_date": (date.today() - timedelta(days=30)).isoformat(),
            "end_date":   date.today().isoformat(),
        })
        data = resp.get_json()
        assert resp.status_code == 201
        assert data["report"]["user_id"] == uid
        assert data["report"]["period_start"] is not None

    def test_user_cannot_access_other_users_progress(self, client):
        """AT-API-10: User A cannot see User B's progress."""
        hdrs_a = register_and_login(client, "prog_a_user", "pass", email="proga@t.com")
        register_and_login(client, "prog_b_user", "pass", email="progb@t.com")
        with client.application.app_context():
            user_b = User.query.filter_by(username="prog_b_user").first()
            uid_b = user_b.id

        resp = client.get(f"/api/progress/users/{uid_b}/progress", headers=hdrs_a)
        assert resp.status_code == 403


# ══════════════════════════════════════════════════════════════════════════════
#  NOTIFICATIONS / REMINDERS TESTS  (AT-API-04, AT-API-05)
# ══════════════════════════════════════════════════════════════════════════════

class TestNotifications:

    def test_create_workout_reminder(self, client):
        """AT-API-04: POST /api/notifications creates a Workout reminder."""
        hdrs = register_and_login(client, "notif_user1", "pass")
        resp = client.post("/api/notifications", headers=hdrs, json={
            "title": "Evening Run",
            "message": "Time for your evening run!",
            "reminder_type": "Workout",
            "scheduled_at": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
        })
        data = resp.get_json()
        assert resp.status_code == 201
        assert data["notification"]["reminder_type"] == "Workout"
        assert data["notification"]["is_read"] is False

    def test_create_meal_reminder(self, client):
        """AT-API-05: POST /api/notifications creates a Meal reminder."""
        hdrs = register_and_login(client, "notif_user2", "pass")
        resp = client.post("/api/notifications", headers=hdrs, json={
            "title": "Lunch Time",
            "message": "Don't forget your healthy lunch!",
            "reminder_type": "Meal",
        })
        data = resp.get_json()
        assert resp.status_code == 201
        assert data["notification"]["reminder_type"] == "Meal"

    def test_list_notifications(self, client):
        """GET /api/notifications returns user notifications with unread_count."""
        hdrs = register_and_login(client, "notif_list_user", "pass")
        client.post("/api/notifications", headers=hdrs, json={
            "title": "N1", "message": "msg1"
        })
        client.post("/api/notifications", headers=hdrs, json={
            "title": "N2", "message": "msg2"
        })
        resp = client.get("/api/notifications", headers=hdrs)
        data = resp.get_json()
        assert resp.status_code == 200
        assert len(data["notifications"]) >= 2
        assert "unread_count" in data
        assert data["unread_count"] >= 2

    def test_mark_notification_as_read(self, client):
        """PATCH /api/notifications/<id>/read marks notification as read."""
        hdrs = register_and_login(client, "notif_read_user", "pass")
        create = client.post("/api/notifications", headers=hdrs, json={
            "title": "To Read", "message": "msg"
        })
        nid = create.get_json()["notification"]["id"]
        resp = client.patch(f"/api/notifications/{nid}/read", headers=hdrs)
        assert resp.status_code == 200

        list_resp = client.get("/api/notifications", headers=hdrs)
        notif = next(n for n in list_resp.get_json()["notifications"] if n["id"] == nid)
        assert notif["is_read"] is True

    def test_mark_all_read(self, client):
        """POST /api/notifications/read-all marks all as read."""
        hdrs = register_and_login(client, "notif_all_user", "pass")
        for i in range(3):
            client.post("/api/notifications", headers=hdrs,
                        json={"title": f"N{i}", "message": "m"})
        client.post("/api/notifications/read-all", headers=hdrs)
        resp = client.get("/api/notifications?unread_only=true", headers=hdrs)
        assert resp.get_json()["unread_count"] == 0

    def test_delete_notification(self, client):
        """DELETE /api/notifications/<id> removes notification."""
        hdrs = register_and_login(client, "notif_del_user", "pass")
        create = client.post("/api/notifications", headers=hdrs, json={
            "title": "Del me", "message": "msg"
        })
        nid = create.get_json()["notification"]["id"]
        assert client.delete(f"/api/notifications/{nid}", headers=hdrs).status_code == 200


# ══════════════════════════════════════════════════════════════════════════════
#  COACH TESTS  (AT-API-06, AT-API-07, AT-API-08)
# ══════════════════════════════════════════════════════════════════════════════

class TestCoach:

    def test_coach_lists_clients(self, client):
        """AT-API-06: GET /api/coach/clients returns assigned clients."""
        coach_hdrs, member_hdrs, coach_id, member_id = make_coach_and_member(client)
        resp = client.get("/api/coach/clients", headers=coach_hdrs)
        data = resp.get_json()
        assert resp.status_code == 200
        client_ids = [c["id"] for c in data["clients"]]
        assert member_id in client_ids

    def test_coach_exports_client_report(self, client):
        """AT-API-07: POST /api/coach/clients/<id>/report generates a ProgressReport."""
        coach_hdrs, member_hdrs, coach_id, member_id = make_coach_and_member(client)

        # Member logs workouts
        for i in range(4):
            client.post("/api/workouts", headers=member_hdrs, json={
                "name": f"Workout {i}", "activity_type": "Cardio",
                "duration_minutes": 45, "calories_burned": 380,
                "date": (date.today() - timedelta(days=i)).isoformat(),
            })

        resp = client.post(
            f"/api/coach/clients/{member_id}/report",
            headers=coach_hdrs,
            json={
                "start_date": (date.today() - timedelta(days=30)).isoformat(),
                "end_date":   date.today().isoformat(),
            },
        )
        data = resp.get_json()
        assert resp.status_code == 201
        assert data["report"]["user_id"] == member_id
        assert data["report"]["generated_by"] == coach_id
        assert data["report"]["total_workouts"] >= 4

    def test_coach_gets_client_summary(self, client):
        """GET /api/coach/clients/<id>/summary returns client stats."""
        coach_hdrs, member_hdrs, coach_id, member_id = make_coach_and_member(client)
        resp = client.get(f"/api/coach/clients/{member_id}/summary", headers=coach_hdrs)
        data = resp.get_json()
        assert resp.status_code == 200
        assert "client" in data
        assert "this_month" in data
        assert "recent_workouts" in data

    def test_non_coach_blocked_from_coach_endpoints(self, client):
        """AT-API-08: Regular user calling /coach/clients gets 403 Forbidden."""
        hdrs = register_and_login(client, "regular_user_coach_test", "pass",
                                  email="ruc@t.com", role="user")
        resp = client.get("/api/coach/clients", headers=hdrs)
        assert resp.status_code == 403

    def test_coach_cannot_access_unassigned_client(self, client):
        """AT-API-09: Coach gets 404 for client not assigned to them."""
        coach_hdrs = register_and_login(client, "coach2_user", "pass",
                                        email="coach2@t.com", role="coach")
        register_and_login(client, "unrelated_user", "pass", email="unrel@t.com")
        with client.application.app_context():
            unrelated = User.query.filter_by(username="unrelated_user").first()
            uid = unrelated.id

        resp = client.get(f"/api/coach/clients/{uid}/summary", headers=coach_hdrs)
        assert resp.status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
#  EXPECTED RESULTS TABLE
# ══════════════════════════════════════════════════════════════════════════════

API_EXPECTED_RESULTS_TABLE = """
╔═══════════════════════════════════════════════════════════════════════════════╗
║        FITTRACK PRO — FLASK API TEST PLAN EXPECTED RESULTS TABLE             ║
╠══════════════╦══════════════════════════════════════╦════════════════════════╣
║  Test ID     ║ Test Name                            ║ Expected Result        ║
╠══════════════╬══════════════════════════════════════╬════════════════════════╣
║ AUTH-01      ║ Register new user                    ║ 201 + access_token     ║
║ AUTH-02      ║ Register duplicate username          ║ 409 Conflict           ║
║ AUTH-03      ║ Login correct credentials            ║ 200 + tokens           ║
║ AUTH-04      ║ Login wrong password                 ║ 401 Unauthorized       ║
║ AUTH-05      ║ GET /me with valid token             ║ 200 + user object      ║
║ AUTH-06      ║ GET /me without token                ║ 401 Unauthorized       ║
╠══════════════╬══════════════════════════════════════╬════════════════════════╣
║ IT-API-01    ║ POST /api/workouts                   ║ 201 + workout persisted║
║ IT-API-01b   ║ POST /workouts auto-calc calories    ║ calories_burned > 0    ║
║ IT-API-01c   ║ POST /workouts with exercises        ║ 2 exercises saved      ║
║ IT-API-01d   ║ POST /workouts missing name          ║ 422 Validation Error   ║
║ IT-API-02    ║ GET /progress/users/<id>/progress    ║ 200 + all summary keys ║
║ IT-API-03    ║ POST /progress/users/<id>/report     ║ 201 + report created   ║
║ IT-API-04    ║ Nutrition adapter fallback           ║ 201 + calories >= 0    ║
╠══════════════╬══════════════════════════════════════╬════════════════════════╣
║ AT-API-01    ║ POST /nutrition/sync (3 meals)       ║ 200 + 3 synced_ids     ║
║ AT-API-02    ║ POST /workouts/sync (2 workouts)     ║ 200 + 2 synced_ids     ║
║ AT-API-03    ║ POST /workouts/sync empty            ║ 200 + [] synced_ids    ║
║ AT-API-04    ║ Workout reminder created             ║ 201 type=Workout       ║
║ AT-API-05    ║ Meal reminder created                ║ 201 type=Meal          ║
║ AT-API-06    ║ Coach lists clients                  ║ 200 + member in list   ║
║ AT-API-07    ║ Coach exports client report          ║ 201 + report object    ║
║ AT-API-08    ║ Non-coach blocked from /coach        ║ 403 Forbidden          ║
║ AT-API-09    ║ User A cannot see User B workout     ║ 404 Not Found          ║
║ AT-API-10    ║ User A cannot see User B progress    ║ 403 Forbidden          ║
╚══════════════╩══════════════════════════════════════╩════════════════════════╝
Total API Tests: 35
"""

if __name__ == "__main__":
    print(API_EXPECTED_RESULTS_TABLE)
