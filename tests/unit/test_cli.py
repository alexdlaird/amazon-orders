__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import datetime
import os
from unittest.mock import patch

import responses
from click.testing import CliRunner

from amazonorders.cli import amazon_orders_cli
from tests.unittestcase import UnitTestCase


class TestCli(UnitTestCase):
    def setUp(self):
        super().setUp()

        self.test_config.save()

        self.runner = CliRunner()

    def test_missing_credentials(self):
        # WHEN
        response = self.runner.invoke(amazon_orders_cli,
                                      [
                                          "--config-path", self.test_config.config_path,
                                          "--username", "",
                                          "--password", ""
                                      ])

        # THEN
        self.assertEqual(2, response.exit_code)
        self.assertTrue("Usage: " in response.output)

    @responses.activate
    def test_login_command(self):
        # GIVEN
        self.given_unauthenticated_home_page()
        self.given_login_responses_success()

        # WHEN
        response = self.runner.invoke(amazon_orders_cli,
                                      [
                                          "--config-path", self.test_config.config_path,
                                          "--username", "some-username@gmail.com",
                                          "--password", "some-password",
                                          "login"
                                      ])

        self.assertEqual(0, response.exit_code)
        self.assert_login_responses_success()
        self.assertIn("Successfully logged in to Amazon", response.output)

    @responses.activate
    def test_logout_command(self):
        # GIVEN
        self.given_persisted_session_exists()
        signout_response = self.given_logout_response_success()

        # WHEN
        response = self.runner.invoke(amazon_orders_cli,
                                      [
                                          "--config-path", self.test_config.config_path,
                                          "logout"
                                      ])

        self.assertEqual(0, response.exit_code)
        self.assertEqual(1, signout_response.call_count)
        self.assertIn("Successfully logged out of Amazon", response.output)

    @responses.activate
    def test_check_session_command(self):
        # GIVEN
        self.given_persisted_session_exists()

        # WHEN
        response = self.runner.invoke(amazon_orders_cli,
                                      [
                                          "--config-path", self.test_config.config_path,
                                          "check-session"
                                      ])

        self.assertEqual(0, response.exit_code)
        self.assertIn("A persisted session exists", response.output)

    @responses.activate
    def test_history_command(self):
        # GIVEN
        year = 2023
        start_index = 10
        self.given_unauthenticated_home_page()
        self.given_login_responses_success()
        resp = self.given_order_history_exists(year, start_index)

        # WHEN
        response = self.runner.invoke(amazon_orders_cli,
                                      [
                                          "--config-path", self.test_config.config_path,
                                          "--username", "some-username@gmail.com",
                                          "--password", "some-password",
                                          "history", "--year", year, "--start-index", start_index, "--single-page"])

        # THEN
        self.assertEqual(0, response.exit_code)
        self.assert_login_responses_success()
        self.assertEqual(1, resp.call_count)
        self.assertIn("Order #112-0069846-3887437", response.output)
        self.assertIn("Order #113-1909885-6198667", response.output)
        self.assertIn("Order #112-4188066-0547448", response.output)
        self.assertIn("Order #112-9685975-5907428", response.output)
        self.assertIn("Order #112-1544475-9165068", response.output)
        self.assertIn("Order #112-9858173-0430628", response.output)
        self.assertIn("Order #112-3899501-4971443", response.output)
        self.assertIn("Order #112-2545298-6805068", response.output)
        self.assertIn("Order #113-4970960-6452217", response.output)
        self.assertIn("Order #112-9733602-9062669", response.output)

    @responses.activate
    def test_order_command(self):
        # GIVEN
        order_id = "112-2961628-4757846"
        self.given_unauthenticated_home_page()
        self.given_login_responses_success()
        with open(os.path.join(self.RESOURCES_DIR, "orders", "order-details-112-2961628-4757846.html"), "r",
                  encoding="utf-8") as f:
            resp1 = responses.add(
                responses.GET,
                f"{self.test_config.constants.ORDER_DETAILS_URL}?orderID={order_id}",
                body=f.read(),
                status=200,
            )

        # WHEN
        response = self.runner.invoke(amazon_orders_cli,
                                      [
                                          "--config-path", self.test_config.config_path,
                                          "--username", "some-username@gmail.com",
                                          "--password", "some-password",
                                          "order", order_id
                                      ])

        # THEN
        self.assertEqual(0, response.exit_code)
        self.assertEqual(1, resp1.call_count)
        self.assert_login_responses_success()
        self.assertIn("Order #112-2961628-4757846", response.output)

    @responses.activate
    @patch("amazonorders.transactions.datetime", wraps=datetime)
    def test_transactions_command(self, mock_today):
        # GIVEN
        mock_today.date.today.return_value = datetime.date(2024, 10, 11)
        days = 1
        self.given_unauthenticated_home_page()
        self.given_login_responses_success()
        with open(os.path.join(self.RESOURCES_DIR, "transactions", "get-transactions-snippet.html"),
                  "r", encoding="utf-8") as f:
            resp = responses.add(
                responses.POST,
                f"{self.test_config.constants.TRANSACTION_HISTORY_URL}",
                body=f.read(),
                status=200,
            )

        # WHEN
        response = self.runner.invoke(
            amazon_orders_cli,
            [
                "--config-path", self.test_config.config_path,
                "--username", "some-username@gmail.com",
                "--password", "some-password",
                "transactions", "--days",
                days,
            ],
        )

        # THEN
        self.assertEqual(0, response.exit_code)
        self.assertEqual(1, resp.call_count)
        self.assert_login_responses_success()
        self.assertIn("1 Transactions parsed", response.output)
        self.assertIn("Transaction: 2024-10-11\n  Order #123-4567890-1234567\n  Grand Total: -$45.19", response.output)

    @responses.activate
    def test_history_command_error(self):
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
        response = self.runner.invoke(amazon_orders_cli,
                                      [
                                          "--config-path", self.test_config.config_path,
                                          "--username", "some-username@gmail.com",
                                          "--password", "some-password",
                                          "history"
                                      ])

        # THEN
        self.assertEqual(2, response.exit_code)
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(1, resp2.call_count)
        self.assertIn("Error from Amazon: There was a problem. Your password is incorrect.", response.output)

    @responses.activate
    def test_order_command_error(self):
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
        response = self.runner.invoke(amazon_orders_cli,
                                      [
                                          "--config-path", self.test_config.config_path,
                                          "--username", "some-username@gmail.com",
                                          "--password", "some-password",
                                          "order", "1234-fake-id"
                                      ])

        # THEN
        self.assertEqual(2, response.exit_code)
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(1, resp2.call_count)
        self.assertIn("Error from Amazon: There was a problem. Your password is incorrect.", response.output)

    @responses.activate
    def test_transactions_command_error(self):
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
        response = self.runner.invoke(
            amazon_orders_cli,
            [
                "--config-path", self.test_config.config_path,
                "--username", "some-username@gmail.com",
                "--password", "some-password",
                "transactions"
            ],
        )

        # THEN
        self.assertEqual(2, response.exit_code)
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(1, resp2.call_count)
        self.assertIn("Error from Amazon: There was a problem. Your password is incorrect.", response.output)

    @responses.activate
    def test_persisted_session_stale_logout(self):
        # GIVEN
        self.given_persisted_session_exists()
        self.given_unauthenticated_home_page()
        self.given_login_responses_success()
        auth_redirect_response = self.given_authenticated_url_redirects_to_login()
        signout_response = self.given_logout_response_success()

        # WHEN
        response = self.runner.invoke(amazon_orders_cli,
                                      [
                                          "--config-path", self.test_config.config_path,
                                          "history"
                                      ])

        self.assertEqual(0, response.exit_code)
        self.assertEqual(1, auth_redirect_response.call_count)
        self.assertEqual(1, signout_response.call_count)
        self.assert_no_auth_cookies_persisted()
        self.assertIn("Amazon redirected to login", response.output)
        self.assertIn("logged out, so try running the command again", response.output)

    def test_update_config(self):
        # GIVEN
        self.test_config.save()
        with open(self.test_config.config_path, "r") as f:
            self.assertIn("max_auth_attempts: 10", f.read())

        # WHEN
        response = self.runner.invoke(amazon_orders_cli,
                                      [
                                          "--config-path", self.test_config.config_path,
                                          "update-config", "max_auth_attempts", "7"
                                      ])

        # THEN
        self.assertEqual(0, response.exit_code)
        self.assertIn("max_auth_attempts\" updated", response.output)
        with open(self.test_config.config_path, "r") as f:
            self.assertIn("max_auth_attempts: 7", f.read())
