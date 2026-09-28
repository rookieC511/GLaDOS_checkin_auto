import pathlib
import sys
import unittest
from unittest.mock import patch

import requests


sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import glados


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class GladosTests(unittest.TestCase):
    def test_split_cookies_supports_ampersand_and_newlines(self):
        self.assertEqual(glados.split_cookies("one& two\nthree\r\n"), ["one", "two", "three"])

    def test_status_and_successful_checkin(self):
        session = FakeSession(
            [
                FakeResponse({"data": {"leftDays": "52.8", "points": 255, "email": "hidden@example.com"}}),
                FakeResponse({"message": "Checkin! Got 13 Points"}),
            ]
        )
        status = glados.get_status(session, "https://glados.network", "secret-cookie")
        message = glados.check_in(session, "https://glados.network", "secret-cookie")
        self.assertEqual(status["points"], 255)
        self.assertEqual(message, "Checkin! Got 13 Points")
        self.assertNotIn("hidden@example.com", glados.format_status(status))

    def test_wrong_token_falls_back_to_next_token(self):
        session = FakeSession(
            [
                FakeResponse({"message": "Please checkin via https://glados.cloud"}),
                FakeResponse({"code": 0, "message": "Checkin Repeats!"}),
            ]
        )
        message = glados.check_in(session, "https://glados.network", "secret-cookie")
        self.assertEqual(message, "Checkin Repeats!")
        self.assertEqual(len(session.calls), 2)

    def test_invalid_cookie_is_a_real_failure(self):
        session = FakeSession([FakeResponse({"code": -2, "message": "没有权限"})])
        with self.assertRaisesRegex(glados.CheckinError, "Cookie"):
            glados.get_status(session, "https://glados.network", "expired-cookie")

    def test_checkin_uses_selected_origin_token_first(self):
        for host in ("glados.cloud", "glados.network", "glados.rocks"):
            with self.subTest(host=host):
                session = FakeSession([FakeResponse({"code": 0, "message": "Checkin Repeats!"})])
                glados.check_in(session, f"https://{host}", "secret-cookie")
                self.assertEqual(session.calls[0][2]["json"], {"token": host})

    def test_user_agent_matches_configured_login_browser(self):
        with patch.dict("os.environ", {"GLADOS_USER_AGENT": " Mac Chrome test "}):
            headers = glados.request_headers("https://glados.cloud", "secret-cookie")
        self.assertEqual(headers["user-agent"], "Mac Chrome test")

    def test_device_mismatch_has_actionable_error_without_sensitive_values(self):
        session = FakeSession([FakeResponse({
            "code": 4, "reason": "device-mismatch",
            "message": "Automated check-in detected. Please sign in again to continue.",
            "loginDevice": "secret-cookie",
        })])
        with self.assertRaisesRegex(glados.CheckinError, "GLADOS_USER_AGENT") as caught:
            glados.check_in(session, "https://glados.cloud", "secret-cookie")
        self.assertNotIn("secret-cookie", str(caught.exception))
        self.assertEqual(len(session.calls), 1)

    def test_automation_block_stops_token_attempts(self):
        session = FakeSession([FakeResponse({
            "message": "Automated check-in detected. Please sign in again to continue."
        })])
        with self.assertRaisesRegex(glados.CheckinError, "拒绝自动签到"):
            glados.check_in(session, "https://glados.cloud", "secret-cookie")
        self.assertEqual(len(session.calls), 1)

    def test_new_already_logged_response_is_success_without_retry(self):
        message = "Today's observation logged. Return tomorrow for more points."
        session = FakeSession([FakeResponse({"code": 1, "message": message})])
        self.assertEqual(glados.check_in(session, "https://glados.cloud", "secret-cookie"), message)
        self.assertEqual(len(session.calls), 1)
        self.assertFalse(glados.is_successful_checkin({"code": 4, "message": message}))

    @patch("glados.time.sleep", return_value=None)
    def test_transient_network_error_is_retried(self, _sleep):
        session = FakeSession(
            [
                requests.ConnectionError("temporary"),
                FakeResponse({"data": {"leftDays": "52"}}),
            ]
        )
        status = glados.get_status(session, "https://glados.network", "secret-cookie")
        self.assertEqual(status["leftDays"], "52")
        self.assertEqual(len(session.calls), 2)

    def test_failure_text_is_not_reported_as_success(self):
        self.assertFalse(glados.is_successful_checkin({"message": "Checkin failed"}))


if __name__ == "__main__":
    unittest.main()
