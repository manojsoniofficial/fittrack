"""
FitTrack Pro - Coach Routes
GET  /api/coach/clients                  List coach's clients
GET  /api/coach/clients/<id>/summary     Client progress summary
POST /api/coach/clients/<id>/report      Generate & export report
"""

from datetime import date, timedelta
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from api import db
from api.models import User, WorkoutSession, MealEntry, BodyMeasurement, ProgressReport

coach_bp = Blueprint("coach", __name__)


def _require_coach():
    user_id = int(get_jwt_identity())
    user = User.query.get_or_404(user_id)
    if user.role != "coach":
        return None, (jsonify({"error": "Coach role required"}), 403)
    return user, None


@coach_bp.route("/clients", methods=["GET"])
@jwt_required()
def list_clients():
    coach, err = _require_coach()
    if err:
        return err

    clients = User.query.filter_by(coach_id=coach.id, is_active=True).all()
    return jsonify({"clients": [c.to_dict() for c in clients]}), 200


@coach_bp.route("/clients/<int:client_id>/summary", methods=["GET"])
@jwt_required()
def client_summary(client_id):
    coach, err = _require_coach()
    if err:
        return err

    client = User.query.filter_by(id=client_id, coach_id=coach.id).first_or_404()

    today = date.today()
    month_start = today.replace(day=1)

    workouts = WorkoutSession.query.filter(
        WorkoutSession.user_id == client_id,
        WorkoutSession.date >= month_start,
    ).all()

    meals = MealEntry.query.filter(
        MealEntry.user_id == client_id,
        MealEntry.date >= month_start,
    ).all()

    measurements = BodyMeasurement.query.filter(
        BodyMeasurement.user_id == client_id,
        BodyMeasurement.weight_kg.isnot(None),
    ).order_by(BodyMeasurement.date.desc()).limit(2).all()

    weight_change = 0.0
    if len(measurements) == 2:
        weight_change = round(measurements[0].weight_kg - measurements[1].weight_kg, 2)

    num_days = max((today - month_start).days, 1)

    return jsonify({
        "client": client.to_dict(),
        "this_month": {
            "total_workouts": len(workouts),
            "total_workout_minutes": sum(w.duration_minutes or 0 for w in workouts),
            "total_calories_burned": round(sum(w.calories_burned or 0 for w in workouts), 1),
            "avg_daily_calories_in": round(sum(m.calories for m in meals) / num_days, 1),
            "weight_change_kg": weight_change,
        },
        "recent_workouts": [w.to_dict() for w in
                            WorkoutSession.query.filter_by(user_id=client_id)
                            .order_by(WorkoutSession.date.desc()).limit(5).all()],
    }), 200


@coach_bp.route("/clients/<int:client_id>/report", methods=["POST"])
@jwt_required()
def generate_client_report(client_id):
    coach, err = _require_coach()
    if err:
        return err

    client = User.query.filter_by(id=client_id, coach_id=coach.id).first_or_404()
    data = request.get_json() or {}

    end_date = date.fromisoformat(data.get("end_date", date.today().isoformat()))
    start_date = date.fromisoformat(
        data.get("start_date", (end_date - timedelta(days=30)).isoformat())
    )

    workouts = WorkoutSession.query.filter(
        WorkoutSession.user_id == client_id,
        WorkoutSession.date >= start_date,
        WorkoutSession.date <= end_date,
    ).all()

    meals = MealEntry.query.filter(
        MealEntry.user_id == client_id,
        MealEntry.date >= start_date,
        MealEntry.date <= end_date,
    ).all()

    measurements = BodyMeasurement.query.filter(
        BodyMeasurement.user_id == client_id,
        BodyMeasurement.date >= start_date,
        BodyMeasurement.date <= end_date,
        BodyMeasurement.weight_kg.isnot(None),
    ).order_by(BodyMeasurement.date).all()

    weight_change = 0.0
    if len(measurements) >= 2:
        weight_change = round(measurements[-1].weight_kg - measurements[0].weight_kg, 2)

    num_days = max((end_date - start_date).days, 1)

    report = ProgressReport(
        user_id=client_id,
        generated_by=coach.id,
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

    return jsonify({
        "message": "Client report generated",
        "client": client.to_dict(),
        "report": report.to_dict(),
    }), 201
