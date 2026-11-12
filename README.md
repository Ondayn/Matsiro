# Matsiro

Matsiro is an offline-first family nutrition planning application built with Python, SQLite, SQLAlchemy, and Streamlit.

## Features

- A colorful family meal-planning workspace with an optional dark theme
- Saved daily meal plans with household member participation controls
- Per-ingredient randomization and lock controls, with allergy-aware alternatives
- Manage multiple household profiles with individual nutrition needs
- Member-specific insights, exercise logs, measurement history, and profile pictures
- Track measurements and activity history
- Store ingredients with preparation-state detail
- Generate nutrition estimates using household-specific rules
- Recommend family-friendly meals while respecting allergies and preferences
- Work entirely offline without internet-connected APIs

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Notes

- Data is stored in `family_nutrition.db` in the project root.
- The app includes sample seed data to help explore the interfaces.
- Nutrition calculations are heuristic, modular, and designed for local reference rather than medical diagnosis.
