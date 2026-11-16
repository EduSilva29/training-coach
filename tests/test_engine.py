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
            patch.object(engine.time, "sleep"),
            patch("google.genai.Client"),
        ]
        self.mocks = [patcher.start() for patcher in self.patches]
        self.addCleanup(self._stop_patches)

        self.get_chat_history = self.mocks[4]
        self.client = self.mocks[-1].return_value

    def _stop_patches(self):
        for patcher in reversed(self.patches):
            patcher.stop()

    def test_busy_model_does_not_persist_user_message(self):
        self.client.models.generate_content.side_effect = [
            RuntimeError("503 unavailable"),
            RuntimeError("503 unavailable"),
            RuntimeError("503 unavailable"),
        ]

        with patch("builtins.print"), patch.object(engine, "save_message") as save_message:
            result = engine.ask_coach("What should I run today?")

        save_message.assert_not_called()
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
            result = engine.ask_coach("What should I run today?")

        self.assertEqual(result, "Coach reply")
        self.assertEqual(save_message.call_args_list, [
            call(role="user", content="What should I run today?"),
            call(role="assistant", content="Coach reply"),
        ])


if __name__ == "__main__":
    unittest.main()
