__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import importlib.util
import json
import os

from tests.unittestcase import UnitTestCase

SCRIPT_PATH = os.path.normpath(os.path.join(os.path.abspath(os.path.dirname(__file__)), "..", "..", "scripts",
                                            "redact-cookie-jar.py"))


def load_redact_cookie_jar():
    spec = importlib.util.spec_from_file_location("redact_cookie_jar", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cookie(name, value):
    return {"name": name, "value": value, "domain": ".amazon.com", "path": "/", "secure": True,
            "expires": 1800000000}


class TestRedactCookieJar(UnitTestCase):
    def setUp(self):
        super().setUp()

        self.redact_cookie_jar = load_redact_cookie_jar()

    def given_cookie_jar(self, cookies):
        os.makedirs(os.path.dirname(self.test_cookie_jar_path), exist_ok=True)
        with open(self.test_cookie_jar_path, "w", encoding="utf-8") as f:
            json.dump(cookies, f)

    def read_cookie_jar(self):
        with open(self.test_cookie_jar_path, "r", encoding="utf-8") as f:
            return {c["name"]: c for c in json.load(f)}

    def test_redact_cookie_jar_masks_session_cookies(self):
        # GIVEN
        self.given_cookie_jar([cookie("x-main", "some-auth-token"),
                               cookie("session-token", "some-session-token"),
                               cookie("ubid-main", "some-ubid")])

        # WHEN
        redacted = self.redact_cookie_jar.redact_cookie_jar(self.test_cookie_jar_path)

        # THEN
        self.assertTrue(redacted)
        cookies = self.read_cookie_jar()
        self.assertEqual(cookies["x-main"]["value"], "REDACTED")
        self.assertEqual(cookies["session-token"]["value"], "REDACTED")
        self.assertEqual(cookies["ubid-main"]["value"], "REDACTED")

    def test_redact_cookie_jar_keeps_locale_and_currency_cookies(self):
        # GIVEN
        self.given_cookie_jar([cookie("lc-main", "en_US"), cookie("i18n-prefs", "USD")])

        # WHEN
        self.redact_cookie_jar.redact_cookie_jar(self.test_cookie_jar_path)

        # THEN
        cookies = self.read_cookie_jar()
        self.assertEqual(cookies["lc-main"]["value"], "en_US")
        self.assertEqual(cookies["i18n-prefs"]["value"], "USD")

    def test_redact_cookie_jar_masks_unexpected_value_of_kept_cookie(self):
        # GIVEN
        self.given_cookie_jar([cookie("lc-main", "some-auth-token")])

        # WHEN
        self.redact_cookie_jar.redact_cookie_jar(self.test_cookie_jar_path)

        # THEN
        self.assertEqual(self.read_cookie_jar()["lc-main"]["value"], "REDACTED")

    def test_redact_cookie_jar_keeps_cookie_details(self):
        # GIVEN
        self.given_cookie_jar([cookie("x-main", "some-auth-token")])

        # WHEN
        self.redact_cookie_jar.redact_cookie_jar(self.test_cookie_jar_path)

        # THEN
        self.assertEqual(self.read_cookie_jar()["x-main"], cookie("x-main", "REDACTED"))

    def test_redact_cookie_jar_missing_file(self):
        # WHEN
        redacted = self.redact_cookie_jar.redact_cookie_jar(self.test_cookie_jar_path)

        # THEN
        self.assertFalse(redacted)
        self.assertFalse(os.path.exists(self.test_cookie_jar_path))
