import json
from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.orm import relationship

from .database import Base


class Household(Base):
    __tablename__ = "households"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    profiles = relationship("Profile", back_populates="household")


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True)
    household_id = Column(Integer, ForeignKey("households.id"), nullable=False)
    name = Column(String(255), nullable=False)
    date_of_birth = Column(Date, nullable=True)
    developmental_stage = Column(String(50), default="adult")
    sex_reference = Column(String(50), default="unspecified")
    height_cm = Column(Float, nullable=True)
    weight_kg = Column(Float, nullable=True)
    activity_baseline = Column(String(50), default="moderate")
    sport_preferences = Column(Text, default="[]")
    allergies = Column(Text, default="[]")
    intolerances = Column(Text, default="[]")
    disliked_ingredients = Column(Text, default="[]")
    dietary_preferences = Column(Text, default="[]")
    medical_considerations = Column(Text, default="[]")
    pregnancy_status = Column(Boolean, default=False)
    pregnancy_trimester = Column(Integer, nullable=True)
    pre_pregnancy_weight_kg = Column(Float, nullable=True)
    current_pregnancy_weight_kg = Column(Float, nullable=True)
    breastfeeding_status = Column(Boolean, default=False)
    exclusive_breastfeeding = Column(Boolean, default=False)
    mixed_feeding = Column(Boolean, default=False)
    breastfeeding_beyond_six_months = Column(Boolean, default=False)
    custom_diet = Column(Text, default="[]")
    usenote = Column(Text, default="")
    avatar_data = Column(LargeBinary, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    household = relationship("Household", back_populates="profiles")
    measurements = relationship("MeasurementRecord", back_populates="profile", cascade="all, delete-orphan")
    activities = relationship("ActivityRecord", back_populates="profile", cascade="all, delete-orphan")

    @staticmethod
    def _serialize_list(value):
        if value is None:
            return "[]"
        if isinstance(value, str):
            return value
        return json.dumps(value)

    @staticmethod
    def _deserialize_list(value):
        if not value:
            return []
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return [item.strip() for item in str(value).split(",") if item.strip()]

    @property
    def allergy_list(self):
        return self._deserialize_list(self.allergies)

    @property
    def intolerance_list(self):
        return self._deserialize_list(self.intolerances)

    @property
    def disliked_ingredient_list(self):
        return self._deserialize_list(self.disliked_ingredients)

    @property
    def dietary_preference_list(self):
        return self._deserialize_list(self.dietary_preferences)

    @property
    def custom_diet_list(self):
        return self._deserialize_list(self.custom_diet)


class MeasurementRecord(Base):
    __tablename__ = "measurement_records"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    date = Column(Date, nullable=False)
    height_cm = Column(Float, nullable=True)
    weight_kg = Column(Float, nullable=True)
    notes = Column(Text, default="")

    profile = relationship("Profile", back_populates="measurements")


class ActivityRecord(Base):
    __tablename__ = "activity_records"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    date = Column(Date, nullable=False)
    sport_type = Column(String(100), nullable=False)
    duration_minutes = Column(Float, nullable=False, default=0)
    intensity = Column(String(50), default="moderate")
    notes = Column(Text, default="")

    profile = relationship("Profile", back_populates="activities")


class Ingredient(Base):
    __tablename__ = "ingredients"

    id = Column(Integer, primary_key=True, index=True)
    common_name = Column(String(255), nullable=False)
    alternative_names = Column(Text, default="[]")
    english_name = Column(String(255), default="")
    local_name = Column(String(255), default="")
    food_category = Column(String(100), nullable=False)
    edible_portion = Column(Float, default=1.0)
    preparation_state = Column(String(100), default="raw")
    energy_kcal_per_100g = Column(Float, default=0)
    protein_g_per_100g = Column(Float, default=0)
    carbohydrates_g_per_100g = Column(Float, default=0)
    fat_g_per_100g = Column(Float, default=0)
    fiber_g_per_100g = Column(Float, default=0)
    iron_mg_per_100g = Column(Float, default=0)
    calcium_mg_per_100g = Column(Float, default=0)
    vitamin_a_ug_per_100g = Column(Float, default=0)
    vitamin_c_mg_per_100g = Column(Float, default=0)
    vitamin_d_ug_per_100g = Column(Float, default=0)
    folate_ug_per_100g = Column(Float, default=0)
    potassium_mg_per_100g = Column(Float, default=0)
    zinc_mg_per_100g = Column(Float, default=0)
    sodium_mg_per_100g = Column(Float, default=0)
    water_ml_per_100g = Column(Float, default=0)
    source = Column(String(255), default="local")
    data_quality = Column(String(50), default="manual")
    license = Column(String(255), default="local")
    last_update = Column(Date, default=datetime.utcnow)


class MealPlan(Base):
    __tablename__ = "meal_plans"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    date = Column(Date, nullable=False)
    meal_type = Column(String(50), default="main")
    title = Column(String(255), default="")
    notes = Column(Text, default="")


class MealPlanItem(Base):
    __tablename__ = "meal_plan_items"

    id = Column(Integer, primary_key=True, index=True)
    meal_plan_id = Column(Integer, ForeignKey("meal_plans.id"), nullable=False)
    ingredient_name = Column(String(255), nullable=False)
    quantity_g = Column(Float, default=0)
