import unittest
from datetime import date

from matsiro.database import SessionLocal, init_db
from matsiro.models import Household, Profile
from matsiro.nutrition_engine import calculate_daily_requirements


class MatsiroSmokeTests(unittest.TestCase):
    def setUp(self):
        init_db()
        self.session = SessionLocal()
        self.household = Household(name="Test Family")
        self.session.add(self.household)
        self.session.commit()
        self.session.refresh(self.household)

    def tearDown(self):
        self.session.close()

    def test_profile_and_requirements(self):
        profile = Profile(
            household_id=self.household.id,
            name="Test User",
            date_of_birth=date(1995, 1, 1),
            developmental_stage="adult",
            sex_reference="female",
            height_cm=165,
            weight_kg=60,
            activity_baseline="moderate",
            allergies="[]",
            intolerances="[]",
            disliked_ingredients="[]",
            dietary_preferences="[]",
            medical_considerations="[]",
            custom_diet="[]",
        )
        self.session.add(profile)
        self.session.commit()
        self.session.refresh(profile)

        requirements = calculate_daily_requirements(profile)
        self.assertIn("energy_kcal", requirements)
        self.assertGreater(requirements["energy_kcal"], 0)
        self.assertIn("method", requirements)

    def test_pregnancy_and_child_adjustments(self):
        pregnant = Profile(
            household_id=self.household.id,
            name="Pregnant User",
            date_of_birth=date(1990, 2, 1),
            developmental_stage="adult",
            sex_reference="female",
            height_cm=165,
            weight_kg=62,
            activity_baseline="light",
            pregnancy_status=True,
            pregnancy_trimester=3,
            current_pregnancy_weight_kg=68,
            allergies="[]",
            intolerances="[]",
            disliked_ingredients="[]",
            dietary_preferences="[]",
            medical_considerations="[]",
            custom_diet="[]",
        )
        self.session.add(pregnant)
        self.session.commit()
        self.session.refresh(pregnant)
        pregnancy_requirements = calculate_daily_requirements(pregnant)
        self.assertGreaterEqual(pregnancy_requirements["folate_ug"], 600)
        self.assertGreaterEqual(pregnancy_requirements["iron_mg"], 27)

        today = date.today()
        child = Profile(
            household_id=self.household.id,
            name="Child User",
            date_of_birth=date(today.year - 8, today.month, min(today.day, 28)),
            developmental_stage="child",
            sex_reference="female",
            height_cm=120,
            weight_kg=24,
            activity_baseline="moderate",
            allergies="[]",
            intolerances="[]",
            disliked_ingredients="[]",
            dietary_preferences="[]",
            medical_considerations="[]",
            custom_diet="[]",
        )
        self.session.add(child)
        self.session.commit()
        self.session.refresh(child)
        child_requirements = calculate_daily_requirements(child)
        self.assertGreater(child_requirements["energy_kcal"], 1200)


if __name__ == "__main__":
    unittest.main()
