__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import datetime
import os
from unittest.mock import Mock, patch

import responses
from click.testing import CliRunner

from amazonorders.cli import amazon_orders_cli
from tests.unittestcase import UnitTestCase


class TestCli(UnitTestCase):
    def setUp(self):
        super().setUp()

        self.runner = CliRunner()

    def test_missing_credentials(self):
        # WHEN
        response = self.runner.invoke(amazon_orders_cli,
                                      ["--config-path", self.test_config.config_path,
                                       "--username", "", "--password", ""])

        # THEN
        self.assertEqual(2, response.exit_code)
        self.assertTrue("Usage: " in response.output)

    @responses.activate
    @patch("amazonorders.transactions.datetime", wraps=datetime)
    def test_history_command(self, mock_get_today: Mock):
        # GIVEN
        mock_get_today.date.today.return_value = datetime.date(2024, 10, 11)
        year = 2024
        start_index = 0
        self.given_login_responses_success()
        resp = self.given_order_history_exists(year, start_index)
        self.given_transactions_exists()

        # WHEN
        response = self.runner.invoke(amazon_orders_cli,
                                      ["--config-path", self.test_config.config_path,
                                       "--username", "some-username", "--password",
                                       "some-password", "history", "--year",
                                       year, "--start-index", start_index, "--single-page"])

        # THEN
        self.assertEqual(0, response.exit_code)
        self.assert_login_responses_success()
        self.assertEqual(1, resp.call_count)
        self.assertIn("Order #112-5939971-8962610", response.output)
        self.assertIn("Order #112-3319487-8015418", response.output)
        self.assertIn("Order #112-4482432-2955442", response.output)

    @responses.activate
    def test_order_command(self):
        # GIVEN
        order_id = "112-2961628-4757846"
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
                                      ["--config-path", self.test_config.config_path,
                                       "--username", "some-username", "--password",
                                       "some-password", "order", order_id])

        # THEN
        self.assertEqual(0, response.exit_code)
        self.assertEqual(1, resp1.call_count)
        self.assertIn("Order #112-2961628-4757846", response.output)

    @responses.activate
    @patch("amazonorders.transactions.datetime", wraps=datetime)
    def test_transactions_command(self, mock_get_today: Mock):
        # GIVEN
        mock_get_today.date.today.return_value = datetime.date(2024, 10, 11)
        days = 1
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
                "--config-path",
                self.test_config.config_path,
                "--username",
                "some-username",
                "--password",
                "some-password",
                "transactions",
                "--days",
                days,
            ],
        )

        # THEN
        self.assertEqual(0, response.exit_code)
        self.assertEqual(1, resp.call_count)
        self.assertIn("1 transactions parsed", response.output)
        self.assertIn("Transaction: 2024-10-11\n  Order #123-4567890-1234567\n  Grand Total: -$45.19", response.output)

    def test_update_config(self):
        # GIVEN
        self.test_config.save()
        with open(self.test_config.config_path, "r") as f:
            self.assertIn("max_auth_attempts: 10", f.read())

        # WHEN
        response = self.runner.invoke(amazon_orders_cli,
                                      ["--config-path", self.test_config.config_path,
                                       "update-config", "max_auth_attempts", "7"])

        # THEN
        self.assertEqual(0, response.exit_code)
        self.assertIn("max_auth_attempts\" updated", response.output)
        with open(self.test_config.config_path, "r") as f:
            self.assertIn("max_auth_attempts: 7", f.read())

    @responses.activate
    @patch("amazonorders.transactions.datetime", wraps=datetime)
    def test_history_command_download_invoices(self, mock_get_today: Mock):
        # GIVEN
        mock_get_today.date.today.return_value = datetime.date(2024, 10, 11)
        year = 2024
        order_id = "112-5939971-8962610"
        self.given_login_responses_success()
        self.given_order_history_exists(year)
        self.given_transactions_exists()
        with open(
            os.path.join(self.RESOURCES_DIR, "orders", f"order-details-{order_id}.html"),
            "r",
            encoding="utf-8",
        ) as f:
            responses.add(
                responses.GET,
                f"{self.test_config.constants.ORDER_DETAILS_URL}?orderID={order_id}",
                body=f.read(),
                status=200,
            )
        pdf_link = "/documents/download/def456/invoice.pdf"
        responses.add(
            responses.GET,
            f"{self.test_config.constants.ORDER_INVOICE_MENU_URL}?orderId={order_id}",
            body=f"<a href='{pdf_link}'>Invoice 1</a>",
            status=200,
        )
        responses.add(
            responses.GET,
            f"{self.test_config.constants.BASE_URL}{pdf_link}",
            body=b"PDFDATA",
            status=200,
            content_type="application/pdf",
        )

        # WHEN
        with self.runner.isolated_filesystem():
            response = self.runner.invoke(
                amazon_orders_cli,
                [
                    "--config-path",
                    self.test_config.config_path,
                    "--username",
                    "some-username",
                    "--password",
                    "some-password",
                    "--output-dir",
                    ".",
                    "history",
                    "--year",
                    year,
                    "--single-page",
                    "--full-details",
                    "--invoices",
                ],
            )

            # THEN
            self.assertEqual(0, response.exit_code)
            expected = "AmazonInvoice_20241101_112-5939971-8962610.pdf"
            self.assertTrue(os.path.exists(expected))

    @responses.activate
    @patch("amazonorders.transactions.datetime", wraps=datetime)
    def test_transactions_command_full_details_csv_invoices(self, mock_get_today: Mock):
        # GIVEN
        mock_get_today.date.today.return_value = datetime.date(2024, 10, 11)
        days = 1
        order_id = "123-4567890-1234567"
        self.given_login_responses_success()
        self.given_transactions_exists()
        self.given_any_order_details_exists("order-details-112-5939971-8962610.html")
        pdf_link = "/documents/download/abc123/invoice.pdf"
        responses.add(
            responses.GET,
            f"{self.test_config.constants.ORDER_INVOICE_MENU_URL}?orderId={order_id}",
            body=f"<a href='{pdf_link}'>Invoice 1</a>",
            status=200,
        )
        responses.add(
            responses.GET,
            f"{self.test_config.constants.BASE_URL}{pdf_link}",
            body=b"PDFDATA",
            status=200,
            content_type="application/pdf",
        )

        # WHEN
        with self.runner.isolated_filesystem():
            response = self.runner.invoke(
                amazon_orders_cli,
                [
                    "--config-path",
                    self.test_config.config_path,
                    "--username",
                    "some-username",
                    "--password",
                    "some-password",
                    "--output-dir",
                    ".",
                    "transactions",
                    "--days",
                    days,
                    "--full-details",
                    "--csv",
                    "--invoices",
                ],
            )

            # THEN
            self.assertEqual(0, response.exit_code)
            self.assertTrue(os.path.exists("transactions-1.csv"))
            expected = "AmazonInvoice_20241101_123-4567890-1234567.pdf"
            self.assertTrue(os.path.exists(expected))
