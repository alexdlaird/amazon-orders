import os
import re
import unittest

import responses

from amazonorders import session
from amazonorders.constants import SIGN_IN_URL, SIGN_IN_REDIRECT_URL, ORDER_HISTORY_LANDING_URL, ORDER_HISTORY_URL, \
    ORDER_DETAILS_URL
from tests.testcase import TestCase

__author__ = "Alex Laird"
__copyright__ = "Copyright 2024, Alex Laird"
__version__ = "1.0.7"


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

    def given_order_history_landing_exists(self):
        with open(os.path.join(self.RESOURCES_DIR, "order-history-2023-10.html"), "r",
                  encoding="utf-8") as f:
            return responses.add(
                responses.GET,
                ORDER_HISTORY_LANDING_URL,
                body=f.read(),
                status=200,
            )

    def given_order_history_exists(self, year, start_index):
        with open(os.path.join(self.RESOURCES_DIR, "order-history-{}-{}.html".format(year, start_index)), "r",
                  encoding="utf-8") as f:
            return responses.add(
                responses.GET,
                "{}?timeFilter=year-{}{}".format(ORDER_HISTORY_URL,
                                                 year,
                                                 "&startIndex={}".format(start_index) if start_index else ""),
                body=f.read(),
                status=200,
            )

    def given_any_order_details_exists(self, order_html_file):
        with open(os.path.join(self.RESOURCES_DIR, order_html_file), "r",
                  encoding="utf-8") as f:
            return responses.add(
                responses.GET,
                re.compile("{}?.*".format(ORDER_DETAILS_URL)),
                body=f.read(),
                status=200,
            )

    def assert_login_responses_success(self):
        self.assertEqual(1, self.signin_response.call_count)
        self.assertEqual(1, self.authenticated_response.call_count)
