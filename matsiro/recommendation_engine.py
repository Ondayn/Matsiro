from __future__ import annotations

import random
from typing import Iterable, List, Optional

from .models import Ingredient, Profile


CATEGORY_KEYWORDS = {
    "carbohydrates": ["grain", "staple", "cassava", "rice", "potato", "maize", "cereal", "bread", "pasta", "sorghum"],
    "protein": ["bean", "lentil", "pea", "egg", "fish", "chicken", "tofu", "beef", "milk", "yogurt", "legume", "protein"],
    "vegetables": ["vegetable", "leafy", "spinach", "cabbage", "carrot", "tomato", "onion", "broccoli", "pepper"],
    "fruit": ["fruit", "apple", "banana", "mango", "orange", "pineapple", "avocado", "pear"],
}


def _normalize(value):
    if value is None:
        return ""
    return str(value).strip().lower()


def _as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    text = str(value).strip()
    if not text:
        return []
    if text.startswith("["):
        try:
            parsed = __import__("json").loads(text)
            return parsed if isinstance(parsed, list) else [parsed]
        except Exception:
            pass
    return [item.strip() for item in text.split(",") if item.strip()]


def _build_allergen_set(profile: Profile, household_profiles: Optional[Iterable[Profile]] = None) -> set:
    blocked = set()
    for item in profile.allergy_list + profile.intolerance_list + profile.custom_diet_list:
        blocked.add(_normalize(item))
    if household_profiles:
        for member in household_profiles:
            if member.id == profile.id:
                continue
            for item in member.allergy_list:
                blocked.add(_normalize(item))
    return blocked


def recommend_meal(
    profile: Profile,
    ingredients: Iterable[Ingredient],
    previous_meals: Optional[List[str]] = None,
    household_profiles: Optional[Iterable[Profile]] = None,
) -> dict:
    previous = { _normalize(name) for name in (previous_meals or []) }
    allergen_set = _build_allergen_set(profile, household_profiles)
    disliked = { _normalize(item) for item in profile.disliked_ingredient_list }
    ingredient_list = list(ingredients)

    suggested = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        options = []
        for ingredient in ingredient_list:
            name = _normalize(ingredient.common_name)
            alt_names = [_normalize(item) for item in _as_list(ingredient.alternative_names)]
            combined = {name, *alt_names}
            if combined & allergen_set:
                continue
            if name in disliked or any(item in disliked for item in combined):
                continue
            category_text = _normalize(ingredient.food_category)
            if any(keyword in category_text or keyword in name for keyword in keywords):
                options.append(ingredient)
        if not options:
            continue

        scored = []
        for ingredient in options:
            score = 10
            ingredient_name = _normalize(ingredient.common_name)
            alt_names = [_normalize(item) for item in _as_list(ingredient.alternative_names)]
            if ingredient_name in previous or any(item in previous for item in alt_names):
                score -= 6
            if str(ingredient.preparation_state).lower() in {"raw", "boiled"}:
                score += 2
            if str(ingredient.food_category).lower() in {"fruit", "vegetable"}:
                score += 1
            scored.append((score, ingredient))
        chosen = max(scored, key=lambda item: item[0])[1]
        suggested[category] = {
            "name": chosen.common_name,
            "category": chosen.food_category,
            "preparation": chosen.preparation_state,
            "energy_kcal": chosen.energy_kcal_per_100g,
            "protein_g": chosen.protein_g_per_100g,
        }

    if not suggested:
        return {
            "title": "No suggestions available",
            "items": [],
            "message": "Try adding more ingredients or remove restrictions for this profile.",
        }

    meal_title = "Family meal suggestion"
    items = [
        {"category": key, "name": value["name"], "preparation": value["preparation"], "category_label": value["category"]}
        for key, value in suggested.items()
    ]
    return {
        "title": meal_title,
        "items": items,
        "message": "This recommendation respects strict exclusions, avoids repeated ingredients, and keeps the plan flexible for family participation.",
    }
