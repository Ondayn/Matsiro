from __future__ import annotations

from datetime import date
from typing import Iterable, Optional

from .models import ActivityRecord, Profile


METRIC_KEYS = [
    "energy_kcal",
    "protein_g",
    "carbohydrates_g",
    "fat_g",
    "fiber_g",
    "iron_mg",
    "calcium_mg",
    "vitamin_a_ug",
    "vitamin_c_mg",
    "vitamin_d_ug",
    "folate_ug",
    "potassium_mg",
    "zinc_mg",
    "sodium_mg",
    "hydration_liters",
]


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _age_years(profile: Profile) -> float:
    if not profile.date_of_birth:
        return 30.0
    today = date.today()
    years = (today - profile.date_of_birth).days / 365.25
    return max(0.0, years)


def _latest_measurement(profile: Profile) -> dict:
    measurement = None
    for item in profile.measurements:
        if measurement is None or item.date > measurement.date:
            measurement = item
    if measurement is None:
        return {"height_cm": profile.height_cm, "weight_kg": profile.weight_kg}
    return {
        "height_cm": measurement.height_cm or profile.height_cm,
        "weight_kg": measurement.weight_kg or profile.weight_kg,
    }


def _stage_name(profile: Profile) -> str:
    label = str(profile.developmental_stage or "adult").lower().strip()
    if label in {"baby", "infant"}:
        return "infant"
    if label in {"child", "young_child"}:
        return "child"
    if label in {"adolescent", "teen"}:
        return "adolescent"
    if label in {"older adult", "older_adult", "senior"}:
        return "older_adult"
    return "adult"


def _effective_weight(profile: Profile, latest_measurement: dict) -> float:
    if profile.pregnancy_status and profile.current_pregnancy_weight_kg:
        return _safe_float(profile.current_pregnancy_weight_kg, _safe_float(latest_measurement.get("weight_kg"), 60.0))
    if profile.pregnancy_status and profile.pre_pregnancy_weight_kg:
        return _safe_float(profile.pre_pregnancy_weight_kg, _safe_float(latest_measurement.get("weight_kg"), 60.0))
    if latest_measurement.get("weight_kg"):
        return _safe_float(latest_measurement.get("weight_kg"), _safe_float(profile.weight_kg, 60.0))
    return _safe_float(profile.weight_kg, 60.0)


def _effective_height(profile: Profile, latest_measurement: dict) -> float:
    if latest_measurement.get("height_cm"):
        return _safe_float(latest_measurement.get("height_cm"), _safe_float(profile.height_cm, 165.0))
    return _safe_float(profile.height_cm, 165.0)


def _activity_factor(profile: Profile) -> float:
    mapping = {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725,
        "very_active": 1.9,
    }
    return mapping.get(str(profile.activity_baseline).lower(), 1.55)


def _sport_multiplier(sport_name: str, intensity: str) -> float:
    sport = (sport_name or "").lower()
    intensity_map = {
        "low": 0.8,
        "moderate": 1.0,
        "high": 1.3,
        "vigorous": 1.5,
    }
    multiplier = intensity_map.get((intensity or "moderate").lower(), 1.0)
    if "walking" in sport:
        return 0.9 * multiplier
    if "running" in sport:
        return 1.4 * multiplier
    if "swimming" in sport:
        return 1.3 * multiplier
    if "cycling" in sport:
        return 1.2 * multiplier
    if "football" in sport or "basketball" in sport:
        return 1.35 * multiplier
    if "strength" in sport:
        return 1.2 * multiplier
    if "dance" in sport:
        return 1.0 * multiplier
    return 1.0 * multiplier


def _exercise_minutes(activities: Optional[Iterable[ActivityRecord]]) -> float:
    total = 0.0
    if not activities:
        return total
    for activity in activities:
        total += _safe_float(getattr(activity, "duration_minutes", 0), 0.0)
    return total


def _exercise_energy_top_up(weight_kg: float, exercise_minutes: float) -> float:
    if exercise_minutes <= 0:
        return 0.0
    return max(0.0, weight_kg * 0.02 * (exercise_minutes / 30.0))


def _daily_exercise_adjustment(profile: Profile, activities: Optional[Iterable[ActivityRecord]]) -> float:
    minutes = _exercise_minutes(activities)
    if minutes <= 0:
        return 1.0
    sex_bias = 1.08 if str(profile.sex_reference).lower() == "female" else 1.10
    return sex_bias + (minutes / 180.0) * 0.12


def calculate_daily_requirements(profile: Profile, activities: Optional[Iterable[ActivityRecord]] = None) -> dict:
    """Generate a modular daily nutrition estimate from available profile data."""
    measurements = _latest_measurement(profile)
    weight_kg = _effective_weight(profile, measurements)
    height_cm = _effective_height(profile, measurements)
    age = _age_years(profile)
    stage = _stage_name(profile)
    sex = str(profile.sex_reference or "unspecified").lower()
    pal = _activity_factor(profile)
    exercise_minutes = _exercise_minutes(activities)
    exercise_multiplier = _daily_exercise_adjustment(profile, activities)
    exercise_top_up = _exercise_energy_top_up(weight_kg, exercise_minutes)

    notes = []
    if profile.pregnancy_status:
        notes.append("Pregnancy adjustments applied using trimester-specific energy and micronutrient increases.")
    if profile.breastfeeding_status:
        notes.append("Breastfeeding adjustments applied for lactation energy and protein needs.")
    if stage in {"child", "adolescent"}:
        notes.append("Pediatric growth-related patterns used instead of adult BMI-based estimates.")
    if exercise_minutes:
        notes.append("Recorded activity was considered as a modest top-up to daily energy needs without double-counting baseline activity.")

    if age < 1:
        energy_kcal = max(550.0, 95.0 * weight_kg)
        protein_g = max(9.0, 1.6 * weight_kg)
        carbs_g = 0.50 * energy_kcal / 4.0
        fat_g = 0.35 * energy_kcal / 9.0
        fiber_g = 5.0
    elif age < 3:
        energy_kcal = max(700.0, 82.0 * weight_kg)
        protein_g = max(13.0, 1.8 * weight_kg)
        carbs_g = 0.55 * energy_kcal / 4.0
        fat_g = 0.30 * energy_kcal / 9.0
        fiber_g = 10.0
    elif age < 10:
        energy_kcal = max(1200.0, 70.0 * weight_kg)
        protein_g = max(18.0, 1.5 * weight_kg)
        carbs_g = 0.52 * energy_kcal / 4.0
        fat_g = 0.30 * energy_kcal / 9.0
        fiber_g = 15.0
    elif age < 18:
        energy_kcal = max(1400.0, 55.0 * weight_kg)
        protein_g = max(35.0, 1.2 * weight_kg)
        carbs_g = 0.50 * energy_kcal / 4.0
        fat_g = 0.30 * energy_kcal / 9.0
        fiber_g = max(18.0, 0.2 * weight_kg)
    else:
        sex_offset = 5 if sex == "male" else -161
        if sex == "unspecified":
            sex_offset = 0
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + sex_offset
        energy_kcal = bmr * pal * exercise_multiplier
        protein_g = max(45.0, 1.2 * weight_kg)
        carbs_g = 0.50 * energy_kcal / 4.0
        fat_g = 0.30 * energy_kcal / 9.0
        fiber_g = 25.0 if sex == "female" else 30.0

    if profile.pregnancy_status:
        trimester = profile.pregnancy_trimester or 2
        extra_kcal = 180 if trimester < 2 else 340 if trimester < 3 else 452
        energy_kcal += extra_kcal
        protein_g += 10.0
        if profile.current_pregnancy_weight_kg:
            weight_kg = max(weight_kg, _safe_float(profile.current_pregnancy_weight_kg, weight_kg))
    if profile.breastfeeding_status:
        energy_kcal += 330 if profile.exclusive_breastfeeding or profile.mixed_feeding else 250
        protein_g += 10.0

    energy_kcal += exercise_top_up

    if age >= 18:
        iron_mg = 27.0 if profile.pregnancy_status else 18.0 if sex == "female" else 8.0
    elif age < 10:
        iron_mg = 7.0
    elif age < 14:
        iron_mg = 8.0
    else:
        iron_mg = 11.0

    if age >= 18 and profile.breastfeeding_status:
        iron_mg = max(iron_mg, 9.0)

    calcium_mg = 1000.0 if age >= 18 else 800.0
    if stage in {"child", "adolescent"}:
        calcium_mg = 1000.0 if age >= 9 else 800.0
    vitamin_a_ug = 700.0 if sex == "female" else 900.0
    if stage in {"child", "adolescent"}:
        vitamin_a_ug = 400.0 if age < 9 else 600.0
    vitamin_c_mg = 75.0 if sex == "female" else 90.0
    vitamin_d_ug = 15.0
    folate_ug = 400.0
    potassium_mg = 2600.0
    zinc_mg = 8.0 if sex == "female" else 11.0
    sodium_mg = 1500.0
    hydration_liters = max(1.5, 0.035 * weight_kg)

    if profile.pregnancy_status:
        calcium_mg = max(calcium_mg, 1000.0)
        folate_ug = max(folate_ug, 600.0)
        iron_mg = max(iron_mg, 27.0)
    if profile.breastfeeding_status:
        folate_ug = max(folate_ug, 500.0)
        vitamin_a_ug = max(vitamin_a_ug, 1200.0)

    result = {
        "energy_kcal": round(energy_kcal, 1),
        "protein_g": round(protein_g, 1),
        "carbohydrates_g": round(carbs_g, 1),
        "fat_g": round(fat_g, 1),
        "fiber_g": round(fiber_g, 1),
        "iron_mg": round(iron_mg, 1),
        "calcium_mg": round(calcium_mg, 1),
        "vitamin_a_ug": round(vitamin_a_ug, 1),
        "vitamin_c_mg": round(vitamin_c_mg, 1),
        "vitamin_d_ug": round(vitamin_d_ug, 1),
        "folate_ug": round(folate_ug, 1),
        "potassium_mg": round(potassium_mg, 1),
        "zinc_mg": round(zinc_mg, 1),
        "sodium_mg": round(sodium_mg, 1),
        "hydration_liters": round(hydration_liters, 2),
        "method": "Offline modular nutrition model using age-appropriate growth and activity estimates",
        "reference_source": "WHO/FAO/INFOODS-informed references with local heuristics for offline use",
        "date": date.today().isoformat(),
        "uncertainty": "Moderate. Clinical review is recommended for medical conditions, atypical growth, or pregnancy/lactation planning.",
        "notes": notes,
        "adjustments": {
            "baseline_activity_factor": round(pal, 3),
            "exercise_minutes": round(exercise_minutes, 1),
            "exercise_top_up_kcal": round(exercise_top_up, 1),
            "pregnancy_status": bool(profile.pregnancy_status),
            "breastfeeding_status": bool(profile.breastfeeding_status),
        },
    }
    return result


def list_requirement_rows(profile: Profile, activities: Optional[Iterable[ActivityRecord]] = None):
    requirements = calculate_daily_requirements(profile, activities)
    rows = []
    for key in METRIC_KEYS:
        label = key.replace("_", " ").replace("kg", "kg").title()
        rows.append({"metric": label, "value": requirements.get(key, 0), "unit": _unit_for_key(key)})
    return rows


def _unit_for_key(key: str) -> str:
    mapping = {
        "energy_kcal": "kcal",
        "protein_g": "g",
        "carbohydrates_g": "g",
        "fat_g": "g",
        "fiber_g": "g",
        "iron_mg": "mg",
        "calcium_mg": "mg",
        "vitamin_a_ug": "µg",
        "vitamin_c_mg": "mg",
        "vitamin_d_ug": "µg",
        "folate_ug": "µg",
        "potassium_mg": "mg",
        "zinc_mg": "mg",
        "sodium_mg": "mg",
        "hydration_liters": "L",
    }
    return mapping.get(key, "")
