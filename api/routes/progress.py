"""
FitTrack Pro - Progress Routes
GET /api/progress/users/<user_id>/progress   Weekly progress summary
GET /api/progress/users/<user_id>/report     Generate full progress report
"""

from datetime import date, timedelta
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from api import db
from api.models import User, WorkoutSession, MealEntry, BodyMeasurement, ProgressReport

progress_bp = Blueprint("progress", __name__)


@progress_bp.route("/users/<int:user_id>/progress", methods=["GET"])
@jwt_required()
def get_progress(user_id):
    """
    Get weekly progress summary for a user.
    The caller must be the user or their coach.
    """
    caller_id = int(get_jwt_identity())
    caller = User.query.get_or_404(caller_id)

    # Authorisation: self or coach
    target = User.query.get_or_404(user_id)
    if caller_id != user_id and caller.role != "coach" and target.coach_id != caller_id:
        return jsonify({"error": "Forbidden"}), 403

    # Parse date range
    end_date = date.fromisoformat(request.args.get("end_date", date.today().isoformat()))
    start_date = date.fromisoformat(
        request.args.get("start_date", (end_date - timedelta(days=7)).isoformat())
    )

    workouts = WorkoutSession.query.filter(
        WorkoutSession.user_id == user_id,
        WorkoutSession.date >= start_date,
        WorkoutSession.date <= end_date,
    ).all()

    meals = MealEntry.query.filter(
        MealEntry.user_id == user_id,
        MealEntry.date >= start_date,
        MealEntry.date <= end_date,
    ).all()

    # Weight data
    measurements = BodyMeasurement.query.filter(
        BodyMeasurement.user_id == user_id,
        BodyMeasurement.date >= start_date,
        BodyMeasurement.date <= end_date,
        BodyMeasurement.weight_kg.isnot(None),
    ).order_by(BodyMeasurement.date).all()

    weight_change = 0.0
    if len(measurements) >= 2:
        weight_change = round(measurements[-1].weight_kg - measurements[0].weight_kg, 2)

    num_days = max((end_date - start_date).days, 1)
    total_cal_in = sum(m.calories for m in meals)

    return jsonify({
        "user_id": user_id,
        "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
        "total_workouts": len(workouts),
        "total_workout_minutes": sum(w.duration_minutes or 0 for w in workouts),
        "total_calories_burned": round(sum(w.calories_burned or 0 for w in workouts), 1),
        "avg_daily_calories_in": round(total_cal_in / num_days, 1),
        "weight_change_kg": weight_change,
        "workout_types": list({w.activity_type for w in workouts}),
    }), 200


@progress_bp.route("/users/<int:user_id>/report", methods=["POST"])
@jwt_required()
def generate_report(user_id):
    """Generate and persist a ProgressReport for a user over a date range."""
    caller_id = int(get_jwt_identity())
    caller = User.query.get_or_404(caller_id)

    if caller_id != user_id and caller.role != "coach":
        return jsonify({"error": "Forbidden"}), 403

    data = request.get_json() or {}
    end_date = date.fromisoformat(data.get("end_date", date.today().isoformat()))
    start_date = date.fromisoformat(
        data.get("start_date", (end_date - timedelta(days=30)).isoformat())
    )

    workouts = WorkoutSession.query.filter(
        WorkoutSession.user_id == user_id,
        WorkoutSession.date >= start_date,
        WorkoutSession.date <= end_date,
    ).all()

    meals = MealEntry.query.filter(
        MealEntry.user_id == user_id,
        MealEntry.date >= start_date,
        MealEntry.date <= end_date,
    ).all()

    measurements = BodyMeasurement.query.filter(
        BodyMeasurement.user_id == user_id,
        BodyMeasurement.date >= start_date,
        BodyMeasurement.date <= end_date,
        BodyMeasurement.weight_kg.isnot(None),
    ).order_by(BodyMeasurement.date).all()

    weight_change = 0.0
    if len(measurements) >= 2:
        weight_change = round(measurements[-1].weight_kg - measurements[0].weight_kg, 2)

    num_days = max((end_date - start_date).days, 1)

    report = ProgressReport(
        user_id=user_id,
        generated_by=caller_id,
        period_start=start_date,
        period_end=end_date,
        total_workouts=len(workouts),
        total_workout_minutes=sum(w.duration_minutes or 0 for w in workouts),
        total_calories_burned=round(sum(w.calories_burned or 0 for w in workouts), 1),
        avg_daily_calories_in=round(sum(m.calories for m in meals) / num_days, 1),
        weight_change_kg=weight_change,
    )
    db.session.add(report)
    db.session.commit()

    return jsonify({"message": "Report generated", "report": report.to_dict()}), 201
