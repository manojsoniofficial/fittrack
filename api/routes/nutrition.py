"""
FitTrack Pro - Nutrition Routes
GET    /api/nutrition              List meals for a date
POST   /api/nutrition              Log a meal
GET    /api/nutrition/summary      Daily macro summary
GET    /api/nutrition/search       Search food nutrition (adapter + cache fallback)
PUT    /api/nutrition/<id>         Update meal
DELETE /api/nutrition/<id>         Delete meal
POST   /api/nutrition/sync         Sync offline meals
"""

from datetime import date
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from api import db
from api.models import MealEntry
from api.nutrition_adapter import get_nutrition_info, search_foods

nutrition_bp = Blueprint("nutrition", __name__)


@nutrition_bp.route("", methods=["GET"])
@jwt_required()
def list_meals():
    user_id = int(get_jwt_identity())
    date_param = request.args.get("date")
    meal_type  = request.args.get("meal_type")

    query = MealEntry.query.filter_by(user_id=user_id)
    if date_param:
        try:
            query = query.filter(MealEntry.date == date.fromisoformat(date_param))
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 422
    if meal_type:
        query = query.filter(MealEntry.meal_type == meal_type)

    meals = query.order_by(MealEntry.date.desc(), MealEntry.created_at).all()
    return jsonify({"meals": [m.to_dict() for m in meals]}), 200


@nutrition_bp.route("", methods=["POST"])
@jwt_required()
def log_meal():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    for field in ["food_name", "meal_type"]:
        if not data.get(field):
            return jsonify({"error": f"Field '{field}' is required"}), 422

    qty = float(data.get("quantity", 1.0))

    # Auto-fetch nutrition via adapter (external API → cache → fallback DB)
    if data.get("calories") is None:
        nutrition  = get_nutrition_info(data["food_name"], quantity=qty)
        calories   = nutrition["calories"]
        protein_g  = nutrition["protein_g"]
        carbs_g    = nutrition["carbs_g"]
        fat_g      = nutrition["fat_g"]
    else:
        calories  = float(data["calories"])
        protein_g = float(data.get("protein_g", 0))
        carbs_g   = float(data.get("carbs_g", 0))
        fat_g     = float(data.get("fat_g", 0))

    try:
        meal_date = date.fromisoformat(data["date"]) if data.get("date") else date.today()
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 422

    meal = MealEntry(
        user_id=user_id,
        meal_type=data["meal_type"],
        date=meal_date,
        food_name=data["food_name"],
        quantity=qty,
        unit=data.get("unit", "serving"),
        calories=calories,
        protein_g=protein_g,
        carbs_g=carbs_g,
        fat_g=fat_g,
        is_synced=True,
    )
    db.session.add(meal)
    db.session.commit()
    return jsonify({"message": "Meal logged", "meal": meal.to_dict()}), 201


@nutrition_bp.route("/summary", methods=["GET"])
@jwt_required()
def daily_summary():
    user_id = int(get_jwt_identity())
    date_param = request.args.get("date", date.today().isoformat())
    try:
        target_date = date.fromisoformat(date_param)
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 422

    meals    = MealEntry.query.filter_by(user_id=user_id, date=target_date).all()
    by_type  = {}
    for m in meals:
        by_type.setdefault(m.meal_type, []).append(m.to_dict())

    return jsonify({
        "date":            target_date.isoformat(),
        "total_calories":  round(sum(m.calories for m in meals), 1),
        "total_protein_g": round(sum(m.protein_g or 0 for m in meals), 1),
        "total_carbs_g":   round(sum(m.carbs_g or 0 for m in meals), 1),
        "total_fat_g":     round(sum(m.fat_g or 0 for m in meals), 1),
        "meal_count":      len(meals),
        "meals_by_type":   by_type,
    }), 200


@nutrition_bp.route("/search", methods=["GET"])
@jwt_required()
def search_food():
    """
    Search food nutrition data.
    Queries Edamam API (requests-cache) → falls back to built-in DB.
    GET /api/nutrition/search?q=chicken&qty=1
    """
    query = request.args.get("q", "").strip()
    qty   = float(request.args.get("qty", 1.0))

    if not query or len(query) < 2:
        return jsonify({"error": "Query 'q' must be at least 2 characters"}), 422

    nutrition   = get_nutrition_info(query, quantity=qty)
    suggestions = search_foods(query, max_results=8)

    return jsonify({
        "query":       query,
        "quantity":    qty,
        "result":      nutrition,
        "suggestions": suggestions,
    }), 200


@nutrition_bp.route("/<int:meal_id>", methods=["GET"])
@jwt_required()
def get_meal(meal_id):
    user_id = int(get_jwt_identity())
    meal = MealEntry.query.filter_by(id=meal_id, user_id=user_id).first_or_404()
    return jsonify({"meal": meal.to_dict()}), 200


@nutrition_bp.route("/<int:meal_id>", methods=["PUT"])
@jwt_required()
def update_meal(meal_id):
    user_id = int(get_jwt_identity())
    meal = MealEntry.query.filter_by(id=meal_id, user_id=user_id).first_or_404()
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    for field in ["food_name", "meal_type", "quantity", "calories", "protein_g", "carbs_g", "fat_g"]:
        if field in data:
            setattr(meal, field, data[field])
    if "date" in data:
        try:
            meal.date = date.fromisoformat(data["date"])
        except ValueError:
            return jsonify({"error": "Invalid date format"}), 422

    db.session.commit()
    return jsonify({"message": "Meal updated", "meal": meal.to_dict()}), 200


@nutrition_bp.route("/<int:meal_id>", methods=["DELETE"])
@jwt_required()
def delete_meal(meal_id):
    user_id = int(get_jwt_identity())
    meal = MealEntry.query.filter_by(id=meal_id, user_id=user_id).first_or_404()
    db.session.delete(meal)
    db.session.commit()
    return jsonify({"message": "Meal deleted"}), 200


@nutrition_bp.route("/sync", methods=["POST"])
@jwt_required()
def sync_meals():
    """
    Offline sync endpoint.
    Accepts a list of meal entries created while offline (is_synced=False),
    persists them, and returns their new server-side IDs.
    """
    user_id = int(get_jwt_identity())
    data    = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    offline_meals = data.get("meals", [])
    if not isinstance(offline_meals, list):
        return jsonify({"error": "'meals' must be a list"}), 422

    synced_ids = []
    for m_data in offline_meals:
        try:
            meal_date = date.fromisoformat(m_data["date"]) if m_data.get("date") else date.today()
        except ValueError:
            meal_date = date.today()

        meal = MealEntry(
            user_id=user_id,
            meal_type=m_data.get("meal_type", "Snack"),
            date=meal_date,
            food_name=m_data.get("food_name", "Unknown"),
            quantity=float(m_data.get("quantity", 1.0)),
            unit=m_data.get("unit", "serving"),
            calories=float(m_data.get("calories", 0)),
            protein_g=float(m_data.get("protein_g", 0)),
            carbs_g=float(m_data.get("carbs_g", 0)),
            fat_g=float(m_data.get("fat_g", 0)),
            is_synced=True,
        )
        db.session.add(meal)
        db.session.flush()
        synced_ids.append(meal.id)

    db.session.commit()
    return jsonify({
        "message":    f"Synced {len(synced_ids)} meal(s)",
        "synced_ids": synced_ids,
    }), 200
