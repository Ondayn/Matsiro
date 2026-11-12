from __future__ import annotations

import random
import re
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
            if member is profile or (profile.id is not None and member.id == profile.id):
                continue
            for item in member.allergy_list + member.intolerance_list + member.custom_diet_list:
                blocked.add(_normalize(item))
    return blocked


def _dietary_preference_allows(ingredient: Ingredient, profiles: Iterable[Profile]) -> bool:
    ingredient_text = " ".join(
        [
            _normalize(ingredient.common_name),
            _normalize(ingredient.food_category),
            *[_normalize(item) for item in _as_list(ingredient.alternative_names)],
        ]
    )
    land_meat = ("beef", "pork", "chicken", "turkey", "lamb", "goat", "bacon", "ham", "sausage")
    fish_and_seafood = ("fish", "salmon", "tuna", "shrimp", "prawn", "seafood", "anchovy")
    dairy = ("milk", "cheese", "butter", "cream", "yogurt", "yoghurt", "whey", "casein")
    gluten = ("wheat", "barley", "rye", "malt", "semolina", "bulgur", "couscous")

    def contains_any(terms):
        return any(
            re.search(rf"\b{re.escape(term)}\b", ingredient_text)
            for term in terms
        )

    for member in profiles:
        preferences = {_normalize(item) for item in member.dietary_preference_list}
        is_vegan = "vegan" in preferences or "plant-based" in preferences or "plant based" in preferences
        is_vegetarian = is_vegan or "vegetarian" in preferences
        is_pescatarian = "pescatarian" in preferences

        if (is_vegetarian or is_pescatarian) and contains_any(land_meat):
            return False
        if is_vegetarian and not is_pescatarian and contains_any(fish_and_seafood):
            return False
        if is_vegan and contains_any((*dairy, "egg", "honey", "gelatin")):
            return False
        if any("gluten-free" in preference or "gluten free" in preference for preference in preferences):
            if contains_any(gluten):
                return False
        if any(
            "dairy-free" in preference or "dairy free" in preference or "lactose-free" in preference
            for preference in preferences
        ) and contains_any(dairy):
            return False

    return True


def recommend_ingredient(
    profile: Profile,
    ingredients: Iterable[Ingredient],
    category: str,
    previous_meals: Optional[List[str]] = None,
    household_profiles: Optional[Iterable[Profile]] = None,
    exclude_names: Optional[Iterable[str]] = None,
) -> Optional[dict]:
    category_key = category if category in CATEGORY_KEYWORDS else next(
        (
            key
            for key, category_keywords in CATEGORY_KEYWORDS.items()
            if any(keyword in _normalize(category) for keyword in category_keywords)
        ),
        None,
    )
    keywords = CATEGORY_KEYWORDS.get(category_key)
    if not keywords:
        return None

    previous = {_normalize(name) for name in (previous_meals or [])}
    excluded = {_normalize(name) for name in (exclude_names or [])}
    blocked = _build_allergen_set(profile, household_profiles)
    disliked = {_normalize(item) for item in profile.disliked_ingredient_list}
    preference_profiles = list(household_profiles or [])
    if all(member is not profile for member in preference_profiles):
        preference_profiles.append(profile)
    scored = []

    for ingredient in ingredients:
        name = _normalize(ingredient.common_name)
        alternative_names = [_normalize(item) for item in _as_list(ingredient.alternative_names)]
        combined = {name, *alternative_names}
        if combined & (blocked | disliked | excluded):
            continue
        if not _dietary_preference_allows(ingredient, preference_profiles):
            continue

        category_text = _normalize(ingredient.food_category)
        if not any(keyword in category_text or keyword in name for keyword in keywords):
            continue

        score = 10
        if name in previous or any(item in previous for item in alternative_names):
            score -= 6
        if str(ingredient.preparation_state).lower() in {"raw", "boiled"}:
            score += 2
        if str(ingredient.food_category).lower() in {"fruit", "vegetable"}:
            score += 1
        scored.append((score, ingredient))

    if not scored:
        return None

    best_score = max(score for score, _ in scored)
    chosen = random.choice([ingredient for score, ingredient in scored if score == best_score])
    return {
        "category": category_key,
        "name": chosen.common_name,
        "preparation": chosen.preparation_state,
        "category_label": chosen.food_category,
        "energy_kcal": chosen.energy_kcal_per_100g,
        "protein_g": chosen.protein_g_per_100g,
    }


def recommend_meal(
    profile: Profile,
    ingredients: Iterable[Ingredient],
    previous_meals: Optional[List[str]] = None,
    household_profiles: Optional[Iterable[Profile]] = None,
) -> dict:
    ingredient_list = list(ingredients)
    suggested = {}
    for category in CATEGORY_KEYWORDS:
        selection = recommend_ingredient(
            profile=profile,
            ingredients=ingredient_list,
            category=category,
            previous_meals=previous_meals,
            household_profiles=household_profiles,
        )
        if selection:
            suggested[category] = selection

    if not suggested:
        return {
            "title": "No suggestions available",
            "items": [],
            "message": "Try adding more ingredients or remove restrictions for this profile.",
        }

    meal_title = "Family meal suggestion"
    items = list(suggested.values())
    return {
        "title": meal_title,
        "items": items,
        "message": "This recommendation respects strict exclusions, avoids repeated ingredients, and keeps the plan flexible for family participation.",
    }
