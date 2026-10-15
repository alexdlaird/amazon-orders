__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

import requests
import responses
from bs4 import BeautifulSoup
from responses.matchers import query_string_matcher, urlencoded_params_matcher

from amazonorders.conf import AmazonOrdersConfig
from amazonorders.constants import Constants
from amazonorders.exception import AmazonOrdersAuthError, AmazonOrdersError
from amazonorders.forms import JSAuthBlocker, MfaDeviceSelectForm
from amazonorders.session import AmazonSession, IODefault
from tests._auth_form_stubs import OtherStubAuthForm, StubAuthForm
from tests.unittestcase import UnitTestCase

try:
    import amazoncaptcha  # noqa: F401

    HAS_AMAZONCAPTCHA = True
except ImportError:
    HAS_AMAZONCAPTCHA = False


class TestSession(UnitTestCase):
    def setUp(self):
        super().setUp()

        self.amazon_session = AmazonSession("some-username@gmail.com",
                                            "some-password",
                                            config=self.test_config)

    @responses.activate
    def test_login(self):
        # GIVEN
        self.given_unauthenticated_home_page()
        self.given_login_responses_success()

        # WHEN
        self.amazon_session.login()

        # THEN
        self.assertTrue(self.amazon_session.is_authenticated)
        self.assert_login_responses_success()

    @responses.activate
    def test_login_claim(self):
        # GIVEN
        self.given_unauthenticated_home_page()
        self.given_login_claim_responses_success()

        # WHEN
        self.amazon_session.login()

        # THEN
        self.assertTrue(self.amazon_session.is_authenticated)
        self.assert_login_responses_success()

    @responses.activate
    def test_login_bad_index_retries(self):
        # GIVEN
        with open(os.path.join(self.RESOURCES_DIR, "auth", "unauth-bad-index.html"), "r", encoding="utf-8") as f:
            resp1 = responses.add(
                responses.GET,
                self.test_config.constants.BASE_URL,
                body=f.read(),
                status=200,
            )
        self.given_unauthenticated_home_page()
        self.given_login_claim_responses_success()

        # WHEN
        self.amazon_session.login()

        # THEN
        self.assertTrue(self.amazon_session.is_authenticated)
        self.assertEqual(1, resp1.call_count)
        self.assert_login_responses_success()

    @responses.activate
    def test_logout(self):
        # GIVEN
        signout_response = self.given_logout_response_success()
        self.amazon_session.is_authenticated = True
        old_session = self.amazon_session.session

        # WHEN
        self.amazon_session.logout()

        # THEN
        self.assertFalse(self.amazon_session.is_authenticated)
        self.assertNotEqual(old_session, self.amazon_session.session)
        self.assertEqual(1, signout_response.call_count)

    @responses.activate
    def test_debug_write_provisions_output_dir(self):
        # GIVEN a debug session whose output dir does not exist (the config no longer creates it)
        self.assertFalse(os.path.exists(self.test_output_dir))
        amazon_session = AmazonSession("some-username@gmail.com",
                                       "some-password",
                                       debug=True,
                                       config=self.test_config)
        responses.add(responses.GET,
                      f"{self.test_config.constants.BASE_URL}/some/page",
                      body="<html><body>debug page</body></html>",
                      status=200)

        # WHEN
        amazon_session.get(f"{self.test_config.constants.BASE_URL}/some/page")

        # THEN the debug write provisioned the output dir itself
        self.assertTrue(os.path.exists(self.test_output_dir))
        self.assertEqual(1, len(os.listdir(self.test_output_dir)))

    @responses.activate
    def test_request_cookies(self):
        # GIVEN
        config = AmazonOrdersConfig(data={
            "constants_class": "tests.unit.test_session.RequestCookiesConstants",
            "domain": "amazon.de",
            "output_dir": self.test_output_dir,
            "cookie_jar_path": self.test_cookie_jar_path,
        })
        amazon_session = AmazonSession("some-username@gmail.com", "some-password", config=config)
        amazon_session.session.cookies.set("lc-acbde", "de_DE", domain=".amazon.de", path="/")
        amazon_session.session.cookies.set("session-id", "some-session-id", domain=".amazon.de", path="/")
        url = f"{config.constants.BASE_URL}/some/page"
        responses.add(responses.GET, url, body="<html></html>", status=200,
                      headers={"Set-Cookie": "lc-acbde=de_DE; Domain=.amazon.de; Path=/"})

        # WHEN
        amazon_session.get(url)
        amazon_session.get(url)

        # THEN
        for call in responses.calls:
            cookie_header = call.request.headers["Cookie"]
            self.assertIn("lc-acbde=en_GB", cookie_header)
            self.assertNotIn("de_DE", cookie_header)
            self.assertIn("session-id=some-session-id", cookie_header)

    @responses.activate
    def test_only_language_cookie_by_default(self):
        # GIVEN
        url = f"{self.test_config.constants.BASE_URL}/some/page"
        responses.add(responses.GET, url, body="<html></html>", status=200)

        # WHEN
        self.amazon_session.get(url)

        # THEN
        self.assertEqual("lc-main=en_US", responses.calls[0].request.headers["Cookie"])

    def test_legacy_cookie_jar_loads_with_site_domain(self):
        # GIVEN
        self.given_persisted_session_exists()

        # WHEN
        amazon_session = AmazonSession("some-username@gmail.com", "some-password", config=self.test_config)

        # THEN
        cookies = {cookie.name: cookie.domain for cookie in amazon_session.session.cookies}
        self.assertEqual(".amazon.com", cookies["x-main"])
        self.assertEqual(".amazon.com", cookies["session-id"])

    @responses.activate
    def test_reissued_cookie_replaces_persisted_cookie(self):
        # GIVEN
        self.given_persisted_session_exists()
        amazon_session = AmazonSession("some-username@gmail.com", "some-password", config=self.test_config)
        self.given_response_reissues_cookie("x-main", "reissued-main")

        # WHEN
        amazon_session.get(f"{self.test_config.constants.BASE_URL}/some/page")

        # THEN
        self.assertEqual(1, len([cookie for cookie in amazon_session.session.cookies if cookie.name == "x-main"]))
        persisted = self.read_persisted_cookies()
        self.assertEqual(["reissued-main"], [cookie["value"] for cookie in persisted if cookie["name"] == "x-main"])
        self.assertEqual(".amazon.com", [cookie["domain"] for cookie in persisted if cookie["name"] == "x-main"][0])

    @responses.activate
    def test_unchanged_cookies_are_not_persisted(self):
        # GIVEN
        self.given_persisted_session_exists()
        amazon_session = AmazonSession("some-username@gmail.com", "some-password", config=self.test_config)
        with open(self.test_config.cookie_jar_path, "r", encoding="utf-8") as f:
            persisted_before = f.read()
        url = f"{self.test_config.constants.BASE_URL}/some/page"
        responses.add(responses.GET, url, body="<html></html>", status=200)

        # WHEN
        amazon_session.get(url)

        # THEN
        with open(self.test_config.cookie_jar_path, "r", encoding="utf-8") as f:
            self.assertEqual(persisted_before, f.read())

    @responses.activate
    def test_reissued_cookie_is_not_persisted_over_a_newer_save_by_another_process(self):
        # GIVEN
        self.given_persisted_session_exists()
        amazon_session = AmazonSession("some-username@gmail.com", "some-password", config=self.test_config)
        newer_sign_in = [{"name": "x-main", "value": "newer-sign-in", "domain": ".amazon.com", "path": "/"}]
        with open(self.test_config.cookie_jar_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(newer_sign_in))
        saved_at = os.path.getmtime(self.test_config.cookie_jar_path) + 10
        os.utime(self.test_config.cookie_jar_path, (saved_at, saved_at))
        self.given_response_reissues_cookie("x-main", "stale-reissue")

        # WHEN
        amazon_session.get(f"{self.test_config.constants.BASE_URL}/some/page")

        # THEN
        self.assertEqual(newer_sign_in, self.read_persisted_cookies())

    @responses.activate
    def test_reissued_cookie_is_persisted_again_after_this_session_saved(self):
        # GIVEN
        self.given_persisted_session_exists()
        amazon_session = AmazonSession("some-username@gmail.com", "some-password", config=self.test_config)
        self.given_response_reissues_cookie("x-main", "first-reissue")
        amazon_session.get(f"{self.test_config.constants.BASE_URL}/some/page")
        self.given_response_reissues_cookie("x-main", "second-reissue")

        # WHEN
        amazon_session.get(f"{self.test_config.constants.BASE_URL}/some/page")

        # THEN
        self.assertEqual(["second-reissue"],
                         [cookie["value"] for cookie in self.read_persisted_cookies() if cookie["name"] == "x-main"])

    @responses.activate
    def test_reissued_cookie_is_not_persisted_when_persist_cookies_is_false(self):
        # GIVEN
        self.given_persisted_session_exists()
        amazon_session = AmazonSession("some-username@gmail.com", "some-password", config=self.test_config)
        with open(self.test_config.cookie_jar_path, "r", encoding="utf-8") as f:
            persisted_before = f.read()
        self.given_response_reissues_cookie("x-main", "reissued-main")

        # WHEN
        amazon_session.get(f"{self.test_config.constants.BASE_URL}/some/page", persist_cookies=False)

        # THEN
        with open(self.test_config.cookie_jar_path, "r", encoding="utf-8") as f:
            self.assertEqual(persisted_before, f.read())

    @responses.activate
    def test_reissued_cookie_is_persisted_when_no_jar_existed_at_load(self):
        # GIVEN
        self.assertFalse(os.path.exists(self.test_config.cookie_jar_path))
        amazon_session = AmazonSession("some-username@gmail.com", "some-password", config=self.test_config)
        self.given_response_reissues_cookie("x-main", "reissued-main")

        # WHEN
        amazon_session.get(f"{self.test_config.constants.BASE_URL}/some/page")

        # THEN
        self.assertEqual(["reissued-main"],
                         [cookie["value"] for cookie in self.read_persisted_cookies() if cookie["name"] == "x-main"])
        self.assertEqual(os.path.getmtime(self.test_config.cookie_jar_path), amazon_session.cookie_jar_mtime)
        self.assertEqual(0o600, os.stat(self.test_config.cookie_jar_path).st_mode & 0o777)
        self.assertEqual([], [name for name in os.listdir(os.path.dirname(self.test_config.cookie_jar_path))
                              if name.endswith(".tmp")])

    def test_js_challenge_message_when_browser_extra_installed(self):
        # GIVEN
        blocker = JSAuthBlocker(self.test_config, "not a robot")
        parsed = BeautifulSoup("<html><body>Verify that you're not a robot</body></html>", "html.parser")

        # WHEN
        with patch("amazonorders.forms.importlib.util.find_spec", return_value=MagicMock()):
            with self.assertRaises(AmazonOrdersAuthError) as cm:
                blocker.select_form(self.amazon_session, parsed)

        # THEN
        self.assertIn("Add amazonorders.contrib.browser.playwright.PlaywrightAcicForm, then "
                      "amazonorders.contrib.browser.playwright.PlaywrightJSAuthForm, to auth_forms_classes",
                      str(cm.exception))
        self.assertNotIn("pip install", str(cm.exception))

    def test_js_challenge_message_when_browser_extra_not_installed(self):
        # GIVEN
        blocker = JSAuthBlocker(self.test_config, "not a robot")
        parsed = BeautifulSoup("<html><body>Verify that you're not a robot</body></html>", "html.parser")

        # WHEN
        with patch("amazonorders.forms.importlib.util.find_spec", return_value=None):
            with self.assertRaises(AmazonOrdersAuthError) as cm:
                blocker.select_form(self.amazon_session, parsed)

        # THEN
        self.assertIn("`pip install amazon-orders[browser]`", str(cm.exception))
        self.assertNotIn("auth_forms_classes", str(cm.exception))

    def given_response_reissues_cookie(self, name, value):
        responses.upsert(responses.GET,
                         f"{self.test_config.constants.BASE_URL}/some/page",
                         body="<html></html>",
                         status=200,
                         headers={"Set-Cookie": f"{name}={value}; Domain=.amazon.com; Path=/; Secure"})

    def read_persisted_cookies(self):
        with open(self.test_config.cookie_jar_path, "r", encoding="utf-8") as f:
            return json.loads(f.read())

    @responses.activate
    def test_login_claim_invalid_username(self):
        # GIVEN
        self.given_unauthenticated_home_page()
        with open(os.path.join(self.RESOURCES_DIR, "auth", "signin-claim-username.html"), "r", encoding="utf-8") as f:
            resp1 = responses.add(
                responses.GET,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )
        with open(os.path.join(self.RESOURCES_DIR, "auth", "post-signin-intent.html"), "r",
                  encoding="utf-8") as f:
            resp2 = responses.add(
                responses.POST,
                self.test_config.constants.SIGN_IN_CLAIM_URL,
                body=f.read(),
                status=200,
            )

        # WHEN
        with self.assertRaises(AmazonOrdersAuthError) as cm:
            self.amazon_session.login()

        # THEN
        self.assertFalse(self.amazon_session.is_authenticated)
        self.assertIn("Error from Amazon: Looks like you're new to Amazon", str(cm.exception))
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(1, resp2.call_count)

    @responses.activate
    def test_login_invalid_username(self):
        # GIVEN
        self.given_unauthenticated_home_page()
        with open(os.path.join(self.RESOURCES_DIR, "auth", "signin.html"), "r", encoding="utf-8") as f:
            resp1 = responses.add(
                responses.GET,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )
        with open(os.path.join(self.RESOURCES_DIR, "auth", "post-signin-invalid-email.html"), "r",
                  encoding="utf-8") as f:
            resp2 = responses.add(
                responses.POST,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )

        # WHEN
        with self.assertRaises(AmazonOrdersAuthError) as cm:
            self.amazon_session.login()

        # THEN
        self.assertFalse(self.amazon_session.is_authenticated)
        self.assertIn("Error from Amazon: There was a problem. We cannot find an account with that "
                      "email address.", str(cm.exception))
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(1, resp2.call_count)

    @responses.activate
    def test_login_invalid_password(self):
        # GIVEN
        self.given_unauthenticated_home_page()
        with open(os.path.join(self.RESOURCES_DIR, "auth", "signin.html"), "r", encoding="utf-8") as f:
            resp1 = responses.add(
                responses.GET,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )
        with open(os.path.join(self.RESOURCES_DIR, "auth", "post-signin-invalid-password.html"), "r",
                  encoding="utf-8") as f:
            resp2 = responses.add(
                responses.POST,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )

        # WHEN
        with self.assertRaises(AmazonOrdersAuthError) as cm:
            self.amazon_session.login()

        # THEN
        self.assertFalse(self.amazon_session.is_authenticated)
        self.assertEqual("Error from Amazon: There was a problem. Your password is incorrect.", str(cm.exception))
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(1, resp2.call_count)

    @responses.activate
    @patch("builtins.input")
    def test_mfa(self, input_mock):
        # GIVEN
        self.given_unauthenticated_home_page()
        with open(os.path.join(self.RESOURCES_DIR, "auth", "signin.html"), "r", encoding="utf-8") as f:
            resp1 = responses.add(
                responses.GET,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )
        with open(os.path.join(self.RESOURCES_DIR, "auth", "post-signin-mfa.html"), "r", encoding="utf-8") as f:
            resp2 = responses.add(
                responses.POST,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )
        with open(os.path.join(self.RESOURCES_DIR, "orders", "order-history-2018-0.html"), "r", encoding="utf-8") as f:
            resp3 = responses.add(
                responses.POST,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )

        # WHEN
        self.amazon_session.login()

        # THEN
        self.assertTrue(self.amazon_session.is_authenticated)
        self.assertEqual(1, input_mock.call_count)
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(1, resp2.call_count)
        self.assertEqual(1, resp3.call_count)

    @responses.activate
    @patch("builtins.input")
    def test_new_otp(self, input_mock):
        # GIVEN
        self.given_unauthenticated_home_page()
        with open(os.path.join(self.RESOURCES_DIR, "auth", "signin.html"), "r", encoding="utf-8") as f:
            resp1 = responses.add(
                responses.GET,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )
        with open(os.path.join(self.RESOURCES_DIR, "auth", "post-signin-new-otp.html"), "r", encoding="utf-8") as f:
            resp2 = responses.add(
                responses.POST,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )
        with open(os.path.join(self.RESOURCES_DIR, "auth", "post-signin-mfa.html"), "r", encoding="utf-8") as f:
            resp3 = responses.add(
                responses.POST,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )
        with open(os.path.join(self.RESOURCES_DIR, "orders", "order-history-2018-0.html"), "r", encoding="utf-8") as f:
            resp4 = responses.add(
                responses.POST,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )

        # WHEN
        self.amazon_session.login()

        # THEN
        self.assertTrue(self.amazon_session.is_authenticated)
        self.assertEqual(2, input_mock.call_count)
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(1, resp2.call_count)
        self.assertEqual(1, resp3.call_count)
        self.assertEqual(1, resp4.call_count)

    @responses.activate
    def test_amazon_blocks_auth(self):
        # GIVEN
        self.given_unauthenticated_home_page()
        with open(os.path.join(self.RESOURCES_DIR, "auth", "signin.html"), "r", encoding="utf-8") as f:
            resp1 = responses.add(
                responses.GET,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )
        resp2 = responses.add(
            responses.POST,
            self.test_config.constants.SIGN_IN_URL,
            status=503
        )

        # WHEN
        with self.assertRaises(AmazonOrdersAuthError) as cm:
            self.amazon_session.login()

        # THEN
        self.assertFalse(self.amazon_session.is_authenticated)
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(1, resp2.call_count)
        self.assertIn("The page https://www.amazon.com/ap/signin returned 503. Amazon had an issue on "
                      "their end, or may be temporarily blocking your requests.", str(cm.exception))

    @unittest.skipUnless(HAS_AMAZONCAPTCHA, "amazoncaptcha optional dependency not installed")
    @responses.activate
    def test_captcha_1(self):
        # GIVEN
        self.given_unauthenticated_home_page()
        with open(os.path.join(self.RESOURCES_DIR, "auth", "signin.html"), "r", encoding="utf-8") as f:
            resp1 = responses.add(
                responses.GET,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )
        resp2 = responses.add(
            responses.POST,
            self.test_config.constants.SIGN_IN_URL,
            status=302,
            headers={"Location": f"{self.test_config.constants.BASE_URL}/ap/cvf/request"}
        )
        with open(os.path.join(self.RESOURCES_DIR, "auth", "post-signin-captcha-1.html"), "r", encoding="utf-8") as f:
            resp3 = responses.add(
                responses.GET,
                f"{self.test_config.constants.BASE_URL}/ap/cvf/request",
                body=f.read(),
                status=200
            )
        with open(os.path.join(self.RESOURCES_DIR, "auth", "captcha_easy.jpg"), "rb") as f:
            resp4 = responses.add(
                responses.GET,
                "https://opfcaptcha-prod.s3.amazonaws.com/d32ff4fa043d4f969a1693adfb5d663a.jpg",
                body=f.read(),
                headers={"Content-Type": "image/jpeg"},
                status=200,
            )
        with open(os.path.join(self.RESOURCES_DIR, "orders", "order-history-2018-0.html"), "r", encoding="utf-8") as f:
            request_data = {
                "clientContext": "132-7968344-2156059",
                "cvf_captcha_captcha_action": "verifyCaptcha",
                "cvf_captcha_captcha_token": "sEusNpCt1AQ2rRr2f39/fwAAAAAAAAABPjglplbzE96xUsCT0ZswRq/pkFbblKXbv1cN6"
                                             "hKjq04HzZIYdTBAsdTA9fOZZZsAXG/6qLx8k6IQ8N5gpuIxjtQRhgYiPGzs/b0x0UO9Bp"
                                             "FhRTd5JGaUlxx3NdvsaBvaaCDpiGc3E6pzcmhqzqGOuMYMNCP0hLh1u1c+y+6xpzgSr9U"
                                             "YDWHZ9da61HQ8B/ay90YCc5vbiH556wwYffTosLN9LJzCydLp+zzJ2gU1NjWfGyDYvIWY"
                                             "t2h6dCxxJe1jIztakaLnkkJhYQEzHZMC9az8M0S+Yr87/IMh0m9/QMERYs+/cDlUT4jVs"
                                             "qii1qEt/m7pfJMz3G4f",
                "cvf_captcha_captcha_type": "imageCaptcha",
                "cvf_captcha_input": "FBJRAC",
                "cvf_captcha_js_enabled_metric": "0",
                "openid.assoc_handle": "usflex",
                "openid.mode": "checkid_setup",
                "openid.ns": "http://specs.openid.net/auth/2.0",
                "openid.pape.max_auth_age": "900",
                "openid.return_to": "https://www.amazon.com?",
                "pageId": "usflex",
                "verifyToken": "s|71202aba-23dd-378a-9cb3-75f90b00933e"
            }
            resp5 = responses.add(
                responses.POST,
                f"{self.test_config.constants.BASE_URL}/ap/cvf/verify",
                body=f.read(),
                status=200,
                match=[urlencoded_params_matcher(request_data)],
            )

        # WHEN
        self.amazon_session.login()

        # THEN
        self.assertTrue(self.amazon_session.is_authenticated)
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(1, resp2.call_count)
        self.assertEqual(1, resp3.call_count)
        self.assertEqual(1, resp4.call_count)
        self.assertEqual(1, resp5.call_count)

    @unittest.skipUnless(HAS_AMAZONCAPTCHA, "amazoncaptcha optional dependency not installed")
    @responses.activate
    def test_captcha_2(self):
        # GIVEN
        self.given_unauthenticated_home_page()
        with open(os.path.join(self.RESOURCES_DIR, "auth", "signin.html"), "r", encoding="utf-8") as f:
            resp1 = responses.add(
                responses.GET,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )
        with open(os.path.join(self.RESOURCES_DIR, "auth", "post-signin-captcha-2.html"), "r", encoding="utf-8") as f:
            resp2 = responses.add(
                responses.POST,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )
        with open(os.path.join(self.RESOURCES_DIR, "auth", "captcha_easy.jpg"), "rb") as f:
            resp3 = responses.add(
                responses.GET,
                "https://images-na.ssl-images-amazon.com/captcha/ddwwidnf/Captcha_gmwackhtzu.jpg",
                body=f.read(),
                headers={"Content-Type": "image/jpeg"},
                status=200,
            )
        resp4 = responses.add(
            responses.GET,
            f"{self.test_config.constants.BASE_URL}/errors/validateCaptcha",
            status=302,
            headers={"Location": f"{self.test_config.constants.BASE_URL}/"},
            match=[query_string_matcher(
                "amzn=Ozn2ONrAzGQc1ZETILqvvA%3D%3D&amzn-r=%2Fap%2Fsignin%3Fopenid.pape.max_auth_age%3D900%26"
                "openid.return_to%3Dhttps%253A%252F%252Fwww.amazon.com%253F%26openid.assoc_handle%3Dusflex%2"
                "6openid.mode%3Dcheckid_setup%26openid.ns%3Dhttp%253A%252F%252Fspecs.openid.net%252Fauth%252"
                "F2.0&amzn-pt=AuthenticationPortal&field-keywords=FBJRAC")],
        )
        # Successful Captcha redirects us back to the home page, which should restart the auth flow
        with open(os.path.join(self.RESOURCES_DIR, "index.html"), "r", encoding="utf-8") as f:
            resp5 = responses.add(
                responses.GET,
                f"{self.test_config.constants.BASE_URL}/",
                body=f.read(),
                status=200,
            )
        self.given_login_responses_success()

        # WHEN
        self.amazon_session.login()

        # THEN
        self.assertTrue(self.amazon_session.is_authenticated)
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(1, resp2.call_count)
        self.assertEqual(1, resp3.call_count)
        self.assertEqual(1, resp4.call_count)
        self.assertEqual(1, resp5.call_count)
        self.given_login_responses_success()

    @unittest.skipUnless(HAS_AMAZONCAPTCHA, "amazoncaptcha optional dependency not installed")
    @responses.activate
    def test_captcha_3(self):
        # GIVEN
        self.given_unauthenticated_home_page()
        with open(os.path.join(self.RESOURCES_DIR, "auth", "signin.html"), "r", encoding="utf-8") as f:
            resp1 = responses.add(
                responses.GET,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )
        with open(os.path.join(self.RESOURCES_DIR, "auth", "post-signin-captcha-3.html"), "r", encoding="utf-8") as f:
            resp2 = responses.add(
                responses.POST,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )
        with open(os.path.join(self.RESOURCES_DIR, "auth", "captcha_easy_2.jpg"), "rb") as f:
            resp3 = responses.add(
                responses.GET,
                "https://images-na.ssl-images-amazon.com/captcha/cdkxpfei/Captcha_yzifyqjijr.jpg",
                body=f.read(),
                headers={"Content-Type": "image/jpeg"},
                status=200,
            )
        with open(os.path.join(self.RESOURCES_DIR, "orders", "order-history-2018-0.html"), "r", encoding="utf-8") as f:
            resp4 = responses.add(
                responses.GET,
                f"{self.test_config.constants.BASE_URL}/errors/validateCaptcha",
                body=f.read(),
                status=200,
                match=[query_string_matcher("amzn=RHy879F26bdbSPHRWeZJyA%3D%3D&amzn-r=%2F"
                                            "&amzn-pt=AuthenticationPortal&field-keywords=KACXFB")],
            )

        # WHEN
        self.amazon_session.login()

        # THEN
        self.assertTrue(self.amazon_session.is_authenticated)
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(1, resp2.call_count)
        self.assertEqual(1, resp3.call_count)
        self.assertEqual(1, resp4.call_count)

    @unittest.skipIf(sys.platform == "win32", reason="Windows does not respect PIL's show() method in tests")
    @responses.activate
    @patch("builtins.input")
    @patch("PIL.Image.Image.show")
    def test_captcha_1_hard(self, show_mock, input_mock):
        # GIVEN
        self.given_unauthenticated_home_page()
        with open(os.path.join(self.RESOURCES_DIR, "auth", "signin.html"), "r", encoding="utf-8") as f:
            resp1 = responses.add(
                responses.GET,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )
        resp2 = responses.add(
            responses.POST,
            self.test_config.constants.SIGN_IN_URL,
            status=302,
            headers={"Location": f"{self.test_config.constants.BASE_URL}/ap/cvf/request"}
        )
        with open(os.path.join(self.RESOURCES_DIR, "auth", "post-signin-captcha-1.html"), "r", encoding="utf-8") as f:
            resp3 = responses.add(
                responses.GET,
                f"{self.test_config.constants.BASE_URL}/ap/cvf/request",
                body=f.read(),
                status=200
            )
        with open(os.path.join(self.RESOURCES_DIR, "auth", "captcha_hard.jpg"), "rb") as f:
            resp4 = responses.add(
                responses.GET,
                "https://opfcaptcha-prod.s3.amazonaws.com/d32ff4fa043d4f969a1693adfb5d663a.jpg",
                body=f.read(),
                headers={"Content-Type": "image/jpeg"},
                status=200,
            )
        with open(os.path.join(self.RESOURCES_DIR, "orders", "order-history-2018-0.html"), "r", encoding="utf-8") as f:
            resp5 = responses.add(
                responses.POST,
                f"{self.test_config.constants.BASE_URL}/ap/cvf/verify",
                body=f.read(),
                status=200,
            )

        # WHEN
        self.amazon_session.login()

        # THEN
        self.assertTrue(self.amazon_session.is_authenticated)
        self.assertEqual(1, input_mock.call_count)
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(1, resp2.call_count)
        self.assertEqual(1, resp3.call_count)
        # When amazoncaptcha is installed, the image URL is fetched twice (once by the solver,
        # once by the manual-prompt fallback); without it, only the fallback fetch happens.
        self.assertEqual(2 if HAS_AMAZONCAPTCHA else 1, resp4.call_count)
        self.assertEqual(1, resp5.call_count)

    @unittest.skipUnless(HAS_AMAZONCAPTCHA, "amazoncaptcha optional dependency not installed")
    @responses.activate
    def test_captcha_loop_retries_exhausted(self):
        # GIVEN
        self.given_unauthenticated_home_page()
        with open(os.path.join(self.RESOURCES_DIR, "auth", "signin.html"), "r", encoding="utf-8") as f:
            resp1 = responses.add(
                responses.GET,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )
        with open(os.path.join(self.RESOURCES_DIR, "auth", "post-signin-captcha-2.html"), "r", encoding="utf-8") as f:
            resp2 = responses.add(
                responses.POST,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )
        with open(os.path.join(self.RESOURCES_DIR, "auth", "captcha_easy.jpg"), "rb") as f:
            resp3 = responses.add(
                responses.GET,
                "https://images-na.ssl-images-amazon.com/captcha/ddwwidnf/Captcha_gmwackhtzu.jpg",
                body=f.read(),
                headers={"Content-Type": "image/jpeg"},
                status=200,
            )
        resp4 = responses.add(
            responses.GET,
            f"{self.test_config.constants.BASE_URL}/errors/validateCaptcha",
            status=302,
            headers={"Location": f"{self.test_config.constants.BASE_URL}/"},
            match=[query_string_matcher(
                "amzn=Ozn2ONrAzGQc1ZETILqvvA%3D%3D&amzn-r=%2Fap%2Fsignin%3Fopenid.pape.max_auth_age%3D900%26"
                "openid.return_to%3Dhttps%253A%252F%252Fwww.amazon.com%253F%26openid.assoc_handle%3Dusflex%2"
                "6openid.mode%3Dcheckid_setup%26openid.ns%3Dhttp%253A%252F%252Fspecs.openid.net%252Fauth%252"
                "F2.0&amzn-pt=AuthenticationPortal&field-keywords=FBJRAC")],
        )
        # Successful Captcha redirects us back to the home page, which should restart the auth flow
        with open(os.path.join(self.RESOURCES_DIR, "index.html"), "r", encoding="utf-8") as f:
            resp5 = responses.add(
                responses.GET,
                f"{self.test_config.constants.BASE_URL}/",
                body=f.read(),
                status=200,
            )

        # WHEN
        with self.assertRaises(AmazonOrdersAuthError) as cm:
            self.amazon_session.login()

        # THEN
        self.assertFalse(self.amazon_session.is_authenticated)
        self.assertEqual(5, resp1.call_count)
        self.assertEqual(5, resp2.call_count)
        self.assertEqual(5, resp3.call_count)
        self.assertEqual(5, resp4.call_count)
        self.assertEqual(5, resp5.call_count)
        self.assertIn("Authentication attempts exhausted.", str(cm.exception))

    @responses.activate
    def test_captcha_fields_keywords_1(self):
        # GIVEN
        self.given_unauthenticated_home_page("captcha-field-keywords.html")
        resp1 = responses.add(
            responses.GET,
            f"{self.test_config.constants.BASE_URL}/errors/validateCaptcha",
            status=302,
            headers={"Location": f"{self.test_config.constants.BASE_URL}/"},
            match=[query_string_matcher(
                "amzn=JC7LJGBaJlGTFs1Ao3s3XA%3D%3D&amzn-r=%2F&field-keywords=CJYYPE")],
        )
        # Successful Captcha redirects us back to the home page, which should restart the auth flow
        with open(os.path.join(self.RESOURCES_DIR, "index.html"), "r", encoding="utf-8") as f:
            resp2 = responses.add(
                responses.GET,
                f"{self.test_config.constants.BASE_URL}/",
                body=f.read(),
                status=200,
            )
        self.given_login_responses_success()

        # WHEN
        self.amazon_session.login()

        # THEN
        self.assertTrue(self.amazon_session.is_authenticated)
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(1, resp2.call_count)

    @responses.activate
    def test_captcha_fields_keywords_2(self):
        # GIVEN
        self.given_unauthenticated_home_page()
        with open(os.path.join(self.RESOURCES_DIR, "auth", "signin.html"), "r", encoding="utf-8") as f:
            resp1 = responses.add(
                responses.GET,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )
        with open(os.path.join(self.RESOURCES_DIR, "auth", "captcha-field-keywords.html"), "r",
                  encoding="utf-8") as f:
            resp2 = responses.add(
                responses.POST,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200
            )
        resp3 = responses.add(
            responses.GET,
            f"{self.test_config.constants.BASE_URL}/errors/validateCaptcha",
            status=302,
            headers={"Location": f"{self.test_config.constants.BASE_URL}/"},
            match=[query_string_matcher(
                "amzn=JC7LJGBaJlGTFs1Ao3s3XA%3D%3D&amzn-r=%2F&field-keywords=CJYYPE")],
        )
        # Successful Captcha redirects us back to the home page, which should restart the auth flow
        with open(os.path.join(self.RESOURCES_DIR, "index.html"), "r", encoding="utf-8") as f:
            resp4 = responses.add(
                responses.GET,
                f"{self.test_config.constants.BASE_URL}/",
                body=f.read(),
                status=200,
            )
        self.given_login_responses_success()

        # WHEN
        self.amazon_session.login()

        # THEN
        self.assertTrue(self.amazon_session.is_authenticated)
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(1, resp2.call_count)
        self.assertEqual(1, resp3.call_count)
        self.assertEqual(1, resp4.call_count)

    @responses.activate
    @patch("builtins.input")
    def test_captcha_otp(self, input_mock):
        # GIVEN
        self.given_unauthenticated_home_page()
        with open(os.path.join(self.RESOURCES_DIR, "auth", "signin.html"), "r", encoding="utf-8") as f:
            resp1 = responses.add(
                responses.GET,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )
        with open(os.path.join(self.RESOURCES_DIR, "auth", "post-signin-captcha-otp.html"),
                  "r", encoding="utf-8") as f:
            resp2 = responses.add(
                responses.POST,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )
        with open(os.path.join(self.RESOURCES_DIR, "orders", "order-history-2018-0.html"),
                  "r", encoding="utf-8") as f:
            resp3 = responses.add(
                responses.POST,
                f"{self.test_config.constants.BASE_URL}/ap/cvf/approval/verifyOtp",
                body=f.read(),
                status=200,
            )

        # WHEN
        self.amazon_session.login()

        # THEN
        self.assertTrue(self.amazon_session.is_authenticated)
        self.assertEqual(1, input_mock.call_count)
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(1, resp2.call_count)
        self.assertEqual(1, resp3.call_count)

    @responses.activate
    def test_js_waf_login_blocker(self):
        # GIVEN
        self.given_unauthenticated_home_page()
        with open(os.path.join(self.RESOURCES_DIR, "auth", "signin.html"), "r", encoding="utf-8") as f:
            resp1 = responses.add(
                responses.GET,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )
        with open(os.path.join(self.RESOURCES_DIR, "auth", "post-signin-js-bot-challenge.html"), "r",
                  encoding="utf-8") as f:
            resp2 = responses.add(
                responses.POST,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )

        # WHEN
        with self.assertRaises(AmazonOrdersAuthError) as cm:
            self.amazon_session.login()

        # THEN
        self.assertFalse(self.amazon_session.is_authenticated)
        self.assertIn("Amazon returned a JavaScript-based authentication challenge.",
                      str(cm.exception))
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(1, resp2.call_count)

    @responses.activate
    def test_acic_login_blocker(self):
        # GIVEN
        self.given_unauthenticated_home_page()
        with open(os.path.join(self.RESOURCES_DIR, "auth", "signin.html"), "r", encoding="utf-8") as f:
            resp1 = responses.add(
                responses.GET,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )
        with open(os.path.join(self.RESOURCES_DIR, "auth", "acic-challenge.html"), "r", encoding="utf-8") as f:
            resp2 = responses.add(
                responses.POST,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )

        # WHEN
        with self.assertRaises(AmazonOrdersAuthError) as cm:
            self.amazon_session.login()

        # THEN
        self.assertFalse(self.amazon_session.is_authenticated)
        self.assertIn("Amazon returned a JavaScript-based authentication challenge.",
                      str(cm.exception))
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(1, resp2.call_count)

    def _config_with(self, **extra):
        return AmazonOrdersConfig(data={
            "output_dir": self.test_output_dir,
            "cookie_jar_path": self.test_cookie_jar_path,
            "auth_reattempt_wait": 0,
            "max_auth_retries": 0,
            **extra,
        })

    def test_auth_forms_classes_loads_single_class(self):
        # GIVEN
        config = self._config_with(auth_forms_classes=["tests._auth_form_stubs.StubAuthForm"])

        # WHEN
        session = AmazonSession("user", "pass", config=config)

        # THEN
        self.assertIsInstance(session.auth_forms[-3], StubAuthForm)
        self.assertIsInstance(session.auth_forms[-1], JSAuthBlocker)

    def test_auth_forms_classes_preserves_order(self):
        # GIVEN
        config = self._config_with(auth_forms_classes=[
            "tests._auth_form_stubs.StubAuthForm",
            "tests._auth_form_stubs.OtherStubAuthForm",
        ])

        # WHEN
        session = AmazonSession("user", "pass", config=config)

        # THEN
        self.assertIsInstance(session.auth_forms[-4], StubAuthForm)
        self.assertIsInstance(session.auth_forms[-3], OtherStubAuthForm)
        self.assertIsInstance(session.auth_forms[-1], JSAuthBlocker)

    def test_auth_forms_classes_non_authform_class_raises(self):
        # GIVEN
        config = self._config_with(auth_forms_classes=["tests._auth_form_stubs.NotAnAuthForm"])

        # WHEN / THEN
        with self.assertRaises(AmazonOrdersError) as cm:
            AmazonSession("user", "pass", config=config)
        self.assertIn("NotAnAuthForm", str(cm.exception))
        self.assertIn("AuthForm", str(cm.exception))

    def test_auth_forms_classes_bad_path_raises(self):
        # GIVEN
        config = self._config_with(auth_forms_classes=["nonexistent.module.NotAClass"])

        # WHEN / THEN
        with self.assertRaises(AmazonOrdersError) as cm:
            AmazonSession("user", "pass", config=config)
        self.assertIn("nonexistent.module.NotAClass", str(cm.exception))

    def test_auth_forms_classes_empty_matches_default(self):
        # GIVEN
        config_empty = self._config_with(auth_forms_classes=[])
        config_default = self._config_with()

        # WHEN
        session_empty = AmazonSession("user", "pass", config=config_empty)
        session_default = AmazonSession("user", "pass", config=config_default)

        # THEN
        self.assertEqual(
            [type(f) for f in session_empty.auth_forms],
            [type(f) for f in session_default.auth_forms],
        )

    def test_auth_forms_kwarg_bypasses_config(self):
        # GIVEN
        config = self._config_with(auth_forms_classes=["tests._auth_form_stubs.StubAuthForm"])
        custom_forms = [JSAuthBlocker(config, "robot")]

        # WHEN
        session = AmazonSession("user", "pass", config=config, auth_forms=custom_forms)

        # THEN: config's auth_forms_classes is ignored when auth_forms is passed explicitly
        self.assertEqual(custom_forms, session.auth_forms)
        self.assertEqual(1, len(session.auth_forms))

    def test_request_timeout_forwarded(self):
        # GIVEN
        config = self._config_with(request_timeout=10)
        session = AmazonSession("user", "pass", config=config)
        mock_response = MagicMock()
        mock_response.text = ""

        with patch.object(session.session, "request", return_value=mock_response) as mock_request:
            # WHEN
            session.request("GET", "https://www.amazon.com/")

            # THEN
            self.assertEqual(10, mock_request.call_args.kwargs["timeout"])

    def test_request_timeout_not_set_by_default(self):
        # GIVEN
        mock_response = MagicMock()
        mock_response.text = ""

        with patch.object(self.amazon_session.session, "request", return_value=mock_response) as mock_request:
            # WHEN
            self.amazon_session.request("GET", "https://www.amazon.com/")

            # THEN
            self.assertNotIn("timeout", mock_request.call_args.kwargs)

    def test_request_timeout_caller_kwarg_wins(self):
        # GIVEN
        config = self._config_with(request_timeout=10)
        session = AmazonSession("user", "pass", config=config)
        mock_response = MagicMock()
        mock_response.text = ""

        with patch.object(session.session, "request", return_value=mock_response) as mock_request:
            # WHEN
            session.request("GET", "https://www.amazon.com/", timeout=5)

            # THEN
            self.assertEqual(5, mock_request.call_args.kwargs["timeout"])

    @responses.activate
    def test_request_connection_dropped(self):
        # GIVEN
        url = "https://www.amazon.com/"
        responses.add(responses.GET, url,
                      body=requests.ConnectionError("Remote end closed connection without response"))

        # WHEN
        with self.assertRaises(AmazonOrdersError) as cm:
            self.amazon_session.get(url)

        # THEN
        self.assertEqual("The page https://www.amazon.com/ returned no response: Remote end closed connection "
                         "without response. Amazon had an issue on their end, or may be temporarily blocking your "
                         "requests. Wait a bit before trying again.", str(cm.exception))
        self.assertIsInstance(cm.exception.__cause__, requests.ConnectionError)

    @responses.activate
    def test_request_timed_out(self):
        # GIVEN
        url = "https://www.amazon.com/"
        responses.add(responses.GET, url, body=requests.ReadTimeout("Read timed out"))

        # WHEN
        with self.assertRaises(AmazonOrdersError) as cm:
            self.amazon_session.get(url)

        # THEN
        self.assertIn("returned no response: Read timed out. Amazon had an issue on their end", str(cm.exception))
        self.assertIsInstance(cm.exception.__cause__, requests.ReadTimeout)

    @responses.activate
    def test_request_too_many_redirects(self):
        # GIVEN
        url = "https://www.amazon.com/"
        responses.add(responses.GET, url, body=requests.TooManyRedirects("Exceeded 30 redirects"))

        # WHEN
        with self.assertRaises(AmazonOrdersError) as cm:
            self.amazon_session.get(url)

        # THEN
        self.assertEqual("The page https://www.amazon.com/ returned no response: Exceeded 30 redirects.",
                         str(cm.exception))

    def test_credentials_environment_variables_win_over_arguments_and_config(self):
        # GIVEN
        with patch.dict(os.environ, {"AMAZON_USERNAME": "env-username", "AMAZON_OTP_SECRET_KEY": "env-otp"}):
            config = self._config_with(username="config-username", password="config-password")

        # WHEN
        amazon_session = AmazonSession("argument-username", "argument-password", config=config,
                                       otp_secret_key="argument-otp")

        # THEN
        self.assertEqual("env-username", amazon_session.username)
        self.assertEqual("argument-password", amazon_session.password)
        self.assertEqual("env-otp", amazon_session.otp_secret_key)


class RecordingIO(IODefault):
    def __init__(self, prompt_response):
        self.prompt_response = prompt_response
        self.choices = []

    def echo(self, msg, **kwargs):
        pass

    def prompt(self, msg, type=None, **kwargs):
        self.choices = kwargs.get("choices", [])

        return self.prompt_response


class TestMfaDeviceSelectForm(UnitTestCase):
    SMS_DEVICE_VALUE = "PKZe0oGlJ++N4zzxyJYvgbD5xe9sjooSY4K4t9Tt9e4=, SMS"
    VOICE_DEVICE_VALUE = "PKZe0oGlJ++N4zzxyJYvgbD5xe9sjooSY4K4t9Tt9e4=, VOICE"

    def given_device_select_form(self, prompt_response, with_labels=True):
        self.io = RecordingIO(prompt_response)
        amazon_session = AmazonSession("some-username@gmail.com",
                                       "some-password",
                                       io=self.io,
                                       config=self.test_config)
        with open(os.path.join(self.RESOURCES_DIR, "auth", "post-signin-new-otp.html"), "r", encoding="utf-8") as f:
            parsed = BeautifulSoup(f.read(), self.test_config.bs4_parser)
        if not with_labels:
            for label in parsed.select(self.test_config.selectors.MFA_DEVICE_SELECT_LABEL_SELECTOR):
                label.decompose()
        form = MfaDeviceSelectForm(self.test_config)
        form.select_form(amazon_session, parsed)

        return form

    def test_fill_form_lists_devices_by_readable_label(self):
        # GIVEN
        form = self.given_device_select_form(prompt_response=1)

        # WHEN
        form.fill_form()

        # THEN
        self.assertEqual(["1: Text me at my number ending in 1234",
                          "2: Call me at my number ending in 1234"],
                         self.io.choices)

    def test_fill_form_selects_device_matching_listed_number(self):
        # GIVEN
        form = self.given_device_select_form(prompt_response=2)

        # WHEN
        form.fill_form()

        # THEN
        self.assertEqual(self.VOICE_DEVICE_VALUE, form.data["otpDeviceContext"])

    def test_fill_form_rejects_choice_outside_listed_range(self):
        # GIVEN
        form = self.given_device_select_form(prompt_response=0)

        # WHEN
        with self.assertRaises(AmazonOrdersError) as cm:
            form.fill_form()

        # THEN
        self.assertIn("0", str(cm.exception))

    def test_fill_form_falls_back_to_input_value_when_label_missing(self):
        # GIVEN
        form = self.given_device_select_form(prompt_response=1, with_labels=False)

        # WHEN
        form.fill_form()

        # THEN
        self.assertEqual([f"1: {self.SMS_DEVICE_VALUE}",
                          f"2: {self.VOICE_DEVICE_VALUE}"],
                         self.io.choices)


class RequestCookiesConstants(Constants):
    REQUEST_COOKIES = {"lc-acbde": "en_GB"}
