"""
FitTrack Pro - Workout Routes
GET    /api/workouts               List user's workouts
POST   /api/workouts               Create workout
GET    /api/workouts/<id>          Get single workout
PUT    /api/workouts/<id>          Update workout
DELETE /api/workouts/<id>          Delete workout
POST   /api/workouts/sync          Sync offline workouts
"""

from datetime import date
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from api import db
from api.models import WorkoutSession, Exercise, User
from models.services import CalorieCalculator

workouts_bp = Blueprint("workouts", __name__)


def _get_current_user():
    return User.query.get(int(get_jwt_identity()))


@workouts_bp.route("", methods=["GET"])
@jwt_required()
def list_workouts():
    user_id = int(get_jwt_identity())
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    activity_type = request.args.get("activity_type")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    query = WorkoutSession.query.filter_by(user_id=user_id)

    if activity_type:
        query = query.filter(WorkoutSession.activity_type == activity_type)
    if start_date:
        query = query.filter(WorkoutSession.date >= date.fromisoformat(start_date))
    if end_date:
        query = query.filter(WorkoutSession.date <= date.fromisoformat(end_date))

    query = query.order_by(WorkoutSession.date.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "workouts": [w.to_dict() for w in pagination.items],
        "total": pagination.total,
        "pages": pagination.pages,
        "current_page": page,
    }), 200


@workouts_bp.route("", methods=["POST"])
@jwt_required()
def create_workout():
    user_id = int(get_jwt_identity())
    data = request.get_json()

    # Validate required fields
    for field in ["name", "activity_type", "duration_minutes"]:
        if not data.get(field):
            return jsonify({"error": f"Field '{field}' is required"}), 422

    workout_date = date.fromisoformat(data["date"]) if data.get("date") else date.today()

    # Auto-calculate calories if not provided
    calories = data.get("calories_burned")
    if calories is None:
        # Use latest measurement weight or default 75kg
        from api.models import BodyMeasurement
        latest_meas = (
            BodyMeasurement.query
            .filter_by(user_id=user_id)
            .filter(BodyMeasurement.weight_kg.isnot(None))
            .order_by(BodyMeasurement.date.desc())
            .first()
        )
        weight = latest_meas.weight_kg if latest_meas else 75.0
        calories = CalorieCalculator.calculate_calories_burned(
            data["activity_type"],
            int(data["duration_minutes"]),
            weight
        )

    workout = WorkoutSession(
        user_id=user_id,
        name=data["name"],
        activity_type=data["activity_type"],
        date=workout_date,
        duration_minutes=int(data["duration_minutes"]),
        calories_burned=calories,
        notes=data.get("notes"),
        is_synced=True,
    )
    db.session.add(workout)
    db.session.flush()

    # Add exercises if provided
    for ex_data in data.get("exercises", []):
        if ex_data.get("name"):
            exercise = Exercise(
                workout_session_id=workout.id,
                name=ex_data["name"],
                sets=ex_data.get("sets"),
                reps=ex_data.get("reps"),
                weight_kg=ex_data.get("weight_kg"),
                duration_seconds=ex_data.get("duration_seconds"),
                distance_km=ex_data.get("distance_km"),
            )
            db.session.add(exercise)

    db.session.commit()

    # Check for badge awards
    from api.badge_service import check_and_award_badges
    check_and_award_badges(user_id)

    return jsonify({
        "message": "Workout logged successfully",
        "workout": workout.to_dict(),
    }), 201


@workouts_bp.route("/<int:workout_id>", methods=["GET"])
@jwt_required()
def get_workout(workout_id):
    user_id = int(get_jwt_identity())
    workout = WorkoutSession.query.filter_by(id=workout_id, user_id=user_id).first_or_404()
    return jsonify({"workout": workout.to_dict()}), 200


@workouts_bp.route("/<int:workout_id>", methods=["PUT"])
@jwt_required()
def update_workout(workout_id):
    user_id = int(get_jwt_identity())
    workout = WorkoutSession.query.filter_by(id=workout_id, user_id=user_id).first_or_404()
    data = request.get_json()

    if "name" in data:
        workout.name = data["name"]
    if "activity_type" in data:
        workout.activity_type = data["activity_type"]
    if "date" in data:
        workout.date = date.fromisoformat(data["date"])
    if "duration_minutes" in data:
        workout.duration_minutes = int(data["duration_minutes"])
    if "calories_burned" in data:
        workout.calories_burned = data["calories_burned"]
    if "notes" in data:
        workout.notes = data["notes"]

    db.session.commit()
    return jsonify({"message": "Workout updated", "workout": workout.to_dict()}), 200


@workouts_bp.route("/<int:workout_id>", methods=["DELETE"])
@jwt_required()
def delete_workout(workout_id):
    user_id = int(get_jwt_identity())
    workout = WorkoutSession.query.filter_by(id=workout_id, user_id=user_id).first_or_404()
    db.session.delete(workout)
    db.session.commit()
    return jsonify({"message": "Workout deleted"}), 200


@workouts_bp.route("/sync", methods=["POST"])
@jwt_required()
def sync_workouts():
    """
    Offline sync endpoint: receive queued workouts with is_synced=False,
    persist them, then mark as synced.
    """
    user_id = int(get_jwt_identity())
    data = request.get_json()
    offline_workouts = data.get("workouts", [])
    synced_ids = []

    for w_data in offline_workouts:
        workout = WorkoutSession(
            user_id=user_id,
            name=w_data.get("name", "Offline Workout"),
            activity_type=w_data.get("activity_type", "Other"),
            date=date.fromisoformat(w_data["date"]) if w_data.get("date") else date.today(),
            duration_minutes=int(w_data.get("duration_minutes", 0)),
            calories_burned=w_data.get("calories_burned"),
            notes=w_data.get("notes"),
            is_synced=True,
        )
        db.session.add(workout)
        db.session.flush()
        synced_ids.append(workout.id)

    db.session.commit()
    return jsonify({
        "message": f"Synced {len(synced_ids)} offline workout(s)",
        "synced_ids": synced_ids,
    }), 200
