__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import json
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
        # Temporarily clear these if they are set in the environment, so they don't interfere with unit tests
        self.username = os.environ.pop('AMAZON_USERNAME', None)
        self.password = os.environ.pop('AMAZON_PASSWORD', None)
        self.otp_secret_key = os.environ.pop('AMAZON_OTP_SECRET_KEY', None)

        conf.DEFAULT_CONFIG_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), ".config")
        self.test_output_dir = os.path.join(conf.DEFAULT_CONFIG_DIR, "output")
        self.test_cookie_jar_path = os.path.join(conf.DEFAULT_CONFIG_DIR, "cookies.json")
        self.test_config = AmazonOrdersConfig(data={
            "output_dir": self.test_output_dir,
            "cookie_jar_path": self.test_cookie_jar_path,
            "auth_reattempt_wait": 0,
            "max_auth_retries": 0
        })

        if os.path.exists(self.test_cookie_jar_path):
            os.remove(self.test_cookie_jar_path)

    def tearDown(self):
        if os.path.exists(conf.DEFAULT_CONFIG_DIR):
            shutil.rmtree(conf.DEFAULT_CONFIG_DIR)

        # Reset environment variables that were temporarily cleared
        if self.username:
            os.environ["AMAZON_USERNAME"] = self.username
        if self.password:
            os.environ["AMAZON_PASSWORD"] = self.password
        if self.otp_secret_key:
            os.environ["AMAZON_OTP_SECRET_KEY"] = self.otp_secret_key

    def given_unauthenticated_home_page(self,
                                        auth_file="unauth-index.html"):
        with open(os.path.join(self.RESOURCES_DIR, "auth", auth_file), "r", encoding="utf-8") as f:
            self.index_response = responses.add(
                responses.GET,
                self.test_config.constants.BASE_URL,
                body=f.read(),
                status=200,
            )

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
            "email": "some-username@gmail.com",
            "password": "some-password",
            "rememberMe": "true"
        }
        with open(os.path.join(self.RESOURCES_DIR, "orders", "order-history-2018-0.html"), "r", encoding="utf-8") as f:
            self.authenticated_response = responses.add(
                responses.POST,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
                match=[urlencoded_params_matcher(request_data)],
            )

    def given_login_claim_responses_success(self):
        with open(os.path.join(self.RESOURCES_DIR, "auth", "signin-claim-username.html"), "r", encoding="utf-8") as f:
            self.signin_response = responses.add(
                responses.GET,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )
        request_data = {
            "appAction": "SIGNIN_CLAIM_COLLECT",
            "subPageType": "FullPageUnifiedClaimCollect",
            "claimCollectionWorkflow": "unified",
            "metadata1": "true",
            "isServerSideRouting": "true",
            "unifiedAuthTreatment": "T2",
            "signalUnknownCredentialUnifiedAuthWeblabActive": "false",
            "anti-csrftoken-a2z": "hIQUpYKT9xnC6tPiep3YBWI+1WkSrEVHZnPVCyUYiHwyAAAAAGireQ0AAAAB",
            "email": "some-username@gmail.com",
            "password": "some-password",
            "rememberMe": "true"
        }
        with open(os.path.join(self.RESOURCES_DIR, "auth", "signin-claim-password.html"), "r", encoding="utf-8") as f:
            self.signin_response = responses.add(
                responses.POST,
                self.test_config.constants.SIGN_IN_CLAIM_URL,
                body=f.read(),
                status=200,
                match=[urlencoded_params_matcher(request_data)]
            )
        request_data = {
            "appActionToken": "BhG3tDd8XVGMlLyGRHU5EqkhrLEhPbSfbQWXNlTqvvc=:2",
            "appAction": "SIGNIN_PWD_COLLECT",
            "crossDomainRPIDCount": "NONE",
            "metadata1": "ape:dHJ1ZQ==",
            "webAuthnChallengeIdForButton": "01UWKHiU_J628QwHq5cbimyRHISxOmYp:NA",
            "webAuthnGetParametersForButton": "eyJycElkIjoiYW1hem9uLmNvbSIsImNoYWxsZW5nZSI6IjAxVVdLSGlVX0o2MjhRd0hxNW"
                                              "NiaW15UkhJU3hPbVlwIiwidGltZW91dCI6OTAwMDAwLCJhbGxvd0NyZWRlbnRpYWxzIjpb"
                                              "eyJpZCI6IjQwQkZXSEd4Y21GUzc5OGRXejlyRk1aMFRLNG1SMmhncVFCckFOeXdpcGhycF"
                                              "V0cVd2YlhNdVRQNmFJXzRraksiLCJ0eXBlIjoicHVibGljLWtleSIsInRyYW5zcG9ydHMi"
                                              "OlsiaW50ZXJuYWwiLCJoeWJyaWQiXX1dLCJ1c2VyVmVyaWZpY2F0aW9uIjoicHJlZmVycm"
                                              "VkIn0=",
            "openid.return_to": "ape:aHR0cHM6Ly93d3cuYW1hem9uLmNvbS8/cmVmXz1uYXZfY3VzdHJlY19zaWduaW4=",
            "prevRID": "ape:UDVaQjE1WDlGWERWU1pRMTg2UEY=",
            "workflowState": "eyJ6aXAiOiJERUYiLCJlbmMiOiJBMjU2R0NNIiwiYWxnIjoiQTI1NktXIn0.g7Bw9I91vy2ZUf9oGQWcmv6sSQq"
                             "6NOqMVGiBPzS4Ids3xIZfM97jyw._6yBiSMIWGl_fqCG.OzgU6WgDOqPv_rsh9w-cgPEpoFS3uPKYGJjdTDTOKG"
                             "4m2-Tjqr7zlm2H2p5dOdcY1nVcfiRsnm_bB6FQ8gSCOURrk3DvqyqsbK7fW3J_p6JqiDaIGDv1dpHNxPdy6ePWF"
                             "Vta5ZILtY5iiz8pKvUWmcDlQoPA1b40vEkx3t0ZEOgsTNWQdYhkzp5Lra_2VW3RnthX5Z-fl4Ikmv5zAIdesqk1"
                             "5TtKWN_UIMdl3hFgyhtMDjz1A_7ro0Sq_rS6tCDng08NoKpGRZ3twozqyvuF7QsO1UpTly29IahqdCOdeI8PgQL"
                             "33DmTrMlnyDuBU82LSh4rjlJEBx2AhwjbFpJpZ4kPjF1yWpe1j2QugAOOStn1IgjzSGaICmrRKWIoFJql5yHJZh"
                             "E_y3SIMljizg_EChZiYSCa7n_8lEOWWpolNNj2bt3mAjhMNeCi_RG7Yt1NHcHKVRVfsBJkd7ltpeYPkS9hxrN-l"
                             "2w1K1jvvXDmskia7Dxkrx9IvpGXNG2jnACR7AtiEQ0S.51N-D0mkAliz3-kI3Um1Rg",
            "email": "some-username@gmail.com",
            "password": "some-password",
            "rememberMe": "true"
        }
        with open(os.path.join(self.RESOURCES_DIR, "orders", "order-history-2018-0.html"), "r", encoding="utf-8") as f:
            self.authenticated_response = responses.add(
                responses.POST,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
                match=[urlencoded_params_matcher(request_data)],
            )

    def given_authenticated_url_redirects_to_login(self,
                                                   method=responses.GET):
        return responses.add(
            method,
            re.compile(f"{self.test_config.constants.BASE_URL}/(gp|cpe|your-orders)/.*"),
            status=302,
            headers={"Location": self.test_config.constants.SIGN_IN_URL}
        )

    def given_authenticated_url_renders_login(self,
                                              method=responses.GET):
        with open(os.path.join(self.RESOURCES_DIR, "auth", "signin.html"), "r", encoding="utf-8") as f:
            return responses.add(
                method,
                re.compile(f"{self.test_config.constants.BASE_URL}/(gp|cpe|your-orders)/.*"),
                body=f.read(),
                status=200
            )

    def given_logout_response_success(self):
        return responses.add(
            responses.GET,
            self.test_config.constants.SIGN_OUT_URL,
            status=200,
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

    def given_order_history_exists_for_time_filter(self, time_filter, html_file, start_index=0):
        with open(os.path.join(self.RESOURCES_DIR, "orders", html_file), "r",
                  encoding="utf-8") as f:
            optional_start_index = f"&startIndex={start_index}" if start_index else ""
            return responses.add(
                responses.GET,
                "{url}?timeFilter={time_filter}"
                "{optional_start_index}".format(url=self.test_config.constants.ORDER_HISTORY_URL,
                                                time_filter=time_filter,
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

    def given_persisted_session_exists(self):
        cookies = {"session-id": "my-session-id",
                   "session-token": "my-session-token",
                   "x-main": "bleep-bleep-bloop",
                   "skin": "noskin"}
        with open(self.test_config.cookie_jar_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(cookies))

    def assert_login_responses_success(self):
        self.assertEqual(1, self.index_response.call_count)
        self.assertEqual(1, self.signin_response.call_count)
        self.assertEqual(1, self.authenticated_response.call_count)

    def assert_no_auth_cookies_persisted(self):
        with open(self.test_config.cookie_jar_path, "r") as f:
            cookies = json.loads(f.read())
            for cookie in self.test_config.constants.COOKIES_SET_WHEN_AUTHENTICATED:
                self.assertTrue(cookie not in cookies)
