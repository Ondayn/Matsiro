from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field


class HouseholdCreate(BaseModel):
    name: str = Field(..., min_length=1)


class ProfileCreate(BaseModel):
    name: str = Field(..., min_length=1)
    household_id: int
    date_of_birth: Optional[date] = None
    developmental_stage: str = "adult"
    sex_reference: str = "unspecified"
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    activity_baseline: str = "moderate"
    sport_preferences: List[str] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)
    intolerances: List[str] = Field(default_factory=list)
    disliked_ingredients: List[str] = Field(default_factory=list)
    dietary_preferences: List[str] = Field(default_factory=list)
    medical_considerations: List[str] = Field(default_factory=list)
    pregnancy_status: bool = False
    pregnancy_trimester: Optional[int] = None
    pre_pregnancy_weight_kg: Optional[float] = None
    current_pregnancy_weight_kg: Optional[float] = None
    breastfeeding_status: bool = False
    exclusive_breastfeeding: bool = False
    mixed_feeding: bool = False
    breastfeeding_beyond_six_months: bool = False
    custom_diet: List[str] = Field(default_factory=list)
    notes: str = ""


class MeasurementCreate(BaseModel):
    profile_id: int
    date: date
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    notes: str = ""


class ActivityCreate(BaseModel):
    profile_id: int
    date: date
    sport_type: str
    duration_minutes: float = 0
    intensity: str = "moderate"
    notes: str = ""


class IngredientCreate(BaseModel):
    common_name: str
    alternative_names: List[str] = Field(default_factory=list)
    english_name: str = ""
    local_name: str = ""
    food_category: str
    edible_portion: float = 1.0
    preparation_state: str = "raw"
    energy_kcal_per_100g: float = 0.0
    protein_g_per_100g: float = 0.0
    carbohydrates_g_per_100g: float = 0.0
    fat_g_per_100g: float = 0.0
    fiber_g_per_100g: float = 0.0
    iron_mg_per_100g: float = 0.0
    calcium_mg_per_100g: float = 0.0
    vitamin_a_ug_per_100g: float = 0.0
    vitamin_c_mg_per_100g: float = 0.0
    vitamin_d_ug_per_100g: float = 0.0
    folate_ug_per_100g: float = 0.0
    potassium_mg_per_100g: float = 0.0
    zinc_mg_per_100g: float = 0.0
    sodium_mg_per_100g: float = 0.0
    water_ml_per_100g: float = 0.0
    source: str = "local"
    data_quality: str = "manual"
    license: str = "local"
