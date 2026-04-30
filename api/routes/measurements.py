"""
FitTrack Pro - Body Measurements Routes
GET    /api/measurements           List measurements
POST   /api/measurements           Log measurement (auto-updates linked goals)
GET    /api/measurements/<id>      Get single measurement
PUT    /api/measurements/<id>      Update measurement
DELETE /api/measurements/<id>      Delete measurement
"""

from datetime import date
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from api import db
from api.models import BodyMeasurement, FitnessGoal

measurements_bp = Blueprint("measurements", __name__)


@measurements_bp.route("", methods=["GET"])
@jwt_required()
def list_measurements():
    user_id = int(get_jwt_identity())
    measurements = (
        BodyMeasurement.query.filter_by(user_id=user_id)
        .order_by(BodyMeasurement.date.desc())
        .all()
    )
    return jsonify({"measurements": [m.to_dict() for m in measurements]}), 200


@measurements_bp.route("", methods=["POST"])
@jwt_required()
def add_measurement():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    try:
        meas_date = date.fromisoformat(data["date"]) if data.get("date") else date.today()
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 422

    meas = BodyMeasurement(
        user_id=user_id,
        date=meas_date,
        weight_kg=data.get("weight_kg"),
        body_fat_percent=data.get("body_fat_percent"),
        muscle_mass_kg=data.get("muscle_mass_kg"),
        chest_cm=data.get("chest_cm"),
        waist_cm=data.get("waist_cm"),
        hips_cm=data.get("hips_cm"),
        notes=data.get("notes"),
    )
    db.session.add(meas)
    db.session.flush()

    # Auto-update weight-based fitness goals
    if meas.weight_kg:
        weight_goals = FitnessGoal.query.filter(
            FitnessGoal.user_id == user_id,
            FitnessGoal.is_completed == False,
            FitnessGoal.goal_type.in_(["Lose Weight", "Gain Muscle", "Maintain Weight"]),
        ).all()
        for goal in weight_goals:
            goal.current_value = meas.weight_kg
            # Auto-complete if target reached
            if goal.goal_type == "Lose Weight" and meas.weight_kg <= (goal.target_value or 0):
                goal.is_completed = True
            elif goal.goal_type == "Gain Muscle" and meas.weight_kg >= (goal.target_value or 9999):
                goal.is_completed = True

    db.session.commit()
    return jsonify({
        "message": "Measurement saved",
        "measurement": meas.to_dict(),
    }), 201


@measurements_bp.route("/<int:meas_id>", methods=["GET"])
@jwt_required()
def get_measurement(meas_id):
    user_id = int(get_jwt_identity())
    meas = BodyMeasurement.query.filter_by(id=meas_id, user_id=user_id).first_or_404()
    return jsonify({"measurement": meas.to_dict()}), 200


@measurements_bp.route("/<int:meas_id>", methods=["PUT"])
@jwt_required()
def update_measurement(meas_id):
    user_id = int(get_jwt_identity())
    meas = BodyMeasurement.query.filter_by(id=meas_id, user_id=user_id).first_or_404()
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    for field in ["weight_kg", "body_fat_percent", "muscle_mass_kg",
                  "chest_cm", "waist_cm", "hips_cm", "notes"]:
        if field in data:
            setattr(meas, field, data[field])
    if "date" in data:
        try:
            meas.date = date.fromisoformat(data["date"])
        except ValueError:
            return jsonify({"error": "Invalid date format"}), 422

    db.session.commit()
    return jsonify({"message": "Measurement updated", "measurement": meas.to_dict()}), 200


@measurements_bp.route("/<int:meas_id>", methods=["DELETE"])
@jwt_required()
def delete_measurement(meas_id):
    user_id = int(get_jwt_identity())
    meas = BodyMeasurement.query.filter_by(id=meas_id, user_id=user_id).first_or_404()
    db.session.delete(meas)
    db.session.commit()
    return jsonify({"message": "Measurement deleted"}), 200
