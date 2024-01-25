import os
import unittest

import responses

from amazonorders import session
from amazonorders.constants import SIGN_IN_URL, SIGN_IN_REDIRECT_URL
from tests.testcase import TestCase

__author__ = "Alex Laird"
__copyright__ = "Copyright 2024, Alex Laird"
__version__ = "1.0.1"


@unittest.skipIf(os.environ.get("INTEGRATION_TEST", "False") == "True",
                 "Skipping, INTEGRATION_TEST=True was set in the environment")
class UnitTestCase(TestCase):
    RESOURCES_DIR = os.path.normpath(
        os.path.join(os.path.abspath(os.path.dirname(__file__)), "resources"))

    def setUp(self):
        session.DEFAULT_COOKIE_JAR_PATH = os.path.normpath(
            os.path.join(os.path.abspath(os.path.dirname(__file__)), ".config", "cookies.json"))
        if os.path.exists(session.DEFAULT_COOKIE_JAR_PATH):
            os.remove(session.DEFAULT_COOKIE_JAR_PATH)

    def given_login_responses_success(self):
        with open(os.path.join(self.RESOURCES_DIR, "signin.html"), "r", encoding="utf-8") as f:
            self.signin_response = responses.add(
                responses.GET,
                SIGN_IN_URL,
                body=f.read(),
                status=200,
            )
        with open(os.path.join(self.RESOURCES_DIR, "order-history-2018-0.html"), "r", encoding="utf-8") as f:
            self.authenticated_response = responses.add(
                responses.POST,
                SIGN_IN_REDIRECT_URL,
                body=f.read(),
                status=200,
            )

    def assert_login_responses_success(self):
        self.assertEqual(1, self.signin_response.call_count)
        self.assertEqual(1, self.authenticated_response.call_count)
