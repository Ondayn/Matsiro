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
    st.subheader("Profile management")

    with st.expander("Add new profile", expanded=False):
        with st.form("profile_form"):
            name = st.text_input("Name")
            birth_date = st.date_input("Date of birth", value=date(2000, 1, 1))
            stage = st.selectbox("Developmental stage", ["baby", "child", "adolescent", "adult", "older adult"])
            sex = st.selectbox("Sex-related nutritional reference", ["female", "male", "unspecified"])
            col_a, col_b = st.columns(2)
            with col_a:
                height_cm = st.number_input("Height (cm)", min_value=0.0, value=165.0, step=1.0)
                weight_kg = st.number_input("Weight (kg)", min_value=0.0, value=60.0, step=0.5)
            with col_b:
                activity = st.selectbox("Activity baseline", ["sedentary", "light", "moderate", "active", "very_active"])
                sport_preferences = st.text_input("Sport preferences (comma separated)", value="walking, dancing")
            allergies = st.text_input("Allergies (comma separated)", value="")
            intolerances = st.text_input("Food intolerances (comma separated)", value="")
            dislikes = st.text_input("Disliked ingredients (comma separated)", value="")
            dietary_preferences = st.text_input("Dietary preferences (comma separated)", value="")
            medical_considerations = st.text_input("Medical or nutritional considerations (comma separated)", value="")
            notes = st.text_area("Notes", value="")

            pregnancy_enabled = sex == "female" and st.checkbox("Pregnancy-related profile")
            if pregnancy_enabled:
                pregnancy_trimester = st.selectbox("Pregnancy trimester", [1, 2, 3], index=1)
                pre_pregnancy_weight = st.number_input("Pre-pregnancy weight (kg)", min_value=0.0, value=60.0, step=0.5)
                current_pregnancy_weight = st.number_input("Current pregnancy weight (kg)", min_value=0.0, value=62.0, step=0.5)
                breastfeeding_enabled = st.checkbox("Breastfeeding")
                if breastfeeding_enabled:
                    exclusive_breastfeeding = st.checkbox("Exclusive breastfeeding")
                    mixed_feeding = st.checkbox("Mixed feeding")
                    breastfeeding_beyond_six_months = st.checkbox("Breastfeeding beyond 6 months")
                else:
                    exclusive_breastfeeding = False
                    mixed_feeding = False
                    breastfeeding_beyond_six_months = False
            else:
                pregnancy_trimester = None
                pre_pregnancy_weight = None
                current_pregnancy_weight = None
                breastfeeding_enabled = False
                exclusive_breastfeeding = False
                mixed_feeding = False
                breastfeeding_beyond_six_months = False

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
                    sport_preferences=json.dumps([item.strip() for item in sport_preferences.split(",") if item.strip()]),
                    allergies=json.dumps([item.strip() for item in allergies.split(",") if item.strip()]),
                    intolerances=json.dumps([item.strip() for item in intolerances.split(",") if item.strip()]),
                    disliked_ingredients=json.dumps([item.strip() for item in dislikes.split(",") if item.strip()]),
                    dietary_preferences=json.dumps([item.strip() for item in dietary_preferences.split(",") if item.strip()]),
                    medical_considerations=json.dumps([item.strip() for item in medical_considerations.split(",") if item.strip()]),
                    custom_diet="[]",
                    pregnancy_status=pregnancy_enabled,
                    pregnancy_trimester=pregnancy_trimester if pregnancy_enabled else None,
                    pre_pregnancy_weight_kg=float(pre_pregnancy_weight) if pregnancy_enabled else None,
                    current_pregnancy_weight_kg=float(current_pregnancy_weight) if pregnancy_enabled else None,
                    breastfeeding_status=breastfeeding_enabled,
                    exclusive_breastfeeding=exclusive_breastfeeding,
                    mixed_feeding=mixed_feeding,
                    breastfeeding_beyond_six_months=breastfeeding_beyond_six_months,
                    usenote=notes,
                )
                st.success(f"Added profile: {name}")

    if not profiles:
        st.info("No profiles have been added yet.")
        return

    profile_ids = [profile.id for profile in profiles]
    last_selected = st.session_state.get("selected_profile_id")
    selected_id = last_selected if last_selected in profile_ids else profiles[0].id
    selected_profile = next(profile for profile in profiles if profile.id == selected_id)

    st.markdown("### Profile overview")
    cards = st.columns(min(3, len(profiles)))
    for index, profile in enumerate(profiles):
        with cards[index % len(cards)]:
            st.markdown(f"### {profile.name}")
            st.caption(f"{profile.developmental_stage or 'adult'} • {profile.sex_reference or 'unspecified'}")
            st.write(f"Age: {round((date.today() - profile.date_of_birth).days / 365.25, 1)} years" if profile.date_of_birth else "Age not specified")
            st.write(f"Height/Weight: {profile.height_cm or '-'} cm / {profile.weight_kg or '-'} kg")
            if st.button("Select", key=f"select_{profile.id}", use_container_width=True):
                st.session_state["selected_profile_id"] = profile.id
                selected_profile = profile

    st.markdown(f"### Editing: {selected_profile.name}")
    with st.form(f"edit_profile_{selected_profile.id}"):
        new_name = st.text_input("Name", value=selected_profile.name, key=f"name_{selected_profile.id}")
        new_stage = st.selectbox("Developmental stage", ["baby", "child", "adolescent", "adult", "older adult"], index=["baby", "child", "adolescent", "adult", "older adult"].index(selected_profile.developmental_stage or "adult"), key=f"stage_{selected_profile.id}")
        new_sex = st.selectbox("Sex-related nutritional reference", ["female", "male", "unspecified"], index=["female", "male", "unspecified"].index(selected_profile.sex_reference or "unspecified"), key=f"sex_{selected_profile.id}")

        field_col_a, field_col_b = st.columns(2)
        with field_col_a:
            new_height = st.number_input("Height (cm)", value=float(selected_profile.height_cm or 165), min_value=0.0, key=f"height_{selected_profile.id}")
            new_weight = st.number_input("Weight (kg)", value=float(selected_profile.weight_kg or 60), min_value=0.0, key=f"weight_{selected_profile.id}")
            new_activity = st.selectbox("Activity baseline", ["sedentary", "light", "moderate", "active", "very_active"], index=["sedentary", "light", "moderate", "active", "very_active"].index(selected_profile.activity_baseline or "moderate"), key=f"activity_{selected_profile.id}")
            new_sports = st.text_input("Sport preferences", value=", ".join(parse_list_field(selected_profile.sport_preferences)), key=f"sports_{selected_profile.id}")
        with field_col_b:
            new_allergies = st.text_input("Allergies (comma separated)", value=", ".join(parse_list_field(selected_profile.allergies)), key=f"allergies_{selected_profile.id}")
            new_intolerances = st.text_input("Intolerances", value=", ".join(parse_list_field(selected_profile.intolerances)), key=f"intolerances_{selected_profile.id}")
            new_dislikes = st.text_input("Dislikes", value=", ".join(parse_list_field(selected_profile.disliked_ingredients)), key=f"dislikes_{selected_profile.id}")
            new_preferences = st.text_input("Dietary preferences", value=", ".join(parse_list_field(selected_profile.dietary_preferences)), key=f"preferences_{selected_profile.id}")
            new_medical = st.text_input("Medical considerations", value=", ".join(parse_list_field(selected_profile.medical_considerations)), key=f"medical_{selected_profile.id}")

        pregnancy_value = st.checkbox("Pregnancy-related profile", value=bool(selected_profile.pregnancy_status), key=f"preg_{selected_profile.id}")
        if pregnancy_value or selected_profile.pregnancy_status:
            pregnancy_trimester = st.selectbox("Pregnancy trimester", [1, 2, 3], index=(selected_profile.pregnancy_trimester or 2) - 1, key=f"trimester_{selected_profile.id}")
            pre_preg_weight = st.number_input("Pre-pregnancy weight (kg)", value=float(selected_profile.pre_pregnancy_weight_kg or (selected_profile.weight_kg or 60)), min_value=0.0, key=f"prepreg_{selected_profile.id}")
            current_preg_weight = st.number_input("Current pregnancy weight (kg)", value=float(selected_profile.current_pregnancy_weight_kg or (selected_profile.weight_kg or 60)), min_value=0.0, key=f"currentpreg_{selected_profile.id}")
        else:
            pregnancy_trimester = None
            pre_preg_weight = None
            current_preg_weight = None

        breastfeeding_value = st.checkbox("Breastfeeding", value=bool(selected_profile.breastfeeding_status), key=f"breastfeeding_{selected_profile.id}")
        if breastfeeding_value:
            exclusive = st.checkbox("Exclusive breastfeeding", value=bool(selected_profile.exclusive_breastfeeding), key=f"exclusive_{selected_profile.id}")
            mixed = st.checkbox("Mixed feeding", value=bool(selected_profile.mixed_feeding), key=f"mixed_{selected_profile.id}")
            beyond = st.checkbox("Breastfeeding beyond 6 months", value=bool(selected_profile.breastfeeding_beyond_six_months), key=f"beyond_{selected_profile.id}")
        else:
            exclusive = False
            mixed = False
            beyond = False

        new_notes = st.text_area("Notes", value=selected_profile.usenote or "", key=f"notes_{selected_profile.id}")
        save = st.form_submit_button("Update profile")
        if save:
            selected_profile.name = new_name
            selected_profile.developmental_stage = new_stage
            selected_profile.sex_reference = new_sex
            selected_profile.height_cm = float(new_height)
            selected_profile.weight_kg = float(new_weight)
            selected_profile.activity_baseline = new_activity
            selected_profile.sport_preferences = json.dumps([item.strip() for item in new_sports.split(",") if item.strip()])
            selected_profile.allergies = json.dumps([item.strip() for item in new_allergies.split(",") if item.strip()])
            selected_profile.intolerances = json.dumps([item.strip() for item in new_intolerances.split(",") if item.strip()])
            selected_profile.disliked_ingredients = json.dumps([item.strip() for item in new_dislikes.split(",") if item.strip()])
            selected_profile.dietary_preferences = json.dumps([item.strip() for item in new_preferences.split(",") if item.strip()])
            selected_profile.medical_considerations = json.dumps([item.strip() for item in new_medical.split(",") if item.strip()])
            selected_profile.pregnancy_status = bool(pregnancy_value)
            selected_profile.pregnancy_trimester = pregnancy_trimester if pregnancy_value else None
            selected_profile.pre_pregnancy_weight_kg = float(pre_preg_weight) if pregnancy_value and pre_preg_weight is not None else None
            selected_profile.current_pregnancy_weight_kg = float(current_preg_weight) if pregnancy_value and current_preg_weight is not None else None
            selected_profile.breastfeeding_status = bool(breastfeeding_value)
            selected_profile.exclusive_breastfeeding = bool(exclusive)
            selected_profile.mixed_feeding = bool(mixed)
            selected_profile.breastfeeding_beyond_six_months = bool(beyond)
            selected_profile.usenote = new_notes
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

    st.subheader(f"Daily nutritional overview for {selected.name}")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Energy", f"{requirements['energy_kcal']} kcal")
    with col2:
        st.metric("Protein", f"{requirements['protein_g']} g")
    with col3:
        st.metric("Fiber", f"{requirements['fiber_g']} g")
    with col4:
        st.metric("Hydration", f"{requirements['hydration_liters']} L")

    st.caption(requirements["method"])
    st.caption(requirements["reference_source"])

    if requirements.get("notes"):
        st.markdown("### Guidance")
        for bullet in requirements["notes"]:
            st.write(f"- {bullet}")

    chart_data = pd.DataFrame(rows)
    if not chart_data.empty:
        chart_data = chart_data[chart_data["metric"].isin(["Energy Kcal", "Protein G", "Carbohydrates G", "Fiber G", "Iron Mg"])].copy()
        st.markdown("### Key nutrients")
        st.bar_chart(chart_data.set_index("metric")["value"])

    st.markdown("### Full requirement list")
    st.dataframe(pd.DataFrame(rows), use_container_width=True)

    if requirements.get("adjustments"):
        adjustments = requirements["adjustments"]
        st.markdown("### Context")
        st.write({
            "baseline activity factor": adjustments.get("baseline_activity_factor"),
            "exercise minutes": adjustments.get("exercise_minutes"),
            "exercise energy top-up": adjustments.get("exercise_top_up_kcal"),
            "pregnancy status": adjustments.get("pregnancy_status"),
            "breastfeeding status": adjustments.get("breastfeeding_status"),
        })


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
