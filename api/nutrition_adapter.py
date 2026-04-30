"""
FitTrack Pro - External Nutrition API Adapter
api/nutrition_adapter.py

Port: NutritionAPIPort
Adapter: Edamam Food Database API with requests-cache fallback.

When the external API is unavailable or the key is not configured,
the adapter falls back to a built-in food database so the app
always returns usable nutrition data.

Architecture note:
    This is the "external nutrition-data adapter" described in the
    Ports-and-Adapters architecture. The PyQt6 client and Flask routes
    both call get_nutrition_info() — they never hit the network directly.
"""

import os
import logging
from typing import Optional

try:
    import requests
    import requests_cache
    # Cache responses for 1 hour to avoid hammering the external API
    requests_cache.install_cache(
        "fittrack_nutrition_cache",
        backend="memory",
        expire_after=3600,
    )
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

logger = logging.getLogger(__name__)

# ── Built-in fallback food database ──────────────────────────────────────────
# Format: food_name_lower -> {calories, protein_g, carbs_g, fat_g, unit}
FALLBACK_FOOD_DB = {
    "oatmeal":                  {"calories": 350, "protein_g": 12, "carbs_g": 58, "fat_g": 7,  "unit": "bowl"},
    "grilled chicken breast":   {"calories": 165, "protein_g": 31, "carbs_g": 0,  "fat_g": 3.6,"unit": "100g"},
    "grilled chicken salad":    {"calories": 480, "protein_g": 42, "carbs_g": 22, "fat_g": 18, "unit": "plate"},
    "salmon with vegetables":   {"calories": 520, "protein_g": 38, "carbs_g": 30, "fat_g": 22, "unit": "plate"},
    "greek yogurt":             {"calories": 130, "protein_g": 17, "carbs_g": 9,  "fat_g": 0.7,"unit": "cup"},
    "protein bar":              {"calories": 220, "protein_g": 20, "carbs_g": 25, "fat_g": 6,  "unit": "bar"},
    "brown rice":               {"calories": 215, "protein_g": 5,  "carbs_g": 45, "fat_g": 2,  "unit": "cup"},
    "eggs":                     {"calories": 78,  "protein_g": 6,  "carbs_g": 0.6,"fat_g": 5,  "unit": "egg"},
    "banana":                   {"calories": 105, "protein_g": 1,  "carbs_g": 27, "fat_g": 0,  "unit": "medium"},
    "almonds":                  {"calories": 174, "protein_g": 6,  "carbs_g": 6,  "fat_g": 15, "unit": "30g"},
    "whole wheat bread":        {"calories": 80,  "protein_g": 4,  "carbs_g": 15, "fat_g": 1,  "unit": "slice"},
    "milk":                     {"calories": 149, "protein_g": 8,  "carbs_g": 12, "fat_g": 8,  "unit": "250ml"},
    "apple":                    {"calories": 80,  "protein_g": 0.4,"carbs_g": 21, "fat_g": 0.3,"unit": "medium"},
    "lentil soup":              {"calories": 310, "protein_g": 18, "carbs_g": 48, "fat_g": 5,  "unit": "bowl"},
    "pasta":                    {"calories": 220, "protein_g": 8,  "carbs_g": 43, "fat_g": 1.3,"unit": "cup"},
    "pizza":                    {"calories": 285, "protein_g": 12, "carbs_g": 36, "fat_g": 10, "unit": "slice"},
    "burger":                   {"calories": 540, "protein_g": 34, "carbs_g": 40, "fat_g": 27, "unit": "burger"},
    "orange juice":             {"calories": 110, "protein_g": 2,  "carbs_g": 26, "fat_g": 0,  "unit": "250ml"},
    "coffee":                   {"calories": 5,   "protein_g": 0.3,"carbs_g": 1,  "fat_g": 0,  "unit": "cup"},
    "rice":                     {"calories": 200, "protein_g": 4,  "carbs_g": 44, "fat_g": 0.4,"unit": "cup"},
    "tuna":                     {"calories": 132, "protein_g": 29, "carbs_g": 0,  "fat_g": 1,  "unit": "100g"},
    "avocado":                  {"calories": 240, "protein_g": 3,  "carbs_g": 13, "fat_g": 22, "unit": "medium"},
    "sweet potato":             {"calories": 103, "protein_g": 2,  "carbs_g": 24, "fat_g": 0.1,"unit": "medium"},
    "spinach":                  {"calories": 23,  "protein_g": 3,  "carbs_g": 3.6,"fat_g": 0.4,"unit": "cup"},
    "broccoli":                 {"calories": 55,  "protein_g": 4,  "carbs_g": 11, "fat_g": 0.6,"unit": "cup"},
}


def _fuzzy_lookup(food_name: str) -> Optional[dict]:
    """
    Try to find a match in the fallback DB by checking if any key
    is contained in the food_name or vice versa.
    """
    name_lower = food_name.lower().strip()
    # Exact match first
    if name_lower in FALLBACK_FOOD_DB:
        return FALLBACK_FOOD_DB[name_lower]
    # Partial match
    for key, data in FALLBACK_FOOD_DB.items():
        if key in name_lower or name_lower in key:
            return data
    return None


def get_nutrition_info(food_name: str, quantity: float = 1.0) -> dict:
    """
    Main entry point. Returns nutrition info for a food item.

    Priority:
      1. External Edamam API (when key configured and network available)
      2. requests-cache (if same request was made recently)
      3. Built-in fallback food database

    Returns:
        dict with keys: food_name, calories, protein_g, carbs_g, fat_g,
                        unit, source ("api" | "cache" | "fallback")
    """
    api_key = os.environ.get("NUTRITION_API_KEY", "")
    api_id  = os.environ.get("NUTRITION_APP_ID", "")

    # ── Try external API ──────────────────────────────────────────────────────
    if REQUESTS_AVAILABLE and api_key and api_id:
        try:
            resp = requests.get(
                "https://api.edamam.com/api/food-database/v2/parser",
                params={
                    "ingr": food_name,
                    "app_id": api_id,
                    "app_key": api_key,
                    "nutrition-type": "logging",
                },
                timeout=5,
            )
            if resp.status_code == 200:
                hints = resp.json().get("hints", [])
                if hints:
                    food = hints[0].get("food", {})
                    nutrients = food.get("nutrients", {})
                    cal = round(nutrients.get("ENERC_KCAL", 0) * quantity, 1)
                    source = "cache" if getattr(resp, "from_cache", False) else "api"
                    return {
                        "food_name": food.get("label", food_name),
                        "calories":  cal,
                        "protein_g": round(nutrients.get("PROCNT", 0) * quantity, 1),
                        "carbs_g":   round(nutrients.get("CHOCDF", 0) * quantity, 1),
                        "fat_g":     round(nutrients.get("FAT", 0) * quantity, 1),
                        "unit":      "100g",
                        "source":    source,
                    }
        except Exception as exc:
            logger.warning("Nutrition API request failed: %s — using fallback", exc)

    # ── Fallback to built-in database ─────────────────────────────────────────
    data = _fuzzy_lookup(food_name)
    if data:
        return {
            "food_name": food_name,
            "calories":  round(data["calories"] * quantity, 1),
            "protein_g": round(data["protein_g"] * quantity, 1),
            "carbs_g":   round(data["carbs_g"] * quantity, 1),
            "fat_g":     round(data["fat_g"] * quantity, 1),
            "unit":      data.get("unit", "serving"),
            "source":    "fallback",
        }

    # ── Unknown food — return zeros so callers don't break ────────────────────
    logger.info("Food '%s' not found in API or fallback DB", food_name)
    return {
        "food_name": food_name,
        "calories":  0.0,
        "protein_g": 0.0,
        "carbs_g":   0.0,
        "fat_g":     0.0,
        "unit":      "serving",
        "source":    "fallback",
    }


def search_foods(query: str, max_results: int = 10) -> list:
    """
    Return a list of food suggestions for the given query string.
    Used by the nutrition auto-complete in the PyQt6 client.
    """
    results = []
    query_lower = query.lower()

    for name, data in FALLBACK_FOOD_DB.items():
        if query_lower in name:
            results.append({
                "food_name": name.title(),
                "calories":  data["calories"],
                "protein_g": data["protein_g"],
                "carbs_g":   data["carbs_g"],
                "fat_g":     data["fat_g"],
                "unit":      data["unit"],
            })
        if len(results) >= max_results:
            break

    return results
