__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import csv
import datetime
import io
import json
import os
import re
from unittest.mock import patch

import responses
import yaml
from bs4 import BeautifulSoup
from click.testing import CliRunner

from amazonorders.cli import _invoice_pdf_path, amazon_orders_cli
from amazonorders.entity.invoice_pdf import InvoicePdf
from amazonorders.entity.order import Order
from amazonorders.entity.parsable import Parsable
from amazonorders.entity.prime_payment import PrimePayment
from amazonorders.entity.transaction import Transaction
from amazonorders.exception import AmazonOrdersBrowserNotInstalledError
from amazonorders.output import OutputFormatter
from tests.unittestcase import UnitTestCase


class TestCli(UnitTestCase):
    def setUp(self):
        super().setUp()

        self.test_config.save()

        self.runner = CliRunner()

    def given_saved_config_value(self, key, value):
        with open(self.test_config.config_path, "r") as f:
            data = yaml.safe_load(f)
        data[key] = value
        with open(self.test_config.config_path, "w") as f:
            yaml.dump(data, f)

    def given_runner_with_split_streams(self):
        try:
            return CliRunner(mix_stderr=False)
        except TypeError:
            return CliRunner()

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

    def given_browser_not_installed(self, mock_browser_login, browser_types):
        mock_browser_login.return_value.login.side_effect = [
            AmazonOrdersBrowserNotInstalledError("Not installed.", meta={"browser_types": browser_types}),
            None
        ]

    def invoke_login_with_browser(self, input=None):
        return self.runner.invoke(amazon_orders_cli,
                                  ["--config-path", self.test_config.config_path, "login", "--browser"],
                                  input=input)

    @patch("amazonorders.cli.sys")
    @patch("amazonorders.cli.PlaywrightBrowserLauncher")
    @patch("amazonorders.cli.PlaywrightBrowserLogin")
    def test_login_with_browser_downloads_chosen_browser_and_retries(self, mock_browser_login, mock_launcher,
                                                                     mock_sys):
        # GIVEN
        mock_sys.stdin.isatty.return_value = True
        self.given_browser_not_installed(mock_browser_login, ["chromium", "firefox", "webkit"])
        mock_launcher.return_value.install.return_value = True

        # WHEN
        response = self.invoke_login_with_browser(input="x2")

        # THEN
        self.assertEqual(0, response.exit_code)
        self.assertIn("1: chromium\n2: firefox\n3: webkit\n--> Choose a browser to download [1]: 2\n",
                      response.output)
        mock_launcher.return_value.install.assert_called_once_with("firefox")
        self.assertIn("Config \"browser\" updated to \"firefox\"", response.output)
        self.assertEqual(2, mock_browser_login.return_value.login.call_count)

    @patch("amazonorders.cli.sys")
    @patch("amazonorders.cli.PlaywrightBrowserLauncher")
    @patch("amazonorders.cli.PlaywrightBrowserLogin")
    def test_login_with_browser_enter_downloads_default_browser(self, mock_browser_login, mock_launcher, mock_sys):
        # GIVEN
        mock_sys.stdin.isatty.return_value = True
        self.given_browser_not_installed(mock_browser_login, ["chromium", "firefox", "webkit"])
        mock_launcher.return_value.install.return_value = False

        # WHEN
        response = self.invoke_login_with_browser(input="\r")

        # THEN
        self.assertEqual(0, response.exit_code)
        self.assertIn("--> Choose a browser to download [1]: 1\n", response.output)
        mock_launcher.return_value.install.assert_called_once_with("chromium")

    @patch("amazonorders.cli.sys")
    @patch("amazonorders.cli.PlaywrightBrowserLauncher")
    @patch("amazonorders.cli.PlaywrightBrowserLogin")
    def test_login_with_browser_confirms_single_browser_type(self, mock_browser_login, mock_launcher, mock_sys):
        # GIVEN
        mock_sys.stdin.isatty.return_value = True
        self.given_browser_not_installed(mock_browser_login, ["firefox"])
        mock_launcher.return_value.install.return_value = False

        # WHEN
        response = self.invoke_login_with_browser(input="\n")

        # THEN
        self.assertEqual(0, response.exit_code)
        self.assertIn("Download firefox now? [Y/n]", response.output)
        mock_launcher.return_value.install.assert_called_once_with("firefox")
        self.assertNotIn("Config \"browser\" updated", response.output)

    @patch("amazonorders.cli.sys")
    @patch("amazonorders.cli.PlaywrightBrowserLauncher")
    @patch("amazonorders.cli.PlaywrightBrowserLogin")
    def test_login_with_browser_declined_download_fails(self, mock_browser_login, mock_launcher, mock_sys):
        # GIVEN
        mock_sys.stdin.isatty.return_value = True
        self.given_browser_not_installed(mock_browser_login, ["firefox"])

        # WHEN
        response = self.invoke_login_with_browser(input="n\n")

        # THEN
        self.assertEqual(2, response.exit_code)
        self.assertIn("Not installed.", response.output)
        mock_launcher.return_value.install.assert_not_called()

    @patch("amazonorders.cli.PlaywrightBrowserLauncher")
    @patch("amazonorders.cli.PlaywrightBrowserLogin")
    def test_login_with_browser_without_terminal_does_not_prompt(self, mock_browser_login, mock_launcher):
        # GIVEN
        self.given_browser_not_installed(mock_browser_login, ["chromium", "firefox", "webkit"])

        # WHEN
        response = self.invoke_login_with_browser()

        # THEN
        self.assertEqual(2, response.exit_code)
        self.assertIn("Not installed.", response.output)
        self.assertNotIn("Choose a browser", response.output)
        mock_launcher.return_value.install.assert_not_called()

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
        response = self.given_runner_with_split_streams().invoke(amazon_orders_cli,
                                                                 [
                                                                     "--config-path", self.test_config.config_path,
                                                                     "--username", "some-username@gmail.com",
                                                                     "--password", "some-password",
                                                                     "history", "--year", year, "--start-index",
                                                                     start_index, "--single-page"])

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
        self.assertNotIn("found so far", response.output)

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
    def test_history_command_with_family_member_id(self):
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
                                          "history", "--year", year, "--family-member-id", "A1EXAMPLETEEN1",
                                          "--single-page"])

        # THEN
        self.assertEqual(0, response.exit_code)
        self.assert_login_responses_success()
        self.assertEqual(1, resp.call_count)
        self.assertIn("familyMemberId=A1EXAMPLETEEN1", resp.calls[0].request.url)

    @responses.activate
    def test_family_members_command(self):
        # GIVEN
        self.given_unauthenticated_home_page()
        self.given_login_responses_success()
        resp = self.given_family_members_page_exists("order-history-family-members-snippet.html")

        # WHEN
        response = self.given_runner_with_split_streams().invoke(amazon_orders_cli,
                                                                 [
                                                                     "--config-path", self.test_config.config_path,
                                                                     "--username", "some-username@gmail.com",
                                                                     "--password", "some-password",
                                                                     "family-members", "--output", "json"])

        # THEN
        self.assertEqual(0, response.exit_code)
        self.assert_login_responses_success()
        self.assertEqual(1, resp.call_count)
        members = json.loads(response.stdout)
        self.assertEqual([{"id": "A1EXAMPLETEEN1", "name": "Jane Doe"}, {"id": "A2EXAMPLETEEN2", "name": "John Doe"}],
                         members)

    @responses.activate
    def test_family_members_command_error(self):
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
                                          "family-members"
                                      ])

        # THEN
        self.assertEqual(2, response.exit_code)
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(1, resp2.call_count)
        self.assertIn("Error from Amazon: There was a problem. Your password is incorrect.", response.output)

    @responses.activate
    def test_family_members_command_session_expired(self):
        # GIVEN
        self.given_persisted_session_exists()
        self.given_unauthenticated_home_page()
        self.given_login_responses_success()
        auth_redirect_response = self.given_authenticated_url_redirects_to_login()

        # WHEN
        response = self.runner.invoke(amazon_orders_cli,
                                      [
                                          "--config-path", self.test_config.config_path,
                                          "family-members"
                                      ])

        # THEN
        self.assertEqual(0, response.exit_code)
        self.assertEqual(1, auth_redirect_response.call_count)
        self.assertIn("Amazon redirected to login", response.output)

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
    def test_invoice_pdfs_command(self):
        # GIVEN
        self.given_unauthenticated_home_page()
        self.given_login_responses_success()
        resp = self.given_invoice_pdf_list("invoice-pdfs-multiple.html")

        # WHEN
        response = self.runner.invoke(amazon_orders_cli,
                                      [
                                          "--config-path", self.test_config.config_path,
                                          "--username", "some-username@gmail.com",
                                          "--password", "some-password",
                                          "invoice-pdfs", "302-0000000-0000002", "-o", "json"
                                      ])

        # THEN
        self.assertEqual(0, response.exit_code)
        self.assert_login_responses_success()
        self.assertEqual(1, resp.call_count)
        self.assertIn('"name": "Credit note"', response.output)
        self.assertIn("5 Invoice PDFs for 1 Orders", response.output)

    @responses.activate
    def test_invoice_pdfs_command_text(self):
        # GIVEN
        self.given_unauthenticated_home_page()
        self.given_login_responses_success()
        self.given_invoice_pdf_list("invoice-pdfs-multiple.html")
        link = (f"{self.test_config.constants.BASE_URL}/-/en/documents/download/"
                f"00000000-0000-4000-8000-00000000000{{}}/invoice.pdf")

        # WHEN
        response = self.runner.invoke(amazon_orders_cli,
                                      [
                                          "--config-path", self.test_config.config_path,
                                          "--username", "some-username@gmail.com",
                                          "--password", "some-password",
                                          "invoice-pdfs", "302-0000000-0000002"
                                      ])

        # THEN
        self.assertEqual(0, response.exit_code)
        self.assertIn(f"Invoice PDF: Invoice 1\n  Order #302-0000000-0000002\n  Link: {link.format(2)}\n",
                      response.output)
        self.assertIn(f"Invoice PDF: Credit note\n  Order #302-0000000-0000002\n  Credit Note: True\n"
                      f"  Link: {link.format(6)}\n", response.output)

    @responses.activate
    def test_invoice_pdfs_command_download(self):
        # GIVEN
        self.given_unauthenticated_home_page()
        self.given_login_responses_success()
        self.given_invoice_pdf_list("invoice-pdfs-multiple.html")
        download_resp = responses.add(responses.GET,
                                      re.compile(f"{self.test_config.constants.BASE_URL}/-/en/documents/download/.*"),
                                      body=b"%PDF-1.4 some-pdf", status=200, content_type="application/pdf")
        download_dir = os.path.join(self.test_output_dir, "invoices")

        # WHEN
        response = self.runner.invoke(amazon_orders_cli,
                                      [
                                          "--config-path", self.test_config.config_path,
                                          "--username", "some-username@gmail.com",
                                          "--password", "some-password",
                                          "invoice-pdfs", "302-0000000-0000002", "--download", download_dir
                                      ])

        # THEN
        self.assertEqual(0, response.exit_code)
        self.assertEqual(5, download_resp.call_count)
        self.assertEqual(["302-0000000-0000002_credit-note.pdf", "302-0000000-0000002_invoice-1.pdf",
                          "302-0000000-0000002_invoice-2.pdf", "302-0000000-0000002_invoice-3.pdf",
                          "302-0000000-0000002_invoice-4.pdf"], sorted(os.listdir(download_dir)))
        with open(os.path.join(download_dir, "302-0000000-0000002_credit-note.pdf"), "rb") as f:
            self.assertEqual(b"%PDF-1.4 some-pdf", f.read())

    @responses.activate
    def test_invoice_pdfs_command_order_without_invoices(self):
        # GIVEN
        self.given_unauthenticated_home_page()
        self.given_login_responses_success()
        self.given_invoice_pdf_list("invoice-pdfs-none.html")

        # WHEN
        response = self.runner.invoke(amazon_orders_cli,
                                      [
                                          "--config-path", self.test_config.config_path,
                                          "--username", "some-username@gmail.com",
                                          "--password", "some-password",
                                          "invoice-pdfs", "302-0000000-0000003"
                                      ])

        # THEN
        self.assertEqual(0, response.exit_code)
        self.assertIn("No invoice PDFs for Order 302-0000000-0000003.", response.output)
        self.assertIn("0 Invoice PDFs for 1 Orders", response.output)

    @responses.activate
    def test_invoice_pdfs_command_download_not_a_document(self):
        # GIVEN
        self.given_unauthenticated_home_page()
        self.given_login_responses_success()
        self.given_invoice_pdf_list("invoice-pdfs-single.html")
        responses.add(responses.GET, re.compile(f"{self.test_config.constants.BASE_URL}/-/en/documents/download/.*"),
                      body="<html></html>", status=200, content_type="text/html")

        # WHEN
        response = self.runner.invoke(amazon_orders_cli,
                                      [
                                          "--config-path", self.test_config.config_path,
                                          "--username", "some-username@gmail.com",
                                          "--password", "some-password",
                                          "invoice-pdfs", "302-0000000-0000001", "--download",
                                          os.path.join(self.test_output_dir, "invoices")
                                      ])

        # THEN
        self.assertEqual(2, response.exit_code)
        self.assertIn("returned Content-Type \"text/html\", not a PDF", response.output)

    @responses.activate
    def test_invoice_pdfs_command_session_expires(self):
        # GIVEN
        self.given_persisted_session_exists()
        self.given_unauthenticated_home_page()
        self.given_login_responses_success()
        auth_redirect_response = self.given_authenticated_url_redirects_to_login()
        self.given_logout_response_success()

        # WHEN
        response = self.runner.invoke(amazon_orders_cli,
                                      [
                                          "--config-path", self.test_config.config_path,
                                          "invoice-pdfs", "302-0000000-0000001"
                                      ])

        # THEN
        self.assertEqual(0, response.exit_code)
        self.assertEqual(1, auth_redirect_response.call_count)
        self.assertIn("Amazon redirected to login", response.output)

    def test_invoice_pdf_path_counts_repeated_names(self):
        # GIVEN
        invoice_pdf = InvoicePdf(BeautifulSoup('<a href="/documents/download/x/invoice.pdf">Invoice</a>',
                                               "html.parser").a,
                                 self.test_config, order_number="302-0000000-0000001")
        saved_paths = set()

        # WHEN
        paths = [_invoice_pdf_path("invoices", invoice_pdf, saved_paths) for _ in range(3)]

        # THEN
        self.assertEqual([os.path.join("invoices", "302-0000000-0000001_invoice.pdf"),
                          os.path.join("invoices", "302-0000000-0000001_invoice-2.pdf"),
                          os.path.join("invoices", "302-0000000-0000001_invoice-3.pdf")], paths)

    def given_invoice_pdf_list(self, filename):
        with open(os.path.join(self.RESOURCES_DIR, "invoices", filename), "r", encoding="utf-8") as f:
            return responses.add(responses.GET, self.test_config.constants.INVOICE_PDFS_URL, body=f.read(),
                                 status=200)

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
    def test_prime_payments_command(self):
        # GIVEN
        self.given_unauthenticated_home_page()
        self.given_login_responses_success()
        with open(os.path.join(self.RESOURCES_DIR, "prime", "prime-payments.html"), "r", encoding="utf-8") as f:
            resp = responses.add(
                responses.GET,
                f"{self.test_config.constants.PRIME_PAYMENTS_URL}",
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
                "prime-payments",
            ],
        )

        # THEN
        self.assertEqual(0, response.exit_code)
        self.assertEqual(1, resp.call_count)
        self.assert_login_responses_success()
        self.assertIn("Prime Payment: 2025-11-17\n  Order #D01-1000008-2000008\n  Total: $148.38\n"
                      "  Order Details Link: https://www.amazon.com/gp/your-account/order-details"
                      "?orderID=D01-1000008-2000008\n"
                      "  Receipt Link: https://www.amazon.com/gp/digital/your-account/order-summary.html"
                      "/ref=primecentral?ie=UTF8&orderID=D01-1000008-2000008&print=1", response.output)
        self.assertIn("8 Prime payments parsed", response.output)

    @responses.activate
    def test_prime_payments_command_json(self):
        # GIVEN
        self.given_unauthenticated_home_page()
        self.given_login_responses_success()
        with open(os.path.join(self.RESOURCES_DIR, "prime", "prime-payments.html"), "r", encoding="utf-8") as f:
            responses.add(
                responses.GET,
                f"{self.test_config.constants.PRIME_PAYMENTS_URL}",
                body=f.read(),
                status=200,
            )
        runner = self.given_runner_with_split_streams()

        # WHEN
        response = runner.invoke(
            amazon_orders_cli,
            [
                "--config-path", self.test_config.config_path,
                "--username", "some-username@gmail.com",
                "--password", "some-password",
                "prime-payments", "--output", "json",
            ],
        )

        # THEN
        self.assertEqual(0, response.exit_code)
        payments = json.loads(response.stdout)
        self.assertEqual(8, len(payments))
        self.assertEqual({"payment_date": "2025-11-17",
                          "total": 148.38,
                          "order_number": "D01-1000008-2000008",
                          "order_details_link": "https://www.amazon.com/gp/your-account/order-details"
                                                "?orderID=D01-1000008-2000008",
                          "receipt_link": "https://www.amazon.com/gp/digital/your-account/order-summary.html"
                                          "/ref=primecentral?ie=UTF8&orderID=D01-1000008-2000008&print=1"},
                         payments[0])

    @responses.activate
    def test_prime_payments_command_error(self):
        # GIVEN
        self.given_unauthenticated_home_page()
        self.given_login_responses_success()
        with open(os.path.join(self.RESOURCES_DIR, "prime", "prime-payments-error.html"), "r",
                  encoding="utf-8") as f:
            responses.add(
                responses.GET,
                f"{self.test_config.constants.PRIME_PAYMENTS_URL}",
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
                "prime-payments",
            ],
        )

        # THEN
        self.assertEqual(2, response.exit_code)
        self.assertIn("Could not parse Prime payments. Check if Amazon changed the HTML.", response.output)

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
    def test_gift_card_balance_command(self):
        # GIVEN
        self.given_unauthenticated_home_page()
        self.given_login_responses_success()
        with open(os.path.join(self.RESOURCES_DIR, "giftcards", "gift-card-balance-activity.html"),
                  "r", encoding="utf-8") as f:
            resp = responses.add(
                responses.GET,
                f"{self.test_config.constants.GIFT_CARD_BALANCE_URL}",
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
                "gift-card-balance",
            ],
        )

        # THEN
        self.assertEqual(0, response.exit_code)
        self.assertEqual(1, resp.call_count)
        self.assert_login_responses_success()
        self.assertIn("Gift Card Balance: $0.00", response.output)

    @responses.activate
    @patch("amazonorders.gift_cards.datetime", wraps=datetime)
    def test_gift_card_activity_command(self, mock_today):
        # GIVEN
        mock_today.date.today.return_value = datetime.date(2026, 5, 15)
        self.given_unauthenticated_home_page()
        self.given_login_responses_success()
        with open(os.path.join(self.RESOURCES_DIR, "giftcards", "gift-card-balance-activity.html"),
                  "r", encoding="utf-8") as f:
            resp = responses.add(
                responses.GET,
                f"{self.test_config.constants.GIFT_CARD_BALANCE_URL}",
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
                "gift-card-activity", "--days", 5,
            ],
        )

        # THEN
        self.assertEqual(0, response.exit_code)
        self.assertEqual(1, resp.call_count)
        self.assert_login_responses_success()
        self.assertIn("2 Gift Card activity entries parsed", response.output)
        self.assertIn("Gift Card Activity: 2026-05-12\n  Description: Gift Card applied to Amazon.com order\n"
                      "  Amount: -$19.48\n  Closing Balance: $0.00\n  Order #111-5500901-2478601", response.output)

    @responses.activate
    def test_gift_card_commands_invalid_page(self):
        # GIVEN
        self.given_unauthenticated_home_page()
        self.given_login_responses_success()
        with open(os.path.join(self.RESOURCES_DIR, "500.html"), "r", encoding="utf-8") as f:
            responses.add(
                responses.GET,
                f"{self.test_config.constants.GIFT_CARD_BALANCE_URL}",
                body=f.read(),
                status=200,
            )
        args = [
            "--config-path", self.test_config.config_path,
            "--username", "some-username@gmail.com",
            "--password", "some-password",
        ]

        # WHEN
        balance_response = self.runner.invoke(amazon_orders_cli, args + ["gift-card-balance"])
        activity_response = self.runner.invoke(amazon_orders_cli, args + ["gift-card-activity"])

        # THEN
        self.assertEqual(2, balance_response.exit_code)
        self.assertIn("Could not parse Gift Card balance.", balance_response.output)
        self.assertEqual(2, activity_response.exit_code)
        self.assertIn("Could not parse Gift Card activity.", activity_response.output)

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
    def test_persisted_session_stale_keeps_session(self):
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
        self.assertEqual(0, signout_response.call_count)
        with open(self.test_config.cookie_jar_path, "r") as f:
            self.assertIn("x-main", json.loads(f.read()))
        self.assertIn("Amazon redirected to login", response.output)
        self.assertIn("Call the `login` command to sign in again, or `login --browser`", response.output)

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

    def test_update_config_rejects_unimportable_language_package(self):
        # WHEN
        response = self.runner.invoke(amazon_orders_cli,
                                      [
                                          "--config-path", self.test_config.config_path,
                                          "update-config", "language_package", "does_not_exist"
                                      ])

        # THEN
        self.assertEqual(2, response.exit_code)
        self.assertIn("\"language_package\" was not updated", response.output)
        with open(self.test_config.config_path, "r") as f:
            self.assertIn("language_package: null", f.read())

    def test_update_config_fixes_saved_language_package_that_cannot_be_imported(self):
        # GIVEN
        self.given_saved_config_value("language_package", "does_not_exist")

        # WHEN
        history_response = self.runner.invoke(amazon_orders_cli,
                                              ["--config-path", self.test_config.config_path, "history"])
        version_response = self.runner.invoke(amazon_orders_cli,
                                              ["--config-path", self.test_config.config_path, "version"])
        update_response = self.runner.invoke(amazon_orders_cli,
                                             [
                                                 "--config-path", self.test_config.config_path,
                                                 "update-config", "language_package",
                                                 "tests.unit.example_language_package"
                                             ])

        # THEN
        self.assertEqual(2, history_response.exit_code)
        self.assertIn("Could not import \"language_package\" (does_not_exist)", history_response.output)
        self.assertIn("Call the `update-config` command to fix it.", history_response.output)
        self.assertEqual(0, version_response.exit_code)
        self.assertEqual(0, update_response.exit_code)
        with open(self.test_config.config_path, "r") as f:
            self.assertIn("language_package: tests.unit.example_language_package", f.read())

    @responses.activate
    def test_history_command_output_json(self):
        # GIVEN
        year = 2018
        self.given_unauthenticated_home_page()
        self.given_login_responses_success()
        self.given_any_order_history_exists("order-history-2018-0.html")

        # WHEN
        response = self.given_runner_with_split_streams().invoke(amazon_orders_cli,
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
        response = self.given_runner_with_split_streams().invoke(amazon_orders_cli,
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
        response = self.given_runner_with_split_streams().invoke(amazon_orders_cli,
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

    def given_order(self):
        with open(os.path.join(self.RESOURCES_DIR, "orders", "order-currency-stripped-snippet.html"), "r",
                  encoding="utf-8") as f:
            parsed = BeautifulSoup(f.read(), self.test_config.bs4_parser)
        return Order(parsed, self.test_config, full_details=True)

    def given_transaction(self):
        with open(os.path.join(self.RESOURCES_DIR, "transactions", "transaction-snippet.html"), "r",
                  encoding="utf-8") as f:
            parsed = BeautifulSoup(f.read(), self.test_config.bs4_parser)
        return Transaction(parsed, self.test_config, datetime.date(2024, 1, 1))

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

    def test_format_text_prime_payment_omits_missing_total(self):
        # GIVEN
        with open(os.path.join(self.RESOURCES_DIR, "prime", "prime-payments.html"), "r", encoding="utf-8") as f:
            parsed = BeautifulSoup(f.read(), self.test_config.bs4_parser)
        payment = PrimePayment(parsed.select_one(self.test_config.selectors.PRIME_PAYMENT_SELECTOR),
                               self.test_config)
        payment.total = None

        # WHEN
        text = self.given_formatter().format([payment], "text")

        # THEN
        self.assertIn("Prime Payment: 2025-11-17\n  Order #D01-1000008-2000008\n  Order Details Link: ", text)
        self.assertNotIn("Total", text)

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

    def test_order_text_shows_zero_grand_total(self):
        # GIVEN
        order = self.given_order()
        order.grand_total = 0.0

        # WHEN
        text = self.given_formatter().order_text(order)

        # THEN
        self.assertIn("\n  Grand Total: $0.00\n", text)

    def test_order_text_omits_missing_grand_total(self):
        # GIVEN
        order = self.given_order()
        order.grand_total = None

        # WHEN
        text = self.given_formatter().order_text(order)

        # THEN
        self.assertNotIn("Grand Total", text)

    def test_order_text_hides_zero_breakdown_totals(self):
        # GIVEN
        order = self.given_order()
        order.shipping_total = 0.0

        # WHEN
        text = self.given_formatter().order_text(order)

        # THEN
        self.assertNotIn("Shipping Total", text)
        self.assertIn("\n  Subtotal: $1,111.99", text)

    def test_transaction_text_shows_zero_grand_total(self):
        # GIVEN
        transaction = self.given_transaction()
        transaction.grand_total = 0.0

        # WHEN
        text = self.given_formatter().transaction_text(transaction)

        # THEN
        self.assertIn("\n  Grand Total: $0.00\n", text)

    def test_transaction_text_omits_missing_grand_total(self):
        # GIVEN
        transaction = self.given_transaction()
        transaction.grand_total = None

        # WHEN
        text = self.given_formatter().transaction_text(transaction)

        # THEN
        self.assertNotIn("Grand Total", text)
