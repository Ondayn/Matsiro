import json
from datetime import date

import pandas as pd
import streamlit as st

from matsiro.database import SessionLocal, init_db
from matsiro.models import ActivityRecord, Household, Ingredient, MeasurementRecord, Profile
from matsiro.nutrition_engine import calculate_daily_requirements, list_requirement_rows
from matsiro.recommendation_engine import recommend_meal
from matsiro.seed_data import ensure_seed_data


st.set_page_config(page_title="Matsiro", page_icon="🥗", layout="wide")


def get_or_create_household(session):
    household = session.query(Household).first()
    if household is None:
        household = Household(name="Matsiro Family")
        session.add(household)
        session.commit()
        session.refresh(household)
    return household


def parse_list_field(raw_value):
    if raw_value is None:
        return []
    if isinstance(raw_value, list):
        return raw_value
    if isinstance(raw_value, str):
        value = raw_value.strip()
        if not value:
            return []
        if value.startswith("["):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass
        return [item.strip() for item in value.split(",") if item.strip()]
    return [str(raw_value)]


def save_profile(session, profile_id=None, **payload):
    if profile_id:
        profile = session.query(Profile).get(profile_id)
        if profile is None:
            return None
        for key, value in payload.items():
            setattr(profile, key, value)
    else:
        profile = Profile(**payload)
        session.add(profile)
    session.commit()
    return profile


def render_household_tab(session):
    household = get_or_create_household(session)
    st.subheader("Household overview")
    st.write(f"Household: {household.name}")
    with st.form("household_form"):
        name = st.text_input("Update household name", value=household.name)
        submitted = st.form_submit_button("Save household")
        if submitted:
            household.name = name
            session.commit()
            st.success("Household saved")


def render_profiles_tab(session):
    profiles = session.query(Profile).order_by(Profile.id).all()
    st.subheader("Profiles")
    with st.form("profile_form"):
        name = st.text_input("Name")
        birth_date = st.date_input("Date of birth", value=date(2000, 1, 1))
        stage = st.selectbox("Developmental stage", ["baby", "child", "adolescent", "adult", "older adult"])
        sex = st.selectbox("Sex-related nutritional reference", ["female", "male", "unspecified"])
        height_cm = st.number_input("Height (cm)", min_value=0.0, value=165.0, step=1.0)
        weight_kg = st.number_input("Weight (kg)", min_value=0.0, value=60.0, step=0.5)
        activity = st.selectbox("Activity baseline", ["sedentary", "light", "moderate", "active", "very_active"])
        submitted = st.form_submit_button("Add profile")
        if submitted and name:
            save_profile(
                session,
                name=name,
                household_id=get_or_create_household(session).id,
                date_of_birth=birth_date,
                developmental_stage=stage,
                sex_reference=sex,
                height_cm=float(height_cm),
                weight_kg=float(weight_kg),
                activity_baseline=activity,
                sport_preferences="[]",
                allergies="[]",
                intolerances="[]",
                disliked_ingredients="[]",
                dietary_preferences="[]",
                medical_considerations="[]",
                custom_diet="[]",
                usenote="",
            )
            st.success(f"Added profile: {name}")

    if profiles:
        for profile in profiles:
            with st.expander(f"{profile.name} ({profile.developmental_stage})"):
                st.write(f"Age: {round((date.today() - profile.date_of_birth).days / 365.25, 1)} years" if profile.date_of_birth else "Age not specified")
                st.write(f"Activity baseline: {profile.activity_baseline}")
                st.write(f"Allergies: {', '.join(parse_list_field(profile.allergies)) or 'None'}")
                st.write(f"Dislikes: {', '.join(parse_list_field(profile.disliked_ingredients)) or 'None'}")
                with st.form(f"edit_profile_{profile.id}"):
                    new_name = st.text_input("Name", value=profile.name, key=f"name_{profile.id}")
                    new_stage = st.selectbox("Developmental stage", ["baby", "child", "adolescent", "adult", "older adult"], index=["baby", "child", "adolescent", "adult", "older adult"].index(profile.developmental_stage), key=f"stage_{profile.id}")
                    new_sex = st.selectbox("Sex-related nutritional reference", ["female", "male", "unspecified"], index=["female", "male", "unspecified"].index(profile.sex_reference), key=f"sex_{profile.id}")
                    new_height = st.number_input("Height (cm)", value=float(profile.height_cm or 165), min_value=0.0, key=f"height_{profile.id}")
                    new_weight = st.number_input("Weight (kg)", value=float(profile.weight_kg or 60), min_value=0.0, key=f"weight_{profile.id}")
                    new_activity = st.selectbox("Activity baseline", ["sedentary", "light", "moderate", "active", "very_active"], index=["sedentary", "light", "moderate", "active", "very_active"].index(profile.activity_baseline), key=f"activity_{profile.id}")
                    new_allergies = st.text_input("Allergies (comma separated)", value=", ".join(parse_list_field(profile.allergies)), key=f"allergies_{profile.id}")
                    new_dislikes = st.text_input("Dislikes", value=", ".join(parse_list_field(profile.disliked_ingredients)), key=f"dislikes_{profile.id}")
                    save = st.form_submit_button("Update profile")
                    if save:
                        profile.name = new_name
                        profile.developmental_stage = new_stage
                        profile.sex_reference = new_sex
                        profile.height_cm = float(new_height)
                        profile.weight_kg = float(new_weight)
                        profile.activity_baseline = new_activity
                        profile.allergies = json.dumps([item.strip() for item in new_allergies.split(",") if item.strip()])
                        profile.disliked_ingredients = json.dumps([item.strip() for item in new_dislikes.split(",") if item.strip()])
                        session.commit()
                        st.success("Profile updated")


def render_measurements_tab(session):
    profiles = session.query(Profile).order_by(Profile.id).all()
    if not profiles:
        st.info("Add at least one profile first.")
        return
    profile = st.selectbox("Profile", profiles, format_func=lambda item: item.name)
    with st.form("measurement_form"):
        date_value = st.date_input("Measurement date", value=date.today())
        height = st.number_input("Height (cm)", min_value=0.0, value=float(profile.height_cm or 165), step=1.0)
        weight = st.number_input("Weight (kg)", min_value=0.0, value=float(profile.weight_kg or 60), step=0.5)
        notes = st.text_area("Notes")
        submitted = st.form_submit_button("Save measurement")
        if submitted:
            session.add(MeasurementRecord(profile_id=profile.id, date=date_value, height_cm=float(height), weight_kg=float(weight), notes=notes))
            session.commit()
            st.success("Measurement saved")

    history = session.query(MeasurementRecord).filter(MeasurementRecord.profile_id == profile.id).order_by(MeasurementRecord.date.desc()).all()
    if history:
        st.subheader("Measurement history")
        st.dataframe(pd.DataFrame([
            {"date": item.date.isoformat(), "height_cm": item.height_cm, "weight_kg": item.weight_kg, "notes": item.notes}
            for item in history
        ]))


def render_activities_tab(session):
    profiles = session.query(Profile).order_by(Profile.id).all()
    if not profiles:
        st.info("Add at least one profile first.")
        return
    profile = st.selectbox("Profile", profiles, format_func=lambda item: item.name, key="activity_profile")
    with st.form("activity_form"):
        activity_date = st.date_input("Date", value=date.today())
        sport_type = st.selectbox("Sport type", ["Walking", "Running", "Swimming", "Cycling", "Dancing", "Football", "Basketball", "Strength training", "Other"])
        duration = st.number_input("Duration (minutes)", min_value=0, value=30, step=5)
        intensity = st.selectbox("Intensity", ["low", "moderate", "high", "vigorous"])
        notes = st.text_area("Notes")
        submitted = st.form_submit_button("Save activity")
        if submitted:
            session.add(ActivityRecord(profile_id=profile.id, date=activity_date, sport_type=sport_type, duration_minutes=float(duration), intensity=intensity, notes=notes))
            session.commit()
            st.success("Activity saved")

    records = session.query(ActivityRecord).filter(ActivityRecord.profile_id == profile.id).order_by(ActivityRecord.date.desc()).all()
    if records:
        st.subheader("Exercise history")
        st.dataframe(pd.DataFrame([
            {"date": item.date.isoformat(), "sport": item.sport_type, "minutes": item.duration_minutes, "intensity": item.intensity, "notes": item.notes}
            for item in records
        ]))


def render_ingredients_tab(session):
    st.subheader("Ingredient database")
    with st.form("ingredient_form"):
        common_name = st.text_input("Common name")
        alt_names = st.text_input("Alternative names (comma separated)")
        english_name = st.text_input("English name")
        local_name = st.text_input("Local name")
        food_category = st.selectbox("Food category", ["staple grain", "legume", "protein", "vegetable", "fruit", "root", "dairy", "other"])
        preparation_state = st.selectbox("Preparation state", ["raw", "boiled", "roasted", "dried", "steamed", "grilled"])
        energy = st.number_input("Energy (kcal/100 g)", value=0.0)
        protein = st.number_input("Protein (g/100 g)", value=0.0)
        carb = st.number_input("Carbohydrates (g/100 g)", value=0.0)
        fat = st.number_input("Fat (g/100 g)", value=0.0)
        fiber = st.number_input("Fiber (g/100 g)", value=0.0)
        iron = st.number_input("Iron (mg/100 g)", value=0.0)
        calcium = st.number_input("Calcium (mg/100 g)", value=0.0)
        submitted = st.form_submit_button("Add ingredient")
        if submitted and common_name:
            ingredient = Ingredient(
                common_name=common_name,
                alternative_names=json.dumps([item.strip() for item in alt_names.split(",") if item.strip()]),
                english_name=english_name,
                local_name=local_name,
                food_category=food_category,
                preparation_state=preparation_state,
                energy_kcal_per_100g=float(energy),
                protein_g_per_100g=float(protein),
                carbohydrates_g_per_100g=float(carb),
                fat_g_per_100g=float(fat),
                fiber_g_per_100g=float(fiber),
                iron_mg_per_100g=float(iron),
                calcium_mg_per_100g=float(calcium),
            )
            session.add(ingredient)
            session.commit()
            st.success(f"Added ingredient: {common_name}")

    ingredients = session.query(Ingredient).order_by(Ingredient.common_name).all()
    if ingredients:
        st.dataframe(pd.DataFrame([
            {"name": item.common_name, "category": item.food_category, "state": item.preparation_state, "energy_kcal": item.energy_kcal_per_100g}
            for item in ingredients
        ]))


def render_meal_plan_tab(session):
    profiles = session.query(Profile).order_by(Profile.id).all()
    if not profiles:
        st.info("Create at least one profile before planning meals.")
        return
    profile = st.selectbox("Profile", profiles, format_func=lambda item: item.name, key="meal_profile")
    ingredients = session.query(Ingredient).all()
    previous_meals = st.text_input("Previous meal ingredients (comma separated)" )
    if st.button("Generate recommendation"):
        recommendation = recommend_meal(
            profile=profile,
            ingredients=ingredients,
            previous_meals=[item.strip() for item in previous_meals.split(",") if item.strip()],
            household_profiles=session.query(Profile).all(),
        )
        st.subheader(recommendation["title"])
        for item in recommendation["items"]:
            st.markdown(f"- {item['category']}: **{item['name']}** ({item['preparation']})")
        st.write(recommendation["message"])


def render_dashboard_tab(session):
    profiles = session.query(Profile).order_by(Profile.id).all()
    if not profiles:
        st.info("No profiles yet.")
        return
    selected = st.selectbox("View requirements for", profiles, format_func=lambda item: item.name)
    activities = session.query(ActivityRecord).filter(ActivityRecord.profile_id == selected.id).all()
    requirements = calculate_daily_requirements(selected, activities)
    rows = list_requirement_rows(selected, activities)
    st.subheader(f"Daily nutrition requirements for {selected.name}")
    st.write(requirements["method"])
    st.write(requirements["reference_source"])
    st.dataframe(pd.DataFrame(rows))

    chart_data = pd.DataFrame(rows)
    if not chart_data.empty:
        chart_data = chart_data[chart_data["metric"].isin(["Energy Kcal", "Protein G", "Carbohydrates G", "Fiber G"])].copy()
        st.bar_chart(chart_data.set_index("metric")["value"])


def main():
    init_db()
    session = SessionLocal()
    ensure_seed_data(session)

    st.title("Matsiro")
    st.caption("Offline-first family nutrition planning and healthy living support")

    tabs = st.tabs(["Household", "Profiles", "Measurements", "Activity", "Ingredients", "Meal planner", "Dashboard"])
    with tabs[0]:
        render_household_tab(session)
    with tabs[1]:
        render_profiles_tab(session)
    with tabs[2]:
        render_measurements_tab(session)
    with tabs[3]:
        render_activities_tab(session)
    with tabs[4]:
        render_ingredients_tab(session)
    with tabs[5]:
        render_meal_plan_tab(session)
    with tabs[6]:
        render_dashboard_tab(session)

    session.close()


if __name__ == "__main__":
    main()
