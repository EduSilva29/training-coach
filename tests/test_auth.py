import os
import unittest
from unittest.mock import patch

import config
from auth import verify_credentials


class VerifyCredentialsTests(unittest.TestCase):
    def test_accepts_matching_credentials(self):
        self.assertTrue(verify_credentials("owner", "correct horse", "owner", "correct horse"))

    def test_rejects_mismatched_credentials(self):
        self.assertFalse(verify_credentials("owner", "wrong", "owner", "correct horse"))
        self.assertFalse(verify_credentials("someone else", "correct horse", "owner", "correct horse"))


class GetSettingTests(unittest.TestCase):
    def test_prefers_environment_over_streamlit_secrets(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "env-key"}):
            with patch.object(config.st, "secrets", {"GEMINI_API_KEY": "secret-key"}):
                self.assertEqual(config.get_setting("GEMINI_API_KEY"), "env-key")

    def test_reads_streamlit_secrets_when_environment_is_unset(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(config.st, "secrets", {"GEMINI_API_KEY": "secret-key"}):
                self.assertEqual(config.get_setting("GEMINI_API_KEY"), "secret-key")


if __name__ == "__main__":
    unittest.main()
