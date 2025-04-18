__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import os
import re
import shutil

import responses
from responses.matchers import urlencoded_params_matcher

from amazonorders import conf
from amazonorders.conf import AmazonOrdersConfig
from tests.testcase import TestCase


class UnitTestCase(TestCase):
    RESOURCES_DIR = os.path.normpath(
        os.path.join(os.path.abspath(os.path.dirname(__file__)), "resources"))

    def setUp(self):
        conf.DEFAULT_CONFIG_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), ".config")
        self.test_output_dir = os.path.join(conf.DEFAULT_CONFIG_DIR, "output")
        self.test_cookie_jar_path = os.path.join(conf.DEFAULT_CONFIG_DIR, "cookies.json")
        self.test_config = AmazonOrdersConfig(data={
            "output_dir": self.test_output_dir,
            "cookie_jar_path": self.test_cookie_jar_path
        })

        if os.path.exists(self.test_cookie_jar_path):
            os.remove(self.test_cookie_jar_path)

    def tearDown(self):
        if os.path.exists(conf.DEFAULT_CONFIG_DIR):
            shutil.rmtree(conf.DEFAULT_CONFIG_DIR)

    def given_login_responses_success(self):
        with open(os.path.join(self.RESOURCES_DIR, "auth", "signin.html"), "r", encoding="utf-8") as f:
            self.signin_response = responses.add(
                responses.GET,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )
        request_data = {
            "appAction": "SIGNIN_PWD_COLLECT",
            "appActionToken": "fefqbHYLHjhaxHj2B4HElW4j2F3UIwoj3D",
            "create": "0",
            "openid.return_to": "ape:aHR0cHM6Ly93d3cuYW1hem9uLmNvbT8=",
            "prevRID": "ape:SFJBTkVINFBKNkdaU0M2M0dCU00=",
            "subPageType": "SignInClaimCollect",
            "workflowState": "eyJ6aXAiOiJERUYiLCJlbmMiOiJBMjU2R0NNIiwiYWxnIjoiQTI1NktXIn0.Fhepst_Il21IpAOIEkjtr"
                             "H9SBeoOApEaG8sCosdpXrbypsISYkeDTw.J5kd8Up08rEVyLYz.TomGGK9BH7ZmR-rz-ZWg7lzmi9rDVc"
                             "oR_zEZopGMVbOKZhS_wbIx9gFQDdLvCGl8Hc17HJM32_Y2uPj1wEO9ADAYSetlkLDVWuz8xXF0ihtc9Y_"
                             "UNqDPv1JH_u6LxEOOdKkPIjDhH5yeZ_1OO0K_4Im2AUX6mYpNIu-hIio7WGMmMgANT98nQY8uNuRyPSQQ"
                             "x-TsboMC7T6ogs0xV-6aDyPDzlkCaOp-ZgDSwgrsy-1vxs_Ec0LTdMFSmL2E7zw.ZH7JT2vSuhaN7AGth"
                             "FkRXg",
            "email": "some-username",
            "password": "some-password",
            "rememberMe": "true"
        }
        with open(os.path.join(self.RESOURCES_DIR, "orders", "order-history-2018-0.html"), "r", encoding="utf-8") as f:
            self.authenticated_response = responses.add(
                responses.POST,
                self.test_config.constants.SIGN_IN_REDIRECT_URL,
                body=f.read(),
                status=200,
                match=[urlencoded_params_matcher(request_data)],
            )

    def given_order_history_exists(self, year, start_index=0):
        with open(os.path.join(self.RESOURCES_DIR, "orders", f"order-history-{year}-{start_index}.html"), "r",
                  encoding="utf-8") as f:
            optional_start_index = f"&startIndex={start_index}" if start_index else ""
            return responses.add(
                responses.GET,
                "{url}?timeFilter=year-{year}"
                "{optional_start_index}".format(url=self.test_config.constants.ORDER_HISTORY_URL,
                                                year=year,
                                                optional_start_index=optional_start_index),
                body=f.read(),
                status=200,
            )

    def given_any_order_history_exists(self, order_history_html_file):
        with open(os.path.join(self.RESOURCES_DIR, "orders", order_history_html_file), "r",
                  encoding="utf-8") as f:
            return responses.add(
                responses.GET,
                re.compile(f"{self.test_config.constants.ORDER_HISTORY_URL}?.*"),
                body=f.read(),
                status=200,
            )

    def given_any_order_details_exists(self, order_details_html_file):
        with open(os.path.join(self.RESOURCES_DIR, "orders", order_details_html_file), "r",
                  encoding="utf-8") as f:
            return responses.add(
                responses.GET,
                re.compile(f"{self.test_config.constants.ORDER_DETAILS_URL}?.*"),
                body=f.read(),
                status=200,
            )

    def assert_login_responses_success(self):
        self.assertEqual(1, self.signin_response.call_count)
        self.assertEqual(1, self.authenticated_response.call_count)
