__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import os
import sys
import unittest
from unittest.mock import MagicMock

import responses
import yaml
from requests.utils import dict_from_cookiejar

from amazonorders import conf, util
from amazonorders.conf import AmazonOrdersConfig
from amazonorders.constants import Constants
from amazonorders.contrib.browser.playwright import PlaywrightAcicForm
from amazonorders.exception import AmazonOrdersAuthError, AmazonOrdersError
from amazonorders.orders import AmazonOrders
from amazonorders.region_data import REGION_SITES
from amazonorders.session import AmazonSession
from tests.unittestcase import UnitTestCase

EVIL_URL = "https://evil.example"
S3_PDF_URL = "https://s3.amazonaws.com/generated_invoices_v2/some-invoice.pdf"


class TestSiteUrl(unittest.TestCase):
    def test_is_site_url(self):
        base_url = "https://www.amazon.com"
        cases = {
            "https://www.amazon.com/your-orders": True,
            "https://amazon.com/your-orders": True,
            "https://WWW.AMAZON.COM/x": True,
            "http://www.amazon.com/x": False,
            "https://evil.example/x": False,
            "https://www.amazon.com.evil.example/x": False,
            "https://user@www.amazon.com/x": False,
            "https://www.amazon.com:8443/x": False,
            "https://www.amazon.com:bad/x": False,
            "/relative/path": False,
            "": False,
        }
        for url, expected in cases.items():
            with self.subTest(url=url):
                self.assertEqual(expected, util.is_site_url(url, base_url))


class TestDomainAllowList(UnitTestCase):
    def test_domain_rejects_non_amazon_hosts(self):
        for domain in ["evil.example", "amazon.example", "amazon.com.evil.example", "www.amazon.com.evil.example",
                       "https://amazon.com@evil.example", "amazon.com:8443", "amazon.com/path",
                       "https://www.amazon.com/?x=1", "amazon.com#f", "   ", 123]:
            with self.subTest(domain=domain):
                with self.assertRaises(AmazonOrdersError) as cm:
                    AmazonOrdersConfig(data={"domain": domain})
                self.assertIn("Config value for \"domain\"", str(cm.exception))

    def test_domain_rejects_http(self):
        for domain in ["http://www.amazon.com", "http://amazon.de"]:
            with self.subTest(domain=domain):
                with self.assertRaises(AmazonOrdersError):
                    AmazonOrdersConfig(data={"domain": domain})

    def test_domain_accepts_every_region_site_in_each_form(self):
        for tld in REGION_SITES:
            for domain, expected in [(f"amazon.{tld}", f"https://www.amazon.{tld}"),
                                     (f"www.amazon.{tld}", f"https://www.amazon.{tld}"),
                                     (f"https://www.amazon.{tld}/", f"https://www.amazon.{tld}"),
                                     (f"https://amazon.{tld}", f"https://amazon.{tld}"),
                                     (f"AMAZON.{tld.upper()}", f"https://www.amazon.{tld}")]:
                with self.subTest(domain=domain):
                    constants = AmazonOrdersConfig(data={"domain": domain}).constants
                    self.assertEqual(expected, constants.BASE_URL)
                    self.assertTrue(constants.SIGN_IN_URL.startswith(expected))

    def test_environment_variable_domain_rejected(self):
        os.environ["AMAZON_DOMAIN"] = "http://evil.example"
        try:
            with self.assertRaises(AmazonOrdersError):
                AmazonOrdersConfig()
        finally:
            del os.environ["AMAZON_DOMAIN"]

    def test_set_domain_rejects_bad_domain_and_keeps_previous(self):
        # GIVEN
        config = AmazonOrdersConfig(data={"domain": "amazon.de"})

        # WHEN
        with self.assertRaises(AmazonOrdersError):
            config.set_domain("https://evil.example")

        # THEN
        self.assertEqual("amazon.de", config._data["domain"])
        self.assertEqual("https://www.amazon.de", config.constants.BASE_URL)

    def test_update_config_rejects_bad_domain_and_keeps_previous(self):
        # GIVEN
        config = AmazonOrdersConfig()
        base_url = config.constants.BASE_URL

        # WHEN
        with self.assertRaises(AmazonOrdersError):
            config.update_config("domain", "evil.example", save=False)

        # THEN
        self.assertEqual(base_url, config.constants.BASE_URL)
        self.assertNotIn("domain", config._data)


class TestNoPinnedHost(UnitTestCase):
    def test_base_headers_have_no_host_header(self):
        self.assertNotIn("Host", Constants.BASE_HEADERS)
        self.assertNotIn("Host", AmazonOrdersConfig(data={"domain": "amazon.de"}).constants.BASE_HEADERS)


class TestOffSiteRequests(UnitTestCase):
    def setUp(self):
        super().setUp()

        self.amazon_session = AmazonSession("some-username@gmail.com", "some-password", config=self.test_config)
        self.amazon_session.session.cookies.set("x-main", "secret-main", domain=".amazon.com", path="/")
        self.base_url = self.test_config.constants.BASE_URL

    @responses.activate
    def test_request_does_not_pin_host(self):
        # GIVEN
        responses.add(responses.GET, f"{self.base_url}/some/page", body="<html></html>", status=200)

        # WHEN
        self.amazon_session.get(f"{self.base_url}/some/page")

        # THEN
        self.assertNotIn("Host", responses.calls[0].request.headers)
        self.assertIn("x-main=secret-main", responses.calls[0].request.headers["Cookie"])

    @responses.activate
    def test_request_refuses_off_site_url(self):
        # WHEN
        with self.assertRaises(AmazonOrdersError) as cm:
            self.amazon_session.get(f"{EVIL_URL}/path")

        # THEN
        self.assertIn("evil.example", str(cm.exception))
        self.assertEqual(0, len(responses.calls))

    @responses.activate
    def test_request_refuses_http_downgrade(self):
        # WHEN
        with self.assertRaises(AmazonOrdersError):
            self.amazon_session.get("http://www.amazon.com/x")

        # THEN
        self.assertEqual(0, len(responses.calls))

    @responses.activate
    def test_request_follows_same_site_redirect_with_cookies(self):
        # GIVEN
        responses.add(responses.GET, f"{self.base_url}/a", status=302, headers={"Location": "https://amazon.com/b"})
        responses.add(responses.GET, "https://amazon.com/b", body="<html></html>", status=200)

        # WHEN
        self.amazon_session.get(f"{self.base_url}/a")

        # THEN
        self.assertEqual(2, len(responses.calls))
        self.assertIn("x-main=secret-main", responses.calls[1].request.headers["Cookie"])

    @responses.activate
    def test_off_site_redirect_drops_cookies(self):
        # GIVEN
        responses.add(responses.GET, f"{self.base_url}/a", status=302, headers={"Location": f"{EVIL_URL}/b"})
        responses.add(responses.GET, f"{EVIL_URL}/b", body="<html></html>", status=200)

        # WHEN
        with self.assertLogs("amazonorders.session", level="WARNING"):
            self.amazon_session.get(f"{self.base_url}/a")

        # THEN
        self.assertEqual(2, len(responses.calls))
        self.assertIn("x-main=secret-main", responses.calls[0].request.headers["Cookie"])
        off_site_headers = responses.calls[1].request.headers
        for header in ("Cookie", "Origin", "Referer", "Host"):
            self.assertNotIn(header, off_site_headers)

    @responses.activate
    def test_off_site_redirect_with_body_is_refused(self):
        # GIVEN
        responses.add(responses.POST, f"{self.base_url}/ap/signin", status=307, headers={"Location": f"{EVIL_URL}/"})
        evil = responses.add(responses.POST, f"{EVIL_URL}/", body="<html></html>", status=200)

        # WHEN
        with self.assertRaises(AmazonOrdersError):
            self.amazon_session.post(f"{self.base_url}/ap/signin", data={"password": "some-password"})

        # THEN
        self.assertEqual(0, evil.call_count)

    @responses.activate
    def test_allow_off_site_sends_no_cookies(self):
        # GIVEN
        responses.add(responses.GET, S3_PDF_URL, body=b"%PDF-1.4", status=200, content_type="application/pdf",
                      headers={"Set-Cookie": "evil=1; Domain=s3.amazonaws.com; Path=/"})

        # WHEN
        response = self.amazon_session.get(S3_PDF_URL, binary=True, allow_off_site=True)

        # THEN
        self.assertEqual(b"%PDF-1.4", response.response.content)
        headers = responses.calls[0].request.headers
        for header in ("Cookie", "Origin", "Referer", "Host"):
            self.assertNotIn(header, headers)
        self.assertNotIn("evil", dict_from_cookiejar(self.amazon_session.session.cookies))
        self.assertFalse(os.path.exists(self.test_config.cookie_jar_path))

    @responses.activate
    def test_allow_off_site_on_site_url_keeps_cookies(self):
        # GIVEN
        responses.add(responses.GET, f"{self.base_url}/x.pdf", body=b"%PDF-1.4", status=200)

        # WHEN
        self.amazon_session.get(f"{self.base_url}/x.pdf", binary=True, allow_off_site=True)

        # THEN
        self.assertIn("x-main=secret-main", responses.calls[0].request.headers["Cookie"])

    @responses.activate
    def test_allow_off_site_requires_https(self):
        # WHEN
        with self.assertRaises(AmazonOrdersError):
            self.amazon_session.get("http://s3.amazonaws.com/x", allow_off_site=True)

        # THEN
        self.assertEqual(0, len(responses.calls))


class TestAuthFormsStayOnSite(UnitTestCase):
    @responses.activate
    def test_login_refuses_sign_in_form_posting_off_site(self):
        # GIVEN
        amazon_session = AmazonSession("some-username@gmail.com", "some-password", config=self.test_config)
        self.given_unauthenticated_home_page()
        with open(os.path.join(self.RESOURCES_DIR, "auth", "signin.html"), "r", encoding="utf-8") as f:
            signin_html = f.read()
        evil_signin_html = signin_html.replace(self.test_config.constants.SIGN_IN_URL, f"{EVIL_URL}/ap/signin")
        self.assertNotEqual(signin_html, evil_signin_html)
        responses.add(responses.GET, self.test_config.constants.SIGN_IN_URL, body=evil_signin_html, status=200)

        # WHEN
        with self.assertRaises(AmazonOrdersAuthError) as cm:
            amazon_session.login()

        # THEN
        self.assertIn("another site", str(cm.exception))
        for call in responses.calls:
            self.assertNotIn("evil.example", call.request.url)
            self.assertNotIn("some-password", str(call.request.body or ""))


class TestInvoicesStayOnSite(UnitTestCase):
    def setUp(self):
        super().setUp()

        self.amazon_session = AmazonSession("some-username@gmail.com", "some-password", config=self.test_config)
        self.amazon_session.is_authenticated = True
        self.amazon_session.session.cookies.set("x-main", "secret-main", domain=".amazon.com", path="/")
        self.amazon_orders = AmazonOrders(self.amazon_session)

    def given_invoice(self):
        with open(os.path.join(self.RESOURCES_DIR, "invoices", "invoice-pdfs-single.html"), "r",
                  encoding="utf-8") as f:
            return AmazonOrders.parse_invoices(f.read(), self.test_config, order_number="302-0000000-0000001")[1]

    @responses.activate
    def test_download_invoice_off_site_pdf_sends_no_cookies(self):
        # GIVEN
        invoice = self.given_invoice()
        invoice.link = S3_PDF_URL
        responses.add(responses.GET, S3_PDF_URL, body=b"%PDF-1.4 some-pdf", status=200,
                      content_type="application/pdf")

        # WHEN
        content = self.amazon_orders.download_invoice(invoice)

        # THEN
        self.assertEqual(b"%PDF-1.4 some-pdf", content)
        self.assertNotIn("Cookie", responses.calls[0].request.headers)

    @responses.activate
    def test_download_invoice_off_site_html_refused(self):
        # GIVEN
        invoice = self.given_invoice()
        invoice.link = f"{EVIL_URL}/print.html"
        invoice.format = self.test_config.constants.INVOICE_HTML_FORMAT

        # WHEN
        with self.assertRaises(AmazonOrdersError):
            self.amazon_orders.download_invoice(invoice)

        # THEN
        self.assertEqual(0, len(responses.calls))

    @responses.activate
    def test_whole_foods_off_site_details_link_is_skipped(self):
        # GIVEN
        order = MagicMock(is_whole_foods=True, order_details_link=f"{EVIL_URL}/fopo/order-details",
                          order_number="123-0000000-0000000")
        self.test_config.order_cls = MagicMock(return_value=order)

        # WHEN
        with self.assertLogs("amazonorders", level="WARNING"):
            result = self.amazon_orders._build_order(MagicMock(), full_details=True, current_index=0)

        # THEN
        self.assertIs(order, result)
        self.assertEqual(0, len(responses.calls))

    def test_whole_foods_details_url_matches_path_only(self):
        self.assertTrue(self.amazon_orders._is_whole_foods_details_url(
            f"{self.test_config.constants.BASE_URL}/fopo/order-details?orderId=1"))
        self.assertFalse(self.amazon_orders._is_whole_foods_details_url(
            f"{self.test_config.constants.BASE_URL}/x?next=/fopo/order-details"))


@unittest.skipIf(sys.platform == "win32", reason="Windows does not support POSIX file permissions")
class TestOwnerOnlyFiles(UnitTestCase):
    def test_config_is_owner_only(self):
        # GIVEN
        config = AmazonOrdersConfig(data={"output_dir": self.test_output_dir,
                                          "cookie_jar_path": self.test_cookie_jar_path})

        # WHEN
        config.save()

        # THEN
        self.assertEqual(0o600, os.stat(config.config_path).st_mode & 0o777)
        self.assertEqual(0o700, os.stat(conf.DEFAULT_CONFIG_DIR).st_mode & 0o777)

    def test_save_replaces_world_readable_config(self):
        # GIVEN
        config = AmazonOrdersConfig(data={"output_dir": self.test_output_dir,
                                          "cookie_jar_path": self.test_cookie_jar_path})
        os.makedirs(os.path.dirname(config.config_path), exist_ok=True)
        with open(config.config_path, "w") as f:
            f.write("{}")
        os.chmod(config.config_path, 0o644)

        # WHEN
        config.save()

        # THEN
        self.assertEqual(0o600, os.stat(config.config_path).st_mode & 0o777)
        with open(config.config_path, "r") as f:
            self.assertEqual(self.test_output_dir, yaml.safe_load(f)["output_dir"])
        self.assertEqual(["config.yml"], [name for name in os.listdir(os.path.dirname(config.config_path))
                                          if name.startswith((".config-", "config"))])

    @responses.activate
    def test_debug_pages_are_owner_only(self):
        # GIVEN
        amazon_session = AmazonSession("some-username@gmail.com", "some-password", debug=True,
                                       config=self.test_config)
        url = f"{self.test_config.constants.BASE_URL}/some/page"
        responses.add(responses.GET, url, body="<html><body>debug page</body></html>", status=200)

        # WHEN
        amazon_session.get(url)

        # THEN
        self.assertEqual(0o700, os.stat(self.test_output_dir).st_mode & 0o777)
        for name in os.listdir(self.test_output_dir):
            self.assertEqual(0o600, os.stat(os.path.join(self.test_output_dir, name)).st_mode & 0o777)

    def test_playwright_debug_snapshot_files_are_owner_only(self):
        # GIVEN
        form = PlaywrightAcicForm(self.test_config)
        page = MagicMock(content=MagicMock(return_value="<html/>"), screenshot=MagicMock(return_value=b"png"),
                         url="https://www.amazon.com/x")

        # WHEN
        form._save_debug_snapshot(page, self.test_output_dir, "snap")

        # THEN
        self.assertEqual(0o700, os.stat(self.test_output_dir).st_mode & 0o777)
        for name in ("snap.html", "snap.png"):
            self.assertEqual(0o600, os.stat(os.path.join(self.test_output_dir, name)).st_mode & 0o777)
        with open(os.path.join(self.test_output_dir, "snap.png"), "rb") as f:
            self.assertEqual(b"png", f.read())
