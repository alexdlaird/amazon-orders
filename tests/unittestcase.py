__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import json
import os
import re
import shutil

import responses
from responses.matchers import query_string_matcher, urlencoded_params_matcher

from amazonorders import conf
from amazonorders.conf import AmazonOrdersConfig
from tests.testcase import TestCase


class UnitTestCase(TestCase):
    RESOURCES_DIR = os.path.normpath(
        os.path.join(os.path.abspath(os.path.dirname(__file__)), "resources"))

    def setUp(self):
        # Temporarily clear any config set in the environment, so it doesn't interfere with unit tests
        self.cleared_environment = {name: os.environ.pop(name) for name in list(os.environ)
                                    if name.startswith(conf.ENVIRONMENT_VARIABLE_PREFIX)}

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
        os.environ.update(self.cleared_environment)

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
            "password": "some-password"
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
            "email": "some-username@gmail.com"
        }
        with open(os.path.join(self.RESOURCES_DIR, "auth", "signin-claim-password.html"), "r", encoding="utf-8") as f:
            self.signin_response = responses.add(
                responses.POST,
                self.test_config.constants.SIGN_IN_CLAIM_URL,
                body=f.read(),
                status=200,
                match=[urlencoded_params_matcher(request_data)]
            )
        self.given_login_claim_password_responses_success()

    def given_login_email_only_claim_responses_success(self):
        self.given_email_only_claim_responses("signin-claim-password.html")
        self.given_login_claim_password_responses_success()

    def given_login_passkey_claim_responses_success(self):
        self.given_email_only_claim_responses("signin-claim-auth-passkey.html")
        with open(os.path.join(self.RESOURCES_DIR, "auth", "signin-claim-auth-password.html"), "r",
                  encoding="utf-8") as f:
            self.password_challenge_response = responses.add(
                responses.GET,
                f"{self.test_config.constants.SIGN_IN_CLAIM_URL}/auth",
                body=f.read(),
                status=200,
                match=[query_string_matcher("arb=00000000-0000-4000-8000-000000000002&selectedChallengeType=password")]
            )
        request_data = {
            "anti-csrftoken-a2z": "hH97dzyG0jXDtaTbMJH/OG9EcjbV0JOdO9ahThV66XUYAAAAAGrWURQAAAAB",
            "metadata1": "true",
            "arb": "00000000-0000-4000-8000-000000000002",
            "password": "some-password"
        }
        with open(os.path.join(self.RESOURCES_DIR, "auth", "signin-claim-auth-otp.html"), "r", encoding="utf-8") as f:
            self.password_response = responses.add(
                responses.POST,
                f"{self.test_config.constants.SIGN_IN_CLAIM_URL}/auth",
                body=f.read(),
                status=200,
                match=[urlencoded_params_matcher(request_data)],
            )
        request_data = {
            "anti-csrftoken-a2z": "hIHn+3FEGcDOEHEVOWyUOQ18+Mh/xAFC3Ce3jDbOEJsBAAAAAGrWUqAAAAAB",
            "metadata1": "true",
            "arb": "00000000-0000-4000-8000-000000000002",
            "authenticationMethod": "TOTPCode",
            "authenticatorId": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
            "capabilities": "noJs",
            "trustThisDevice": "1",
            "otpCode": "123456"
        }
        with open(os.path.join(self.RESOURCES_DIR, "orders", "order-history-2018-0.html"), "r", encoding="utf-8") as f:
            self.authenticated_response = responses.add(
                responses.POST,
                f"{self.test_config.constants.SIGN_IN_CLAIM_URL}/auth",
                body=f.read(),
                status=200,
                match=[urlencoded_params_matcher(request_data)],
            )

    def given_email_only_claim_responses(self, claim_response_html_file):
        with open(os.path.join(self.RESOURCES_DIR, "auth", "signin-claim-username-email-only-claim.html"), "r",
                  encoding="utf-8") as f:
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
            "emailOnlyClaim": "false",
            "webAuthnGetArbForAutofill": "00000000-0000-4000-8000-000000000002",
            "webAuthnGetParametersForAutofill": "eyJycElkIjoiYW1hem9uLmNvbSIsImNoYWxsZW5nZSI6IlR6akN2RkVHYjI3VEhPS21z"
                                                "YkRibUVuZ3BaR3NGZ3BsIiwidGltZW91dCI6OTAwMDAwLCJtZWRpYXRpb24iOiJjb25k"
                                                "aXRpb25hbCIsInVzZXJWZXJpZmljYXRpb24iOiJwcmVmZXJyZWQifQ==",
            "webAuthnChallengeIdForAutofill": "TzjCvFEGb27THOKmsbDbmEngpZGsFgpl:NA",
            "openid.ns": "http://specs.openid.net/auth/2.0",
            "openid.mode": "checkid_setup",
            "openid.return_to": "https://www.amazon.com/?ref_=nav_custrec_signin",
            "openid.assoc_handle": "usflex",
            "openid.pape.max_auth_age": "0",
            "openid.identity": "http://specs.openid.net/auth/2.0/identifier_select",
            "openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select",
            "signalUnknownCredentialUnifiedAuthWeblabActive": "true",
            "anti-csrftoken-a2z": "hNQTAkqRWDGiHXZuGnu9i+D2UMWi6sJjid1GiBbBRNRpAAAAAGrWLQkAAAAB",
            "email": "some-username@gmail.com"
        }
        with open(os.path.join(self.RESOURCES_DIR, "auth", claim_response_html_file), "r", encoding="utf-8") as f:
            self.signin_response = responses.add(
                responses.POST,
                self.test_config.constants.SIGN_IN_CLAIM_URL,
                body=f.read(),
                status=200,
                match=[urlencoded_params_matcher(request_data)]
            )

    def given_login_claim_password_responses_success(self):
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
            "password": "some-password"
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
            re.compile(f"{self.test_config.constants.BASE_URL}/(gp|cpe|gc|your-orders|progress-tracker)/.*"),
            status=302,
            headers={"Location": self.test_config.constants.SIGN_IN_URL}
        )

    def given_authenticated_url_renders_login(self,
                                              method=responses.GET):
        with open(os.path.join(self.RESOURCES_DIR, "auth", "signin.html"), "r", encoding="utf-8") as f:
            return responses.add(
                method,
                re.compile(f"{self.test_config.constants.BASE_URL}/(gp|cpe|gc|your-orders)/.*"),
                body=f.read(),
                status=200
            )

    def given_logout_response_success(self):
        return responses.add(
            responses.GET,
            self.test_config.constants.SIGN_OUT_URL,
            status=200,
        )

    @staticmethod
    def history_page_query(start_index):
        page = start_index // 10
        return f"&page={page}&startIndex={page * 10}" if page else ""

    def order_history_url(self, year, start_index=0):
        return (f"{self.test_config.constants.ORDER_HISTORY_URL}?timeFilter=year-{year}"
                f"{self.history_page_query(start_index)}")

    def given_order_history_exists(self, year, start_index=0, ref=None):
        with open(os.path.join(self.RESOURCES_DIR, "orders", f"order-history-{year}-{start_index}.html"), "r",
                  encoding="utf-8") as f:
            if ref:
                optional_paging = f"&startIndex={start_index}&ref_={ref}"
            else:
                optional_paging = self.history_page_query(start_index)
            return responses.add(
                responses.GET,
                "{url}?timeFilter=year-{year}"
                "{optional_paging}".format(url=self.test_config.constants.ORDER_HISTORY_URL,
                                           year=year,
                                           optional_paging=optional_paging),
                body=f.read(),
                status=200,
            )

    def given_order_history_exists_for_time_filter(self, time_filter, html_file, start_index=0):
        with open(os.path.join(self.RESOURCES_DIR, "orders", html_file), "r",
                  encoding="utf-8") as f:
            return responses.add(
                responses.GET,
                "{url}?timeFilter={time_filter}"
                "{optional_paging}".format(url=self.test_config.constants.ORDER_HISTORY_URL,
                                           time_filter=time_filter,
                                           optional_paging=self.history_page_query(start_index)),
                body=f.read(),
                status=200,
            )

    def given_family_members_page_exists(self, order_history_html_file):
        with open(os.path.join(self.RESOURCES_DIR, "orders", order_history_html_file), "r",
                  encoding="utf-8") as f:
            return responses.add(
                responses.GET,
                self.test_config.constants.ORDER_HISTORY_URL,
                body=f.read(),
                status=200,
            )

    def given_order_history_page_exists(self, status=200):
        with open(os.path.join(self.RESOURCES_DIR, "orders", "order-history-2018-0.html"), "r",
                  encoding="utf-8") as f:
            return responses.add(
                responses.GET,
                self.test_config.constants.ORDER_HISTORY_URL,
                body=f.read(),
                status=status,
            )

    def given_any_order_history_exists(self, order_history_html_file):
        with open(os.path.join(self.RESOURCES_DIR, "orders", order_history_html_file), "r",
                  encoding="utf-8") as f:
            return responses.add(
                responses.GET,
                re.compile(rf"^{re.escape(self.test_config.constants.ORDER_HISTORY_URL)}\?.*"),
                body=f.read(),
                status=200,
            )

    def given_any_order_details_exists(self, order_details_html_file):
        with open(os.path.join(self.RESOURCES_DIR, "orders", order_details_html_file), "r",
                  encoding="utf-8") as f:
            return responses.add(
                responses.GET,
                re.compile(rf"^{re.escape(self.test_config.constants.ORDER_DETAILS_URL)}\?.*"),
                body=f.read(),
                status=200,
            )

    def given_any_whole_foods_details_exists(self, order_details_html_file):
        with open(os.path.join(self.RESOURCES_DIR, "orders", order_details_html_file), "r",
                  encoding="utf-8") as f:
            return responses.add(
                responses.GET,
                re.compile(r"^https?://[^/]+/(fopo/order-details|wholefoodsmarket/receipts/order)\b.*"),
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

    def read_persisted_cookie_names(self):
        with open(self.test_config.cookie_jar_path, "r") as f:
            return {cookie["name"] for cookie in json.loads(f.read())}

    def assert_no_auth_cookies_persisted(self):
        cookie_names = self.read_persisted_cookie_names()
        for cookie in self.test_config.constants.COOKIES_SET_WHEN_AUTHENTICATED:
            self.assertTrue(cookie not in cookie_names)
