"""
FitTrack Pro - Goals Routes
"""
from datetime import date
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from api import db
from api.models import FitnessGoal

goals_bp = Blueprint("goals", __name__)


@goals_bp.route("", methods=["GET"])
@jwt_required()
def list_goals():
    user_id = int(get_jwt_identity())
    goals = FitnessGoal.query.filter_by(user_id=user_id).order_by(
        FitnessGoal.is_completed, FitnessGoal.target_date
    ).all()
    return jsonify({"goals": [g.to_dict() for g in goals]}), 200


@goals_bp.route("", methods=["POST"])
@jwt_required()
def create_goal():
    user_id = int(get_jwt_identity())
    data = request.get_json()

    if not data.get("goal_type"):
        return jsonify({"error": "goal_type is required"}), 422

    goal = FitnessGoal(
        user_id=user_id,
        goal_type=data["goal_type"],
        description=data.get("description"),
        target_value=data.get("target_value"),
        current_value=data.get("current_value"),
        unit=data.get("unit"),
        start_date=date.fromisoformat(data["start_date"]) if data.get("start_date") else date.today(),
        target_date=date.fromisoformat(data["target_date"]) if data.get("target_date") else None,
    )
    db.session.add(goal)
    db.session.commit()
    return jsonify({"message": "Goal created", "goal": goal.to_dict()}), 201


@goals_bp.route("/<int:goal_id>", methods=["PUT"])
@jwt_required()
def update_goal(goal_id):
    user_id = int(get_jwt_identity())
    goal = FitnessGoal.query.filter_by(id=goal_id, user_id=user_id).first_or_404()
    data = request.get_json()

    for field in ["goal_type", "description", "target_value", "current_value", "unit", "is_completed"]:
        if field in data:
            setattr(goal, field, data[field])
    if "target_date" in data:
        goal.target_date = date.fromisoformat(data["target_date"]) if data["target_date"] else None

    db.session.commit()
    return jsonify({"message": "Goal updated", "goal": goal.to_dict()}), 200


@goals_bp.route("/<int:goal_id>", methods=["DELETE"])
@jwt_required()
def delete_goal(goal_id):
    user_id = int(get_jwt_identity())
    goal = FitnessGoal.query.filter_by(id=goal_id, user_id=user_id).first_or_404()
    db.session.delete(goal)
    db.session.commit()
    return jsonify({"message": "Goal deleted"}), 200
