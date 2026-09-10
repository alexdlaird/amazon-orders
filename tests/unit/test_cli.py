__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import csv
import datetime
import io
import json
import os
from unittest.mock import patch

import responses
import yaml
from bs4 import BeautifulSoup
from click.testing import CliRunner

from amazonorders.cli import amazon_orders_cli
from amazonorders.entity.parsable import Parsable
from amazonorders.output import OutputFormatter
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
    def test_history_command_with_order_filter(self):
        # GIVEN
        year = 2018
        self.given_unauthenticated_home_page()
        self.given_login_responses_success()
        resp = self.given_any_order_history_exists("order-history-2018-0.html")

        # WHEN
        response = self.runner.invoke(amazon_orders_cli,
                                      [
                                          "--config-path", self.test_config.config_path,
                                          "--username", "some-username@gmail.com",
                                          "--password", "some-password",
                                          "history", "--year", year, "--order-filter", "digital-orders",
                                          "--single-page"])

        # THEN
        self.assertEqual(0, response.exit_code)
        self.assert_login_responses_success()
        self.assertEqual(1, resp.call_count)
        request_url = resp.calls[0].request.url
        self.assertIn(f"timeFilter=year-{year}", request_url)
        self.assertIn("orderFilter=digital-orders", request_url)

    @responses.activate
    def test_history_command_last_30_days(self):
        # GIVEN
        self.given_unauthenticated_home_page()
        self.given_login_responses_success()
        resp = self.given_order_history_exists_for_time_filter("last30", "order-history-2024-0.html")

        # WHEN
        response = self.runner.invoke(amazon_orders_cli,
                                      [
                                          "--config-path", self.test_config.config_path,
                                          "--username", "some-username@gmail.com",
                                          "--password", "some-password",
                                          "history", "--last-30-days", "--single-page"])

        # THEN
        self.assertEqual(0, response.exit_code)
        self.assertNotIn("TypeError", response.output)
        self.assert_login_responses_success()
        self.assertEqual(1, resp.call_count)
        self.assertIn("timeFilter=last30", resp.calls[0].request.url)

    @responses.activate
    def test_history_command_last_3_months(self):
        # GIVEN
        self.given_unauthenticated_home_page()
        self.given_login_responses_success()
        resp = self.given_order_history_exists_for_time_filter("months-3", "order-history-2024-0.html")

        # WHEN
        response = self.runner.invoke(amazon_orders_cli,
                                      [
                                          "--config-path", self.test_config.config_path,
                                          "--username", "some-username@gmail.com",
                                          "--password", "some-password",
                                          "history", "--last-3-months", "--single-page"])

        # THEN
        self.assertEqual(0, response.exit_code)
        self.assertNotIn("TypeError", response.output)
        self.assert_login_responses_success()
        self.assertEqual(1, resp.call_count)
        self.assertIn("timeFilter=months-3", resp.calls[0].request.url)

    @responses.activate
    def test_history_command_mutually_exclusive_flags(self):
        # GIVEN
        exclusive_flag_combinations = [
            ["--last-30-days", "--last-3-months"],
            ["--year", "2023", "--last-30-days"],
            ["--year", "2023", "--last-3-months"],
        ]

        for flags in exclusive_flag_combinations:
            with self.subTest(flags=flags):
                self.given_unauthenticated_home_page()
                self.given_login_responses_success()

                # WHEN
                response = self.runner.invoke(amazon_orders_cli,
                                              [
                                                  "--config-path", self.test_config.config_path,
                                                  "--username", "some-username@gmail.com",
                                                  "--password", "some-password",
                                                  "history", *flags])

                # THEN
                self.assertNotEqual(0, response.exit_code)
                self.assertIn("Only one of --last-30-days, --last-3-months, or --year "
                              "may be used at a time.", response.output)

    @responses.activate
    def test_history_command_full_details(self):
        # GIVEN
        year = 2023
        start_index = 10
        self.given_unauthenticated_home_page()
        self.given_login_responses_success()
        resp1 = self.given_order_history_exists(year, start_index)
        resp2 = self.given_any_order_details_exists("order-details-114-9460922-7737063.html")

        # WHEN
        response = self.runner.invoke(amazon_orders_cli,
                                      [
                                          "--config-path", self.test_config.config_path,
                                          "--username", "some-username@gmail.com",
                                          "--password", "some-password",
                                          "history", "--year", year, "--start-index", start_index,
                                          "--single-page", "--full-details"])

        # THEN
        self.assertEqual(0, response.exit_code)
        self.assert_login_responses_success()
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(10, resp2.call_count)
        self.assertIn("with full details", response.output)

    def test_history_command_invalid_start_index(self):
        # WHEN
        response = self.runner.invoke(amazon_orders_cli,
                                      [
                                          "--config-path", self.test_config.config_path,
                                          "--username", "some-username@gmail.com",
                                          "--password", "some-password",
                                          "history", "--start-index", "not-a-number"])

        # THEN
        self.assertNotEqual(0, response.exit_code)
        self.assertNotIn("Traceback", response.output)
        self.assertIn("Invalid value", response.output)

    @responses.activate
    def test_invoice_command(self):
        # GIVEN
        order_id = "123-4567890-1234567"
        self.given_unauthenticated_home_page()
        self.given_login_responses_success()
        resp = self.given_any_invoice_exists("get-invoice.html")

        # WHEN
        response = self.runner.invoke(amazon_orders_cli,
                                      [
                                          "--config-path", self.test_config.config_path,
                                          "--username", "some-username@gmail.com",
                                          "--password", "some-password",
                                          "invoice", order_id
                                      ])

        # THEN
        self.assertEqual(0, response.exit_code)
        self.assert_login_responses_success()
        self.assertEqual(1, resp.call_count)
        self.assertIn(f"orderID={order_id}", resp.calls[0].request.url)
        self.assertIn("Order Details", response.output)

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
    def test_order_transactions_command(self):
        # GIVEN
        order_id = "123-4567890-1234567"
        self.given_unauthenticated_home_page()
        self.given_login_responses_success()
        with open(os.path.join(self.RESOURCES_DIR, "transactions", "get-transactions-snippet.html"),
                  "r", encoding="utf-8") as f:
            resp = responses.add(
                responses.POST,
                f"{self.test_config.constants.TRANSACTION_HISTORY_URL}?transactionTag={order_id}",
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
                "order-transactions", order_id,
            ],
        )

        # THEN
        self.assertEqual(0, response.exit_code)
        self.assertEqual(1, resp.call_count)
        self.assert_login_responses_success()
        self.assertIn(f"transactionTag={order_id}", resp.calls[0].request.url)
        self.assertIn("2 Transactions parsed", response.output)

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
    def test_invoice_command_error(self):
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
                                          "invoice", "1234-fake-id"
                                      ])

        # THEN
        self.assertEqual(2, response.exit_code)
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(1, resp2.call_count)
        self.assertIn("Error from Amazon: There was a problem. Your password is incorrect.", response.output)

    @responses.activate
    def test_order_transactions_command_error(self):
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
                                          "order-transactions", "1234-fake-id"
                                      ])

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

    @responses.activate
    def test_history_command_output_json(self):
        # GIVEN
        year = 2018
        self.given_unauthenticated_home_page()
        self.given_login_responses_success()
        self.given_any_order_history_exists("order-history-2018-0.html")

        # WHEN
        response = self.runner.invoke(amazon_orders_cli,
                                      [
                                          "--config-path", self.test_config.config_path,
                                          "--username", "some-username@gmail.com",
                                          "--password", "some-password",
                                          "history", "--year", year, "--single-page",
                                          "--output", "json"])

        # THEN
        self.assertEqual(0, response.exit_code)
        orders = json.loads(response.stdout)
        self.assertEqual(10, len(orders))
        self.assertEqual("112-0399923-3070642", orders[3]["order_number"])
        self.assertEqual("2018-12-21", orders[3]["order_placed_date"])
        self.assertNotIn("parsed", orders[3])

    @responses.activate
    def test_history_command_output_yaml(self):
        # GIVEN
        year = 2018
        self.given_unauthenticated_home_page()
        self.given_login_responses_success()
        self.given_any_order_history_exists("order-history-2018-0.html")

        # WHEN
        response = self.runner.invoke(amazon_orders_cli,
                                      [
                                          "--config-path", self.test_config.config_path,
                                          "--username", "some-username@gmail.com",
                                          "--password", "some-password",
                                          "history", "--year", year, "--single-page",
                                          "--output", "yaml"])

        # THEN
        self.assertEqual(0, response.exit_code)
        orders = yaml.safe_load(response.stdout)
        self.assertEqual(10, len(orders))
        self.assertEqual("112-0399923-3070642", orders[3]["order_number"])

    @responses.activate
    def test_history_command_output_csv_is_one_row_per_order(self):
        # GIVEN
        year = 2018
        self.given_unauthenticated_home_page()
        self.given_login_responses_success()
        self.given_any_order_history_exists("order-history-2018-0.html")

        # WHEN
        response = self.runner.invoke(amazon_orders_cli,
                                      [
                                          "--config-path", self.test_config.config_path,
                                          "--username", "some-username@gmail.com",
                                          "--password", "some-password",
                                          "history", "--year", year, "--single-page",
                                          "--output", "csv"])

        # THEN
        self.assertEqual(0, response.exit_code)
        rows = list(csv.DictReader(io.StringIO(response.stdout)))
        self.assertEqual(10, len(rows))
        self.assertEqual(10, len(response.stdout.strip().split("\n")) - 1)
        self.assertEqual("112-0399923-3070642", rows[3]["order_number"])
        self.assertEqual("Alex Laird", rows[3]["recipient_name"])
        self.assertEqual("1", rows[3]["items_count"])

    def test_history_command_output_invalid_format(self):
        # WHEN
        response = self.runner.invoke(amazon_orders_cli,
                                      [
                                          "--config-path", self.test_config.config_path,
                                          "--username", "some-username@gmail.com",
                                          "--password", "some-password",
                                          "history", "--output", "xml"])

        # THEN
        self.assertEqual(2, response.exit_code)
        self.assertIn("Usage: ", response.output)


class StubEntity(Parsable):
    def __init__(self, config, name, tags):
        super().__init__(BeautifulSoup("<div></div>", config.bs4_parser), config)
        self.name = name
        self.completed_date = datetime.date(2024, 8, 23)
        self.nested = None
        self.tags = tags

    def __str__(self):
        return f"StubEntity: {self.name}"


class TestOutputFormatter(UnitTestCase):
    def given_formatter(self):
        return OutputFormatter(self.test_config)

    def given_entities(self):
        return [StubEntity(self.test_config, "First", ["a", "b"]),
                StubEntity(self.test_config, "Second", [])]

    def test_format_empty_contracts(self):
        # WHEN / THEN
        self.assertEqual("[]\n", self.given_formatter().format([], "json"))
        self.assertEqual([], yaml.safe_load(self.given_formatter().format([], "yaml")))
        self.assertEqual("", self.given_formatter().format([], "csv"))
        self.assertEqual("", self.given_formatter().format([], "text"))

    def test_format_json_serializes_any_entity(self):
        # WHEN
        serialized = json.loads(self.given_formatter().format(self.given_entities(), "json"))

        # THEN
        self.assertEqual(2, len(serialized))
        self.assertEqual("First", serialized[0]["name"])
        self.assertEqual("2024-08-23", serialized[0]["completed_date"])
        self.assertNotIn("parsed", serialized[0])
        self.assertNotIn("config", serialized[0])

    def test_format_text_falls_back_to_entity_str(self):
        # WHEN
        text = self.given_formatter().format(self.given_entities(), "text")

        # THEN
        self.assertEqual("StubEntity: First\n\nStubEntity: Second\n", text)

    def test_csv_flattens_nested_entities_and_lists(self):
        # GIVEN
        entities = [{"order_number": "111", "recipient": {"name": "Alex Laird", "address": "555 My Road"},
                     "items": [{"title": "One"}, {"title": "Two"}]}]

        # WHEN
        rows = list(csv.DictReader(io.StringIO(self.given_formatter()._csv(entities))))

        # THEN
        self.assertEqual(1, len(rows))
        self.assertEqual("Alex Laird", rows[0]["recipient_name"])
        self.assertEqual("555 My Road", rows[0]["recipient_address"])
        self.assertEqual("2", rows[0]["items_count"])
        self.assertEqual("One; Two", rows[0]["items"])

    def test_csv_keeps_one_physical_line_per_entity(self):
        # GIVEN
        entities = [{"order_number": "111", "recipient": {"address": "555 My Road\nChicago, IL 60007"}}]

        # WHEN
        output = self.given_formatter()._csv(entities)

        # THEN
        self.assertEqual(2, len(output.strip().split("\n")))
        self.assertIn("555 My Road Chicago, IL 60007", output)

    def test_csv_unions_columns_across_differing_entities(self):
        # GIVEN
        entities = [{"a": 1}, {"b": 2}]

        # WHEN
        rows = list(csv.DictReader(io.StringIO(self.given_formatter()._csv(entities))))

        # THEN
        self.assertEqual(["a", "b"], list(rows[0].keys()))
        self.assertEqual("", rows[0]["b"])
        self.assertEqual("2", rows[1]["b"])
