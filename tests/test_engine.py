import os
import unittest
from types import SimpleNamespace
from unittest.mock import call, patch

from coach import engine


class AskCoachTests(unittest.TestCase):
    def setUp(self):
        self.patches = [
            patch.dict(
                os.environ,
                {"GEMINI_API_KEY": "test-key", "GEMINI_MODEL": "primary-model"},
            ),
            patch.object(engine, "get_athlete_profile", return_value={}),
            patch.object(engine, "get_recent_recovery_history", return_value=[]),
            patch.object(engine, "get_recent_activities", return_value=[]),
            patch.object(engine, "get_chat_history", return_value=[
                {"role": "assistant", "content": "Previous reply"}
            ]),
            patch.object(engine, "build_coach_system_instruction", return_value="system"),
            patch.object(engine, "run_scribe_extraction"),
            patch.object(engine.threading, "Thread"),
            patch("google.genai.Client"),
        ]
        self.mocks = [patcher.start() for patcher in self.patches]
        self.addCleanup(self._stop_patches)

        self.get_chat_history = self.mocks[4]
        self.client = self.mocks[-1].return_value

    def _stop_patches(self):
        for patcher in reversed(self.patches):
            patcher.stop()

    def test_busy_models_are_retried_and_do_not_persist_user_message(self):
        self.client.models.generate_content.side_effect = [
            RuntimeError("503 unavailable"),
            RuntimeError("503 unavailable"),
            RuntimeError("503 unavailable"),
            RuntimeError("503 unavailable"),
            RuntimeError("503 unavailable"),
            RuntimeError("503 unavailable"),
        ]

        with patch("builtins.print"), patch.object(engine.time, "sleep") as sleep, patch.object(
            engine, "save_message"
        ) as save_message:
            result, model = engine.ask_coach("What should I run today?")

        save_message.assert_not_called()
        self.assertIsNone(model)
        self.assertEqual(
            [call.kwargs["model"] for call in self.client.models.generate_content.call_args_list],
            ["primary-model"] * 3 + ["gemini-3.6-flash"] * 3,
        )
        self.assertEqual(
            [call.args[0] for call in sleep.call_args_list[-4:]],
            [1, 2, 1, 2],
        )
        self.get_chat_history.assert_called_once_with(limit=49)
        contents = self.client.models.generate_content.call_args_list[0].kwargs["contents"]
        self.assertEqual(contents[-1], {
            "role": "user",
            "parts": [{"text": "What should I run today?"}],
        })
        self.assertIn("Temporary Google Server Congestion", result)

    def test_success_persists_user_and_assistant_messages(self):
        self.client.models.generate_content.return_value = SimpleNamespace(text="Coach reply")

        with patch.object(engine, "save_message") as save_message:
            result, model = engine.ask_coach("What should I run today?")

        self.assertEqual((result, model), ("Coach reply", "primary-model"))
        self.client.models.generate_content.assert_called_once()
        engine.get_recent_activities.assert_called_once_with(limit=100)
        self.assertEqual(save_message.call_args_list, [
            call(role="user", content="What should I run today?"),
            call(role="assistant", content="Coach reply", model="primary-model"),
        ])

    def test_congested_primary_retries_then_uses_backup(self):
        self.client.models.generate_content.side_effect = [
            RuntimeError("503 unavailable"),
            RuntimeError("503 unavailable"),
            RuntimeError("503 unavailable"),
            SimpleNamespace(text="Backup reply"),
        ]

        with patch("builtins.print"), patch.object(engine.time, "sleep"), patch.object(
            engine, "save_message"
        ) as save_message:
            result = engine.ask_coach("What should I run today?")

        self.assertEqual(result, ("Backup reply", "gemini-3.6-flash"))
        self.assertEqual(
            [call.kwargs["model"] for call in self.client.models.generate_content.call_args_list],
            ["primary-model"] * 3 + ["gemini-3.6-flash"],
        )
        self.assertEqual(
            save_message.call_args_list[-1],
            call(role="assistant", content="Backup reply", model="gemini-3.6-flash"),
        )

    def test_congested_primary_can_succeed_on_retry(self):
        self.client.models.generate_content.side_effect = [
            RuntimeError("503 unavailable"),
            SimpleNamespace(text="Recovered reply"),
        ]

        with patch("builtins.print"), patch.object(engine.time, "sleep") as sleep, patch.object(
            engine, "save_message"
        ):
            result = engine.ask_coach("What should I run today?")

        self.assertEqual(result, ("Recovered reply", "primary-model"))
        self.assertEqual(
            [call.kwargs["model"] for call in self.client.models.generate_content.call_args_list],
            ["primary-model", "primary-model"],
        )
        sleep.assert_called_once_with(1)

    def test_fallback_models_are_tried_in_configured_order(self):
        self.client.models.generate_content.side_effect = [
            RuntimeError("503 unavailable"),
            RuntimeError("503 unavailable"),
            RuntimeError("503 unavailable"),
            RuntimeError("503 unavailable"),
            RuntimeError("503 unavailable"),
            RuntimeError("503 unavailable"),
            SimpleNamespace(text="Third model reply"),
        ]

        with patch.dict(
            os.environ,
            {
                "GEMINI_FALLBACK_MODELS": (
                    "primary-model, backup-one, backup-two, backup-one"
                )
            },
        ), patch("builtins.print"), patch.object(engine.time, "sleep"), patch.object(
            engine, "save_message"
        ):
            result = engine.ask_coach("What should I run today?")

        self.assertEqual(result, ("Third model reply", "backup-two"))
        self.assertEqual(
            [call.kwargs["model"] for call in self.client.models.generate_content.call_args_list],
            ["primary-model"] * 3 + ["backup-one"] * 3 + ["backup-two"],
        )


if __name__ == "__main__":
    unittest.main()
