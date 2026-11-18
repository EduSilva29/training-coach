import unittest
from datetime import date, timedelta

from coach.prompts import format_activities_for_prompt


class FormatActivitiesForPromptTests(unittest.TestCase):
    def test_summarizes_weekly_trends_and_limits_recent_details(self):
        today = date.today()
        current_week = today - timedelta(days=today.weekday())
        previous_week = current_week - timedelta(weeks=1)
        first_week = current_week - timedelta(weeks=4)

        activities = []
        for index in range(6):
            activities.append({
                "metadata": {
                    "activity_name": f"Run {index}",
                    "activity_type": "running",
                    "start_time": today.isoformat(),
                    "total_distance_km": index + 1,
                    "duration_seconds": 600,
                    "duration_formatted": "10:00",
                    "average_pace_min_km": "5:00",
                    "average_hr": 150,
                    "hr_zones": [{"zone": 4, "percentage": 10}],
                },
                "llm_summary": "Duplicated details that should not be sent",
            })

        activities.extend([
            {
                "metadata": {
                    "activity_name": "Bike",
                    "activity_type": "indoor_cycling",
                    "start_time": (previous_week + timedelta(days=1)).isoformat(),
                    "total_distance_km": 20,
                    "duration_seconds": 3600,
                    "duration_formatted": "1:00:00",
                    "speed_kmh": 20,
                },
            },
            {
                "metadata": {
                    "activity_name": "Outside history",
                    "activity_type": "running",
                    "start_time": (first_week - timedelta(days=1)).isoformat(),
                    "total_distance_km": 100,
                },
            },
        ])

        prompt_text = format_activities_for_prompt(activities)

        self.assertIn("Run 21.0 km/6 (longest 6.0 km; Z4-5 ~6 min)", prompt_text)
        self.assertIn("Bike 1 sessions/60 min", prompt_text)
        self.assertIn("current week to date", prompt_text)
        self.assertIn("Run 0.0 km/0 runs", prompt_text)
        self.assertIn("Run 4:", prompt_text)
        self.assertNotIn("Run 5:", prompt_text)
        self.assertNotIn("Outside history", prompt_text)
        self.assertNotIn("Duplicated details", prompt_text)

    def test_empty_activities_has_clear_message(self):
        self.assertEqual(
            format_activities_for_prompt([]),
            "No recent activities recorded in the database yet.",
        )


if __name__ == "__main__":
    unittest.main()
