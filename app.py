import json
from datetime import date, timedelta
from html import escape

import pandas as pd
import streamlit as st

from matsiro.database import SessionLocal, init_db
from matsiro.models import (
    ActivityRecord,
    Household,
    Ingredient,
    MealPlan,
    MealPlanItem,
    MeasurementRecord,
    Profile,
)
from matsiro.nutrition_engine import calculate_daily_requirements, list_requirement_rows
from matsiro.recommendation_engine import recommend_ingredient, recommend_meal
from matsiro.seed_data import ensure_seed_data


st.set_page_config(page_title="Matsiro", page_icon="🥗", layout="wide")

MEAL_SLOTS = [
    ("breakfast", "🌅", "Breakfast"),
    ("lunch", "☀️", "Lunch"),
    ("dinner", "🌙", "Dinner"),
    ("snacks", "🍊", "Snacks"),
]


def apply_theme():
    st.markdown(
        f"""
        <style>
        :root {{
          --matsiro-bg: var(--background-color, #f5f7f2);
          --matsiro-surface: var(--secondary-background-color, #ffffff);
          --matsiro-surface-alt: color-mix(in srgb, var(--primary-color, #176445) 9%, var(--matsiro-surface));
          --matsiro-text: var(--text-color, #193b2d);
          --matsiro-muted: color-mix(in srgb, var(--matsiro-text) 62%, var(--matsiro-bg));
          --matsiro-primary: var(--primary-color, #176445);
          --matsiro-accent: #e8794f;
          --matsiro-border: color-mix(in srgb, var(--matsiro-text) 13%, var(--matsiro-bg));
        }}
        .stApp {{
          background: var(--matsiro-bg);
          color: var(--matsiro-text);
        }}
        [data-testid="stAppViewContainer"] {{ color: var(--matsiro-text); }}
        [data-testid="stMainBlockContainer"] {{
          max-width: 1440px;
          padding-top: 2rem;
          padding-bottom: 4rem;
        }}
        [data-testid="stSidebar"] {{
          background: color-mix(in srgb, var(--matsiro-primary) 5%, var(--matsiro-bg));
          border-right: 1px solid var(--matsiro-border);
        }}
        [data-testid="stHeader"] {{ background: transparent; }}
        h1, h2, h3 {{
          color: var(--matsiro-text);
          font-family: "Trebuchet MS", "Segoe UI", sans-serif;
          font-weight: 750;
          letter-spacing: -.04em;
        }}
        h1 {{ font-size: clamp(2rem, 4vw, 3rem); line-height: 1.08; }}
        h2, h3 {{ letter-spacing: -.025em; }}
        p, label, [data-testid="stMarkdownContainer"] {{
          color: var(--matsiro-text);
          font-family: "Trebuchet MS", "Segoe UI", sans-serif;
        }}
        [data-testid="stCaptionContainer"], .stCaption {{ color: var(--matsiro-muted); }}
        [data-testid="stMetric"] {{
          background: var(--matsiro-surface);
          border-color: var(--matsiro-border);
          border-radius: 16px;
          padding: 1rem 1.1rem;
        }}
        [data-testid="stMetricLabel"] p {{
          color: var(--matsiro-muted);
          font-weight: 700;
        }}
        [data-testid="stVerticalBlockBorderWrapper"] {{
          background: var(--matsiro-surface);
          border-color: var(--matsiro-border);
          border-radius: 16px;
        }}
        .stButton > button, .stDownloadButton > button {{
          min-height: 2.6rem;
          border-radius: 10px;
          border: 1px solid var(--matsiro-border);
          color: var(--matsiro-text);
          font-weight: 700;
          transition: border-color .16s ease, box-shadow .16s ease, transform .16s ease;
        }}
        .stButton > button:hover, .stDownloadButton > button:hover {{
          border-color: var(--matsiro-primary);
          box-shadow: 0 5px 16px color-mix(in srgb, var(--matsiro-primary) 14%, transparent);
          transform: translateY(-1px);
        }}
        .stButton > button[kind="primary"] {{
          background: var(--matsiro-primary);
          border-color: var(--matsiro-primary);
          color: #ffffff;
          font-weight: 800;
        }}
        .stButton > button:focus-visible, .stDownloadButton > button:focus-visible {{
          outline: 3px solid color-mix(in srgb, var(--matsiro-primary) 50%, transparent);
          outline-offset: 2px;
        }}
        [data-testid="stTextInput"] input,
        [data-testid="stTextArea"] textarea,
        [data-testid="stNumberInput"] input,
        [data-testid="stDateInput"] input,
        [data-baseweb="select"] > div {{
          background: var(--matsiro-surface);
          color: var(--matsiro-text);
          border-color: var(--matsiro-border);
          border-radius: 10px;
        }}
        [data-testid="stTabs"] button[aria-selected="true"] {{
          color: var(--matsiro-primary);
          border-bottom-color: var(--matsiro-primary);
          font-weight: 800;
        }}
        [data-testid="stDataFrame"], [data-testid="stTable"] {{
          border: 1px solid var(--matsiro-border);
          border-radius: 12px;
          overflow: hidden;
        }}
        .member-avatar {{
          width: 72px; height: 72px; border-radius: 50%;
          display: flex; align-items: center; justify-content: center;
          margin: 0 auto 8px; font-size: 30px; font-weight: 800;
          color: #123626;
          background: color-mix(in srgb, var(--matsiro-primary) 16%, #ffffff);
          border: 2px solid color-mix(in srgb, var(--matsiro-primary) 22%, #ffffff);
        }}
        [data-testid="stCheckbox"] label,
        [data-testid="stRadio"] label {{
          color: var(--matsiro-text);
          font-weight: 700;
        }}
        [data-testid="stMarkdownContainer"] strong {{ color: var(--matsiro-text); }}
        .eyebrow {{
          display: inline-block;
          color: var(--matsiro-primary); font-size: .76rem;
          font-weight: 900; letter-spacing: .12em; text-transform: uppercase;
          padding: .38rem .8rem;
          margin-bottom: .4rem;
          border-radius: 999px 999px 999px 8px;
          background: var(--matsiro-surface-alt);
        }}
        .page-heading {{
          margin: 0 0 1.75rem;
          padding: 1.45rem 1.6rem 1.5rem;
          border: 1px solid var(--matsiro-border);
          border-left: 4px solid var(--matsiro-primary);
          border-radius: 16px;
          background: var(--matsiro-surface);
        }}
        .page-heading .eyebrow {{
          display: block;
          margin-bottom: .45rem;
          padding: 0;
          border-radius: 0;
          background: transparent;
          font-size: .72rem;
          letter-spacing: .11em;
        }}
        .page-heading h1 {{
          margin: 0;
          font-size: clamp(1.9rem, 3.5vw, 2.7rem);
        }}
        .page-heading p {{
          max-width: 64ch;
          margin: .55rem 0 0;
          color: var(--matsiro-muted);
          font-size: 1rem;
          line-height: 1.55;
        }}
        .brand-lockup {{
          display: flex;
          align-items: center;
          gap: .7rem;
          margin: .4rem 0 .25rem;
          color: var(--matsiro-text);
          font-size: 1.25rem;
          font-weight: 800;
          letter-spacing: -.03em;
        }}
        .brand-lockup .brand-icon {{
          display: grid;
          width: 2.35rem;
          height: 2.35rem;
          place-items: center;
          border-radius: 10px;
          background: var(--matsiro-primary);
          color: #fff;
          font-size: 1.25rem;
        }}
        @media (max-width: 640px) {{
          [data-testid="stMainBlockContainer"] {{
            padding: 1.25rem 1rem 3rem;
          }}
          .page-heading {{
            padding: 1.15rem 1.1rem;
            margin-bottom: 1.25rem;
          }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_page_header(eyebrow, title, description):
    st.markdown(
        f"""
        <header class="page-heading">
          <span class="eyebrow">{escape(eyebrow)}</span>
          <h1>{escape(title)}</h1>
          <p>{escape(description)}</p>
        </header>
        """,
        unsafe_allow_html=True,
    )


def parse_list_field(raw_value):
    if raw_value is None:
        return []
    if isinstance(raw_value, list):
        return raw_value
    value = str(raw_value).strip()
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


def _csv_list(raw_value):
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def _avatar(profile, width=72):
    if profile.avatar_data:
        st.image(profile.avatar_data, width=width)
    else:
        initial = escape((profile.name or "?")[:1].upper())
        st.markdown(f'<div class="member-avatar">{initial}</div>', unsafe_allow_html=True)


def _age_label(profile):
    if not profile.date_of_birth:
        return "Age not set"
    years = max(0, (date.today() - profile.date_of_birth).days / 365.25)
    return f"{years:.0f} years"


def _render_member_cards(profiles, state_key):
    if not profiles:
        return None
    valid_ids = {profile.id for profile in profiles}
    selected_id = st.session_state.get(state_key)
    if selected_id not in valid_ids:
        selected_id = profiles[0].id
        st.session_state[state_key] = selected_id

    st.markdown("#### Your household")
    columns = st.columns(min(len(profiles), 4))
    for index, profile in enumerate(profiles):
        with columns[index % len(columns)]:
            with st.container(border=True):
                is_selected = profile.id == selected_id
                _avatar(profile, width=88 if is_selected else 64)
                st.markdown(f"<center><strong>{escape(profile.name)}</strong></center>", unsafe_allow_html=True)
                if is_selected:
                    st.caption(f"{profile.developmental_stage or 'Member'} · {_age_label(profile)}")
                if st.button(
                    "Selected" if is_selected else "View member",
                    key=f"{state_key}_open_{profile.id}",
                    type="primary" if is_selected else "secondary",
                    use_container_width=True,
                ):
                    st.session_state[state_key] = profile.id
                    st.rerun()
    return next(profile for profile in profiles if profile.id == selected_id)


def _set_member_section(profile_id, section):
    st.session_state[f"member_section_{profile_id}"] = section


def _render_household_name(session):
    household = session.query(Household).first()
    if household is None:
        household = Household(name="Matsiro Family")
        session.add(household)
        session.commit()
        session.refresh(household)
    with st.expander("Household settings", expanded=False):
        name = st.text_input("Household name", value=household.name, key="household_name")
        if st.button("Save household name"):
            household.name = name.strip() or "Matsiro Family"
            session.commit()
            st.success("Household name saved.")


def _render_add_member(session, household_id):
    with st.expander("＋ Add a family member", expanded=False):
        name = st.text_input("Name", key="new_member_name")
        photo = st.file_uploader(
            "Profile picture (optional)",
            type=["jpg", "jpeg", "png"],
            key="new_member_photo",
        )
        columns = st.columns(2)
        with columns[0]:
            birth_date = st.date_input("Date of birth", value=date(2000, 1, 1), key="new_member_birth")
            stage = st.selectbox(
                "Life stage",
                ["baby", "child", "adolescent", "adult", "older adult"],
                key="new_member_stage",
            )
            height = st.number_input("Height (cm)", min_value=0.0, value=165.0, key="new_member_height")
        with columns[1]:
            sex = st.selectbox(
                "Nutrition reference",
                ["female", "male", "unspecified"],
                key="new_member_sex",
            )
            weight = st.number_input("Weight (kg)", min_value=0.0, value=60.0, key="new_member_weight")
            activity = st.selectbox(
                "Usual activity",
                ["sedentary", "light", "moderate", "active", "very_active"],
                index=2,
                key="new_member_activity",
            )
        pregnancy = st.checkbox(
            "Pregnancy-related profile",
            disabled=sex != "female",
            key="new_member_pregnancy",
        )
        trimester = pre_weight = current_weight = None
        breastfeeding = exclusive = mixed = beyond = False
        if pregnancy:
            trimester = st.selectbox("Trimester", [1, 2, 3], index=1, key="new_member_trimester")
            pre_weight = st.number_input("Pre-pregnancy weight (kg)", min_value=0.0, value=60.0)
            current_weight = st.number_input("Current pregnancy weight (kg)", min_value=0.0, value=62.0)
        breastfeeding = st.checkbox("Breastfeeding", key="new_member_breastfeeding")
        if breastfeeding:
            exclusive = st.checkbox("Exclusive breastfeeding", key="new_member_exclusive")
            mixed = st.checkbox("Mixed feeding", key="new_member_mixed")
            beyond = st.checkbox("Breastfeeding beyond 6 months", key="new_member_beyond")
        allergies = st.text_input("Allergies (comma separated)", key="new_member_allergies")
        intolerances = st.text_input("Intolerances (comma separated)", key="new_member_intolerances")
        if st.button("Add member", type="primary"):
            if not name.strip():
                st.error("Enter a name before adding a member.")
                return
            profile = Profile(
                household_id=household_id,
                name=name.strip(),
                date_of_birth=birth_date,
                developmental_stage=stage,
                sex_reference=sex,
                height_cm=height or None,
                weight_kg=weight or None,
                activity_baseline=activity,
                allergies=json.dumps(_csv_list(allergies)),
                intolerances=json.dumps(_csv_list(intolerances)),
                disliked_ingredients="[]",
                dietary_preferences="[]",
                medical_considerations="[]",
                custom_diet="[]",
                pregnancy_status=pregnancy,
                pregnancy_trimester=trimester if pregnancy else None,
                pre_pregnancy_weight_kg=pre_weight if pregnancy else None,
                current_pregnancy_weight_kg=current_weight if pregnancy else None,
                breastfeeding_status=breastfeeding,
                exclusive_breastfeeding=exclusive,
                mixed_feeding=mixed,
                breastfeeding_beyond_six_months=beyond,
                avatar_data=photo.getvalue() if photo else None,
            )
            session.add(profile)
            session.commit()
            st.session_state["household_member_id"] = profile.id
            st.success(f"Added {profile.name}.")
            st.rerun()


def _render_member_profile(profile):
    st.markdown("### Profile details")
    _avatar(profile, width=96)
    st.caption("Upload a photo to personalize this member's tab.")
    photo = st.file_uploader(
        "Change profile picture",
        type=["jpg", "jpeg", "png"],
        key=f"member_photo_{profile.id}",
    )
    remove_photo = st.checkbox("Remove profile picture", key=f"remove_photo_{profile.id}")

    columns = st.columns(2)
    with columns[0]:
        name = st.text_input("Name", value=profile.name, key=f"profile_name_{profile.id}")
        birth_date = st.date_input(
            "Date of birth",
            value=profile.date_of_birth or date(2000, 1, 1),
            key=f"profile_birth_{profile.id}",
        )
        stage_options = ["baby", "child", "adolescent", "adult", "older adult"]
        stage_value = profile.developmental_stage if profile.developmental_stage in stage_options else "adult"
        stage = st.selectbox(
            "Life stage",
            stage_options,
            index=stage_options.index(stage_value),
            key=f"profile_stage_{profile.id}",
        )
    with columns[1]:
        sex_options = ["female", "male", "unspecified"]
        sex_value = profile.sex_reference if profile.sex_reference in sex_options else "unspecified"
        sex = st.selectbox(
            "Nutrition reference",
            sex_options,
            index=sex_options.index(sex_value),
            key=f"profile_sex_{profile.id}",
        )
        height = st.number_input(
            "Height (cm)",
            min_value=0.0,
            value=float(profile.height_cm or 165),
            key=f"profile_height_{profile.id}",
        )
        weight = st.number_input(
            "Weight (kg)",
            min_value=0.0,
            value=float(profile.weight_kg or 60),
            key=f"profile_weight_{profile.id}",
        )
        activity_options = ["sedentary", "light", "moderate", "active", "very_active"]
        activity_value = profile.activity_baseline if profile.activity_baseline in activity_options else "moderate"
        activity = st.selectbox(
            "Usual activity",
            activity_options,
            index=activity_options.index(activity_value),
            key=f"profile_activity_{profile.id}",
        )
    sports = st.text_input(
        "Sports and activities",
        value=", ".join(parse_list_field(profile.sport_preferences)),
        key=f"profile_sports_{profile.id}",
    )
    notes = st.text_area("Notes", value=profile.usenote or "", key=f"profile_notes_{profile.id}")
    if st.button("Save profile", type="primary", key=f"save_profile_{profile.id}"):
        profile.name = name.strip() or profile.name
        profile.date_of_birth = birth_date
        profile.developmental_stage = stage
        profile.sex_reference = sex
        profile.height_cm = height or None
        profile.weight_kg = weight or None
        profile.activity_baseline = activity
        profile.sport_preferences = json.dumps(_csv_list(sports))
        profile.usenote = notes
        if photo:
            profile.avatar_data = photo.getvalue()
        elif remove_photo:
            profile.avatar_data = None
        session.commit()
        st.success("Profile saved.")
        st.rerun()


def _render_member_food_needs(session, profile):
    st.markdown("### Food needs and preferences")
    pregnancy = st.checkbox(
        "Pregnancy-related profile",
        value=bool(profile.pregnancy_status),
        disabled=profile.sex_reference != "female",
        key=f"pregnancy_{profile.id}",
    )
    trimester = profile.pregnancy_trimester or 2
    pre_weight = float(profile.pre_pregnancy_weight_kg or profile.weight_kg or 60)
    current_weight = float(profile.current_pregnancy_weight_kg or profile.weight_kg or 62)
    if pregnancy:
        trimester = st.selectbox(
            "Trimester",
            [1, 2, 3],
            index=max(0, min(2, trimester - 1)),
            key=f"trimester_{profile.id}",
        )
        pre_weight = st.number_input(
            "Pre-pregnancy weight (kg)",
            min_value=0.0,
            value=pre_weight,
            key=f"pre_weight_{profile.id}",
        )
        current_weight = st.number_input(
            "Current pregnancy weight (kg)",
            min_value=0.0,
            value=current_weight,
            key=f"current_weight_{profile.id}",
        )
    breastfeeding = st.checkbox(
        "Breastfeeding",
        value=bool(profile.breastfeeding_status),
        key=f"breastfeeding_{profile.id}",
    )
    exclusive = mixed = beyond = False
    if breastfeeding:
        exclusive = st.checkbox(
            "Exclusive breastfeeding",
            value=bool(profile.exclusive_breastfeeding),
            key=f"exclusive_{profile.id}",
        )
        mixed = st.checkbox(
            "Mixed feeding",
            value=bool(profile.mixed_feeding),
            key=f"mixed_{profile.id}",
        )
        beyond = st.checkbox(
            "Breastfeeding beyond 6 months",
            value=bool(profile.breastfeeding_beyond_six_months),
            key=f"beyond_{profile.id}",
        )

    allergies = st.text_input(
        "Allergies",
        value=", ".join(parse_list_field(profile.allergies)),
        key=f"allergies_{profile.id}",
    )
    intolerances = st.text_input(
        "Intolerances",
        value=", ".join(parse_list_field(profile.intolerances)),
        key=f"intolerances_{profile.id}",
    )
    dislikes = st.text_input(
        "Disliked ingredients",
        value=", ".join(parse_list_field(profile.disliked_ingredients)),
        key=f"dislikes_{profile.id}",
    )
    preferences = st.text_input(
        "Dietary preferences",
        value=", ".join(parse_list_field(profile.dietary_preferences)),
        key=f"preferences_{profile.id}",
    )
    medical = st.text_input(
        "Medical or nutrition considerations",
        value=", ".join(parse_list_field(profile.medical_considerations)),
        key=f"medical_{profile.id}",
    )
    if st.button("Save food needs", type="primary", key=f"save_food_needs_{profile.id}"):
        profile.pregnancy_status = bool(pregnancy)
        profile.pregnancy_trimester = trimester if pregnancy else None
        profile.pre_pregnancy_weight_kg = pre_weight if pregnancy else None
        profile.current_pregnancy_weight_kg = current_weight if pregnancy else None
        profile.breastfeeding_status = bool(breastfeeding)
        profile.exclusive_breastfeeding = bool(exclusive)
        profile.mixed_feeding = bool(mixed)
        profile.breastfeeding_beyond_six_months = bool(beyond)
        profile.allergies = json.dumps(_csv_list(allergies))
        profile.intolerances = json.dumps(_csv_list(intolerances))
        profile.disliked_ingredients = json.dumps(_csv_list(dislikes))
        profile.dietary_preferences = json.dumps(_csv_list(preferences))
        profile.medical_considerations = json.dumps(_csv_list(medical))
        session.commit()
        st.success("Food needs saved.")
        st.rerun()


def _render_measurements(session, profile):
    with st.form(f"measurement_form_{profile.id}"):
        measurement_date = st.date_input("Measurement date", value=date.today())
        height = st.number_input(
            "Height (cm)",
            min_value=0.0,
            value=float(profile.height_cm or 165),
        )
        weight = st.number_input(
            "Weight (kg)",
            min_value=0.0,
            value=float(profile.weight_kg or 60),
        )
        notes = st.text_input("Notes")
        submitted = st.form_submit_button("Add measurement", type="primary")
    if submitted:
        session.add(
            MeasurementRecord(
                profile_id=profile.id,
                date=measurement_date,
                height_cm=height or None,
                weight_kg=weight or None,
                notes=notes,
            )
        )
        session.commit()
        st.success("Measurement added.")
        st.rerun()

    history = (
        session.query(MeasurementRecord)
        .filter(MeasurementRecord.profile_id == profile.id)
        .order_by(MeasurementRecord.date.desc())
        .all()
    )
    if history:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Date": item.date.isoformat(),
                        "Height (cm)": item.height_cm,
                        "Weight (kg)": item.weight_kg,
                        "Notes": item.notes,
                    }
                    for item in history
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No measurements yet. Add one above to start a history.")


def _render_exercise(session, profile):
    with st.form(f"activity_form_{profile.id}"):
        activity_date = st.date_input("Activity date", value=date.today())
        sport = st.selectbox(
            "Activity",
            ["Walking", "Running", "Swimming", "Cycling", "Dancing", "Football", "Basketball", "Strength training", "Other"],
        )
        duration = st.number_input("Duration (minutes)", min_value=0, value=30, step=5)
        intensity = st.selectbox("Intensity", ["low", "moderate", "high", "vigorous"], index=1)
        notes = st.text_input("Notes")
        submitted = st.form_submit_button("Log activity", type="primary")
    if submitted:
        session.add(
            ActivityRecord(
                profile_id=profile.id,
                date=activity_date,
                sport_type=sport,
                duration_minutes=float(duration),
                intensity=intensity,
                notes=notes,
            )
        )
        session.commit()
        st.success("Activity logged.")
        st.rerun()

    records = (
        session.query(ActivityRecord)
        .filter(ActivityRecord.profile_id == profile.id)
        .order_by(ActivityRecord.date.desc())
        .all()
    )
    if records:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Date": item.date.isoformat(),
                        "Activity": item.sport_type,
                        "Minutes": item.duration_minutes,
                        "Intensity": item.intensity,
                        "Notes": item.notes,
                    }
                    for item in records
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No activities logged yet.")


def render_household_page(session, profiles):
    _render_page_header(
        "Your family",
        "Household",
        "Keep family profiles, food needs, and activity details together.",
    )
    _render_household_name(session)

    household = session.query(Household).first()
    _render_add_member(session, household.id)
    profiles = session.query(Profile).order_by(Profile.id).all()
    if not profiles:
        st.info("Add your first member to personalize meals and nutrition insights.")
        return

    profile = _render_member_cards(profiles, "household_member_id")
    with st.container(border=True):
        avatar_col, summary_col = st.columns([1, 4])
        with avatar_col:
            _avatar(profile, width=112)
        with summary_col:
            st.markdown(f"### {profile.name}")
            st.caption(
                f"{profile.sex_reference or 'Unspecified'} nutrition reference · "
                f"{profile.developmental_stage or 'Member'} · {_age_label(profile)}"
            )
            metrics = st.columns(3)
            metrics[0].metric("Height", f"{profile.height_cm or '—'} cm")
            metrics[1].metric("Weight", f"{profile.weight_kg or '—'} kg")
            metrics[2].metric(
                "Activity",
                (profile.activity_baseline or "moderate").replace("_", " ").title(),
            )
            allergies = parse_list_field(profile.allergies)
            intolerances = parse_list_field(profile.intolerances)
            preferences = parse_list_field(profile.dietary_preferences)
            st.write(
                f"**Food needs:** {', '.join(allergies + intolerances) or 'None saved'}"
            )
            if preferences:
                st.write(f"**Preferences:** {', '.join(preferences)}")
            if profile.pregnancy_status or profile.breastfeeding_status:
                st.info("Pregnancy or lactation adjustments are enabled.")

    section_key = f"member_section_{profile.id}"
    if section_key not in st.session_state:
        st.session_state[section_key] = "Overview"
    st.markdown("### Member workspace")
    section = st.radio(
        "Member workspace",
        ["Overview", "Insights", "Exercise", "Measurements", "Food needs", "Profile"],
        horizontal=True,
        label_visibility="collapsed",
        key=section_key,
    )
    edit_col, needs_col = st.columns([1, 1])
    with edit_col:
        st.button(
            "Edit profile",
            key=f"edit_profile_link_{profile.id}",
            on_click=_set_member_section,
            args=(profile.id, "Profile"),
        )
    with needs_col:
        st.button(
            "Edit food needs",
            key=f"edit_needs_link_{profile.id}",
            on_click=_set_member_section,
            args=(profile.id, "Food needs"),
        )

    if section == "Overview":
        if profile.usenote:
            st.write(profile.usenote)
        else:
            st.caption("Use Edit profile to add notes and update member details.")
    elif section == "Insights":
        activities = (
            session.query(ActivityRecord)
            .filter(ActivityRecord.profile_id == profile.id)
            .all()
        )
        requirements = calculate_daily_requirements(profile, activities)
        columns = st.columns(4)
        columns[0].metric("Energy estimate", f"{requirements['energy_kcal']} kcal")
        columns[1].metric("Protein", f"{requirements['protein_g']} g")
        columns[2].metric("Fiber", f"{requirements['fiber_g']} g")
        columns[3].metric("Hydration", f"{requirements['hydration_liters']} L")
        st.caption(requirements["uncertainty"])
        st.caption(requirements["method"])
        if requirements["notes"]:
            for note in requirements["notes"]:
                st.write(f"• {note}")
        with st.expander("All estimated daily values"):
            st.dataframe(
                pd.DataFrame(list_requirement_rows(profile, activities)),
                use_container_width=True,
                hide_index=True,
            )
    elif section == "Exercise":
        st.subheader("Exercise and activity")
        _render_exercise(session, profile)
    elif section == "Measurements":
        st.subheader("Measurements")
        _render_measurements(session, profile)
    elif section == "Food needs":
        _render_member_food_needs(session, profile)
    elif section == "Profile":
        _render_member_profile(profile)


def _meal_state_key(plan_date, meal_type):
    return f"meal_draft_{plan_date.isoformat()}_{meal_type}"


def _load_meal_draft(session, plan_date, meal_type):
    plan = (
        session.query(MealPlan)
        .filter(MealPlan.date == plan_date, MealPlan.meal_type == meal_type)
        .order_by(MealPlan.id.desc())
        .first()
    )
    if plan is None:
        return []
    try:
        details = json.loads(plan.notes or "{}")
    except (TypeError, json.JSONDecodeError):
        details = {}
    items = details.get("items")
    if isinstance(items, list):
        return items
    rows = (
        session.query(MealPlanItem)
        .filter(MealPlanItem.meal_plan_id == plan.id)
        .all()
    )
    return [
        {
            "category": "ingredient",
            "name": item.ingredient_name,
            "preparation": "",
            "category_label": "Ingredient",
            "locked": False,
        }
        for item in rows
    ]


def _previous_meal_ingredients(session, plan_date, exclude_type):
    plans = (
        session.query(MealPlan)
        .filter(MealPlan.date == plan_date, MealPlan.meal_type != exclude_type)
        .all()
    )
    plan_ids = [plan.id for plan in plans]
    if not plan_ids:
        return []
    return [
        item.ingredient_name
        for item in session.query(MealPlanItem)
        .filter(MealPlanItem.meal_plan_id.in_(plan_ids))
        .all()
    ]


def _new_meal(profile, participants, ingredients, previous):
    recommendation = recommend_meal(
        profile=profile,
        ingredients=ingredients,
        previous_meals=previous,
        household_profiles=participants,
    )
    return [
        {
            **item,
            "locked": False,
        }
        for item in recommendation["items"]
    ]


def _randomize_one(profile, participants, ingredients, previous, items, index):
    current = items[index]
    other_names = {
        item["name"]
        for offset, item in enumerate(items)
        if offset != index
    }
    replacement = recommend_ingredient(
        profile=profile,
        ingredients=ingredients,
        category=current["category"],
        previous_meals=previous,
        household_profiles=participants,
        exclude_names=other_names | {current["name"]},
    )
    if replacement is None:
        return False
    replacement["locked"] = current.get("locked", False)
    items[index] = replacement
    return True


def _save_meal(session, profile, participants, plan_date, meal_type, items):
    plan = (
        session.query(MealPlan)
        .filter(MealPlan.date == plan_date, MealPlan.meal_type == meal_type)
        .order_by(MealPlan.id.desc())
        .first()
    )
    if plan is None:
        plan = MealPlan(
            profile_id=profile.id,
            date=plan_date,
            meal_type=meal_type,
        )
        session.add(plan)
        session.flush()
    plan.profile_id = profile.id
    plan.title = " + ".join(item["name"] for item in items[:3])
    plan.notes = json.dumps(
        {
            "participants": [member.id for member in participants],
            "items": items,
        }
    )
    session.query(MealPlanItem).filter(
        MealPlanItem.meal_plan_id == plan.id
    ).delete(synchronize_session=False)
    session.add_all(
        [
            MealPlanItem(
                meal_plan_id=plan.id,
                ingredient_name=item["name"],
                quantity_g=0,
            )
            for item in items
        ]
    )
    session.commit()


def _render_meal_slot(session, profile, participants, ingredients, plan_date, meal_type, icon, label):
    key = _meal_state_key(plan_date, meal_type)
    if key not in st.session_state:
        st.session_state[key] = _load_meal_draft(session, plan_date, meal_type)
    items = st.session_state[key]
    previous = _previous_meal_ingredients(session, plan_date, meal_type)

    with st.container(border=True):
        heading, generate = st.columns([4, 1])
        with heading:
            st.subheader(f"{icon}  {label}")
        with generate:
            if st.button(
                "Build meal" if not items else "Randomize unlocked",
                key=f"build_{key}",
                type="primary" if not items else "secondary",
                disabled=not ingredients or (bool(items) and not any(not item.get("locked") for item in items)),
                use_container_width=True,
            ):
                if not items:
                    items = _new_meal(profile, participants, ingredients, previous)
                    if not items:
                        st.warning("No safe suggestions yet. Add more ingredients or review household food needs.")
                    st.session_state[key] = items
                else:
                    updated = False
                    for index, item in enumerate(list(items)):
                        if not item.get("locked"):
                            updated = _randomize_one(
                                profile, participants, ingredients, previous, items, index
                            ) or updated
                    st.session_state[key] = items
                    if not updated:
                        st.info("No alternative ingredients are available for this meal.")
                st.rerun()

        if not items:
            st.caption("Build a meal to get household-aware ingredient suggestions.")
            return

        st.caption(
            "Lock rows to preserve them during a meal randomize. The ↻ beside any row "
            "replaces only that ingredient, even when it is locked."
        )
        for index, item in enumerate(items):
            name_col, lock_col, reroll_col = st.columns([7, 1, 1])
            with name_col:
                st.markdown(
                    f"**{item['name']}**  ·  {item.get('preparation', 'as preferred')}  "
                    f"<span style='color:var(--matsiro-muted)'>{item.get('category_label', item.get('category', ''))}</span>",
                    unsafe_allow_html=True,
                )
            with lock_col:
                lock_label = "🔒" if item.get("locked") else "🔓"
                if st.button(
                    lock_label,
                    key=f"lock_{key}_{index}",
                    help="Keep this ingredient during whole-meal randomization.",
                    use_container_width=True,
                ):
                    item["locked"] = not item.get("locked", False)
                    st.session_state[key] = items
                    st.rerun()
            with reroll_col:
                if st.button(
                    "↻",
                    key=f"reroll_{key}_{index}",
                    help="Randomize this ingredient only. Other ingredients stay unchanged.",
                    use_container_width=True,
                ):
                    if _randomize_one(profile, participants, ingredients, previous, items, index):
                        st.session_state[key] = items
                        st.rerun()
                    else:
                        st.warning("No safe alternative is available for this ingredient.")

        unused = [item.common_name for item in ingredients if item.common_name not in {row["name"] for row in items}]
        with st.expander("＋ Add an ingredient manually"):
            if unused:
                selected_ingredient = st.selectbox(
                    "Ingredient",
                    unused,
                    key=f"add_ingredient_select_{key}",
                )
                if st.button("Add ingredient", key=f"add_ingredient_{key}"):
                    ingredient = next(item for item in ingredients if item.common_name == selected_ingredient)
                    items.append(
                        {
                            "category": ingredient.food_category,
                            "name": ingredient.common_name,
                            "preparation": ingredient.preparation_state,
                            "category_label": ingredient.food_category,
                            "locked": False,
                        }
                    )
                    st.session_state[key] = items
                    st.rerun()
            else:
                st.caption("All available ingredients are already included.")

        if st.button("Save meal to plan", type="primary", key=f"save_meal_{key}"):
            _save_meal(session, profile, participants, plan_date, meal_type, items)
            st.success(f"{label} saved to the plan.")
            st.rerun()


def render_plan_page(session, profiles):
    _render_page_header(
        "Make family meals easier",
        "Meal planner",
        "Choose a day and who is eating, then build meals around the household's needs.",
    )
    if not profiles:
        st.info("Add a household member first, then come back to build a meal plan.")
        return

    if "plan_date_widget" not in st.session_state:
        st.session_state["plan_date_widget"] = date.today()
    selected_day = st.session_state["plan_date_widget"]
    monday = selected_day - timedelta(days=selected_day.weekday())
    week_cols = st.columns(7)
    for offset, column in enumerate(week_cols):
        day = monday + timedelta(days=offset)
        with column:
            if st.button(
                f"{day.strftime('%a')}  {day.day}",
                key=f"plan_day_{day.isoformat()}",
                type="primary" if day == selected_day else "secondary",
                use_container_width=True,
            ):
                st.session_state["plan_date_widget"] = day
                st.rerun()

    date_col, summary_col = st.columns([1, 3])
    with date_col:
        selected_day = st.date_input("Planning date", key="plan_date_widget")
    with summary_col:
        st.markdown(f"### {selected_day.strftime('%A, %B %d')}")
        st.caption("Select who is eating. Suggestions will honor the selected members' restrictions.")

    member_col, meal_col = st.columns([1.05, 2.95])
    participants = []
    with member_col:
        st.markdown("### Who's eating?")
        st.caption("Choose members to apply their food needs.")
        for profile in profiles:
            with st.container(border=True):
                avatar_col, name_col, check_col = st.columns([1, 2.3, 0.8])
                with avatar_col:
                    _avatar(profile, width=44)
                with name_col:
                    st.markdown(f"**{profile.name}**")
                    restrictions = parse_list_field(profile.allergies) + parse_list_field(profile.intolerances)
                    st.caption(", ".join(restrictions) if restrictions else "No restrictions")
                with check_col:
                    key = f"plan_member_{profile.id}"
                    if key not in st.session_state:
                        st.session_state[key] = True
                    included = st.checkbox(
                        "Included",
                        key=key,
                        label_visibility="collapsed",
                    )
                if included:
                    participants.append(profile)

    with meal_col:
        st.markdown("### Plan meals")
        if not participants:
            st.warning("Choose at least one member to get safe, relevant meal suggestions.")
            return

        ingredients = session.query(Ingredient).order_by(Ingredient.common_name).all()
        if not ingredients:
            st.info("Add ingredients in Food library before generating meal suggestions.")
            return

        primary = participants[0]
        for row in range(2):
            meal_cols = st.columns(2)
            for column, slot in zip(meal_cols, MEAL_SLOTS[row * 2 : row * 2 + 2]):
                meal_type, icon, label = slot
                with column:
                    _render_meal_slot(
                        session,
                        primary,
                        participants,
                        ingredients,
                        selected_day,
                        meal_type,
                        icon,
                        label,
                    )


def render_food_library(session):
    _render_page_header(
        "Your local food catalog",
        "Food library",
        "Manage the ingredients used to create safe, flexible meal suggestions.",
    )
    search = st.text_input("Search ingredients", placeholder="Search by name or category")
    with st.expander("＋ Add an ingredient", expanded=False):
        name = st.text_input("Ingredient name", key="ingredient_name")
        columns = st.columns(2)
        with columns[0]:
            category = st.selectbox(
                "Category",
                ["staple grain", "legume", "protein", "vegetable", "fruit", "root", "dairy", "other"],
                key="ingredient_category",
            )
            preparation = st.selectbox(
                "Typical preparation",
                ["raw", "boiled", "roasted", "dried", "steamed", "grilled"],
                key="ingredient_preparation",
            )
            energy = st.number_input("Energy (kcal / 100 g)", min_value=0.0, key="ingredient_energy")
        with columns[1]:
            alternatives = st.text_input("Alternative names (comma separated)", key="ingredient_alternatives")
            protein = st.number_input("Protein (g / 100 g)", min_value=0.0, key="ingredient_protein")
            fiber = st.number_input("Fiber (g / 100 g)", min_value=0.0, key="ingredient_fiber")
        if st.button("Save ingredient", type="primary"):
            if not name.strip():
                st.error("Enter an ingredient name.")
            else:
                session.add(
                    Ingredient(
                        common_name=name.strip(),
                        alternative_names=json.dumps(_csv_list(alternatives)),
                        english_name=name.strip(),
                        food_category=category,
                        preparation_state=preparation,
                        energy_kcal_per_100g=energy,
                        protein_g_per_100g=protein,
                        fiber_g_per_100g=fiber,
                    )
                )
                session.commit()
                st.success(f"Added {name.strip()}.")
                st.rerun()

    query = session.query(Ingredient).order_by(Ingredient.common_name)
    if search.strip():
        query = query.filter(Ingredient.common_name.ilike(f"%{search.strip()}%"))
    ingredients = query.all()
    if ingredients:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Ingredient": item.common_name,
                        "Category": item.food_category,
                        "Preparation": item.preparation_state,
                        "Energy / 100 g": item.energy_kcal_per_100g,
                        "Protein / 100 g": item.protein_g_per_100g,
                    }
                    for item in ingredients
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No ingredients match that search.")


def render_insights_page(session, profiles):
    _render_page_header(
        "Nutrition and activity",
        "Insights",
        "Review estimated nutrition targets and the activity your household has logged.",
    )
    if not profiles:
        st.info("Add a household member to see personalized insights.")
        return
    profile = _render_member_cards(profiles, "insights_member_id")
    activities = (
        session.query(ActivityRecord)
        .filter(ActivityRecord.profile_id == profile.id)
        .all()
    )
    requirements = calculate_daily_requirements(profile, activities)
    columns = st.columns(4)
    columns[0].metric("Energy estimate", f"{requirements['energy_kcal']} kcal")
    columns[1].metric("Protein", f"{requirements['protein_g']} g")
    columns[2].metric("Fiber", f"{requirements['fiber_g']} g")
    columns[3].metric("Hydration", f"{requirements['hydration_liters']} L")
    st.info(
        "These are estimated daily nutrition targets based on the member's profile. "
        "They are not intake or progress measurements—the app does not yet record "
        "food actually eaten."
    )

    details_col, activity_col = st.columns(2)
    with details_col:
        st.subheader("Estimated daily targets")
        st.caption("Use these as general planning references, not medical prescriptions.")
        rows = list_requirement_rows(profile, activities)
        targets = pd.DataFrame(
            [
                {
                    "Nutrient": row["metric"],
                    "Estimated target": f"{row['value']} {row['unit']}",
                }
                for row in rows
            ]
        )
        st.dataframe(targets, use_container_width=True, hide_index=True)
        with st.expander("View all values and assumptions"):
            st.write(requirements["method"])
            st.write(requirements["reference_source"])
            for note in requirements["notes"]:
                st.write(f"• {note}")
    with activity_col:
        st.subheader("Exercise logged this week")
        week_start = date.today() - timedelta(days=6)
        week_records = [
            record
            for record in activities
            if week_start <= record.date <= date.today()
        ]
        totals_by_day = {week_start + timedelta(days=offset): 0.0 for offset in range(7)}
        for record in week_records:
            totals_by_day[record.date] += record.duration_minutes
        activity_chart = pd.DataFrame(
            [
                {"Day": day.strftime("%a"), "Minutes": minutes}
                for day, minutes in totals_by_day.items()
            ]
        )
        st.bar_chart(activity_chart.set_index("Day")["Minutes"])
        st.caption("Minutes come from activity logs; blank days mean no activity was recorded.")
        recent = (
            session.query(ActivityRecord)
            .filter(ActivityRecord.profile_id == profile.id)
            .order_by(ActivityRecord.date.desc())
            .limit(8)
            .all()
        )
        if recent:
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "Date": record.date.isoformat(),
                            "Activity": record.sport_type,
                            "Minutes": record.duration_minutes,
                            "Intensity": record.intensity,
                        }
                        for record in recent
                    ]
                ),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("Log exercise from this member's Exercise workspace.")


def main():
    init_db()
    apply_theme()
    session = SessionLocal()
    try:
        ensure_seed_data(session)
        household = session.query(Household).first()
        profiles = session.query(Profile).order_by(Profile.id).all()

        with st.sidebar:
            st.markdown(
                '<div class="brand-lockup"><span class="brand-icon">🥗</span><span>Matsiro</span></div>',
                unsafe_allow_html=True,
            )
            st.caption("Family food, made simpler")
            st.markdown("**Workspace**")
            page = st.radio(
                "Navigate",
                ["Plan", "Household", "Food library", "Insights"],
                label_visibility="collapsed",
                key="navigation",
            )
            st.divider()
            st.caption("Private by design")
            st.caption("Household data stays on this device.")

        if page == "Plan":
            render_plan_page(session, profiles)
        elif page == "Household":
            render_household_page(session, profiles)
        elif page == "Food library":
            render_food_library(session)
        else:
            render_insights_page(session, profiles)
    finally:
        session.close()


if __name__ == "__main__":
    main()
