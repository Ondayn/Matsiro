import json
from datetime import date

from .models import ActivityRecord, Household, Ingredient, MeasurementRecord, Profile


def _json_list(values):
    return json.dumps(list(values)) if values else "[]"


def ensure_seed_data(session):
    household = session.query(Household).first()
    if household is None:
        household = Household(name="Matsiro Family")
        session.add(household)
        session.commit()
        session.refresh(household)

    profile = session.query(Profile).filter(Profile.name == "Amina").first()
    if profile is None:
        profile = Profile(
            household_id=household.id,
            name="Amina",
            date_of_birth=date(1991, 5, 12),
            developmental_stage="adult",
            sex_reference="female",
            height_cm=165,
            weight_kg=62,
            activity_baseline="moderate",
            sport_preferences=_json_list(["walking", "dancing"]),
            allergies=_json_list(["peanut"]),
            intolerances=_json_list([]),
            disliked_ingredients=_json_list(["eggplant"]),
            dietary_preferences=_json_list(["vegetarian"]),
            medical_considerations=_json_list([]),
            custom_diet=_json_list([]),
            usenote="Active family meal planner",
        )
        session.add(profile)
        session.commit()
        session.refresh(profile)

        session.add(MeasurementRecord(profile_id=profile.id, date=date.today(), height_cm=165, weight_kg=62))
        session.add(ActivityRecord(profile_id=profile.id, date=date.today(), sport_type="walking", duration_minutes=35, intensity="moderate", notes="Evening walk"))
        session.commit()

    if session.query(Ingredient).count() == 0:
        base_ingredients = [
            {
                "common_name": "Brown rice",
                "alternative_names": ["whole grain rice", "brown rice cooked"],
                "english_name": "Brown rice",
                "local_name": "Mchele",
                "food_category": "staple grain",
                "edible_portion": 1.0,
                "preparation_state": "boiled",
                "energy_kcal_per_100g": 111,
                "protein_g_per_100g": 2.6,
                "carbohydrates_g_per_100g": 23.5,
                "fat_g_per_100g": 0.9,
                "fiber_g_per_100g": 1.8,
                "iron_mg_per_100g": 0.8,
                "calcium_mg_per_100g": 10,
                "vitamin_a_ug_per_100g": 0,
                "vitamin_c_mg_per_100g": 0,
                "vitamin_d_ug_per_100g": 0,
                "folate_ug_per_100g": 9,
                "potassium_mg_per_100g": 115,
                "zinc_mg_per_100g": 1.0,
                "sodium_mg_per_100g": 1,
                "water_ml_per_100g": 68,
                "source": "local seed database",
                "data_quality": "manual",
                "license": "local",
            },
            {
                "common_name": "Beans",
                "alternative_names": ["common beans", "kidney beans"],
                "english_name": "Beans",
                "local_name": "Mahindi",
                "food_category": "legume",
                "edible_portion": 1.0,
                "preparation_state": "boiled",
                "energy_kcal_per_100g": 132,
                "protein_g_per_100g": 8.7,
                "carbohydrates_g_per_100g": 22.8,
                "fat_g_per_100g": 0.5,
                "fiber_g_per_100g": 7.9,
                "iron_mg_per_100g": 2.9,
                "calcium_mg_per_100g": 46,
                "vitamin_a_ug_per_100g": 1,
                "vitamin_c_mg_per_100g": 1.5,
                "vitamin_d_ug_per_100g": 0,
                "folate_ug_per_100g": 130,
                "potassium_mg_per_100g": 291,
                "zinc_mg_per_100g": 1.2,
                "sodium_mg_per_100g": 13,
                "water_ml_per_100g": 74,
                "source": "local seed database",
                "data_quality": "manual",
                "license": "local",
            },
            {
                "common_name": "Chicken breast",
                "alternative_names": ["poultry breast", "chicken"],
                "english_name": "Chicken breast",
                "local_name": "Nyama ya kuku",
                "food_category": "protein",
                "edible_portion": 1.0,
                "preparation_state": "grilled",
                "energy_kcal_per_100g": 165,
                "protein_g_per_100g": 31.0,
                "carbohydrates_g_per_100g": 0,
                "fat_g_per_100g": 3.6,
                "fiber_g_per_100g": 0,
                "iron_mg_per_100g": 1.1,
                "calcium_mg_per_100g": 11,
                "vitamin_a_ug_per_100g": 8,
                "vitamin_c_mg_per_100g": 0,
                "vitamin_d_ug_per_100g": 0.3,
                "folate_ug_per_100g": 6,
                "potassium_mg_per_100g": 256,
                "zinc_mg_per_100g": 1.0,
                "sodium_mg_per_100g": 74,
                "water_ml_per_100g": 75,
                "source": "local seed database",
                "data_quality": "manual",
                "license": "local",
            },
            {
                "common_name": "Spinach",
                "alternative_names": ["leafy greens"],
                "english_name": "Spinach",
                "local_name": "Sukuma wiki",
                "food_category": "vegetable",
                "edible_portion": 1.0,
                "preparation_state": "steamed",
                "energy_kcal_per_100g": 23,
                "protein_g_per_100g": 2.9,
                "carbohydrates_g_per_100g": 3.6,
                "fat_g_per_100g": 0.4,
                "fiber_g_per_100g": 2.2,
                "iron_mg_per_100g": 2.7,
                "calcium_mg_per_100g": 99,
                "vitamin_a_ug_per_100g": 469,
                "vitamin_c_mg_per_100g": 28.1,
                "vitamin_d_ug_per_100g": 0,
                "folate_ug_per_100g": 194,
                "potassium_mg_per_100g": 558,
                "zinc_mg_per_100g": 0.5,
                "sodium_mg_per_100g": 79,
                "water_ml_per_100g": 91,
                "source": "local seed database",
                "data_quality": "manual",
                "license": "local",
            },
            {
                "common_name": "Banana",
                "alternative_names": ["plantain"],
                "english_name": "Banana",
                "local_name": "Ndizi",
                "food_category": "fruit",
                "edible_portion": 1.0,
                "preparation_state": "raw",
                "energy_kcal_per_100g": 89,
                "protein_g_per_100g": 1.1,
                "carbohydrates_g_per_100g": 22.8,
                "fat_g_per_100g": 0.3,
                "fiber_g_per_100g": 2.6,
                "iron_mg_per_100g": 0.3,
                "calcium_mg_per_100g": 5,
                "vitamin_a_ug_per_100g": 3,
                "vitamin_c_mg_per_100g": 8.7,
                "vitamin_d_ug_per_100g": 0,
                "folate_ug_per_100g": 20,
                "potassium_mg_per_100g": 358,
                "zinc_mg_per_100g": 0.2,
                "sodium_mg_per_100g": 1,
                "water_ml_per_100g": 75,
                "source": "local seed database",
                "data_quality": "manual",
                "license": "local",
            },
            {
                "common_name": "Cassava",
                "alternative_names": ["manioc", "yuca"],
                "english_name": "Cassava",
                "local_name": "Mihogo",
                "food_category": "staple root",
                "edible_portion": 1.0,
                "preparation_state": "boiled",
                "energy_kcal_per_100g": 160,
                "protein_g_per_100g": 1.4,
                "carbohydrates_g_per_100g": 38.1,
                "fat_g_per_100g": 0.3,
                "fiber_g_per_100g": 1.8,
                "iron_mg_per_100g": 0.3,
                "calcium_mg_per_100g": 16,
                "vitamin_a_ug_per_100g": 0,
                "vitamin_c_mg_per_100g": 20.6,
                "vitamin_d_ug_per_100g": 0,
                "folate_ug_per_100g": 27,
                "potassium_mg_per_100g": 271,
                "zinc_mg_per_100g": 0.3,
                "sodium_mg_per_100g": 14,
                "water_ml_per_100g": 60,
                "source": "local seed database",
                "data_quality": "manual",
                "license": "local",
            },
        ]
        for payload in base_ingredients:
            ingredient = Ingredient(**payload)
            ingredient.alternative_names = _json_list(payload.get("alternative_names", []))
            session.add(ingredient)
        session.commit()

    return household
