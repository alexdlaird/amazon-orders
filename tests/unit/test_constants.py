__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import os
from unittest.mock import patch

from amazonorders.conf import AmazonOrdersConfig
from amazonorders.constants import Constants, _BROWSER_PRESETS
from amazonorders.region_data import REGION_SITES
from tests.unittestcase import UnitTestCase


class TestConstants(UnitTestCase):
    _FIREFOX_UA = _BROWSER_PRESETS["firefox"]["User-Agent"]
    _CHROMIUM_UA = Constants.BASE_HEADERS["User-Agent"]

    def test_default_browser_is_chromium(self):
        # GIVEN / WHEN
        constants = Constants()

        # THEN
        self.assertEqual(self._CHROMIUM_UA, constants.BASE_HEADERS["User-Agent"])
        self.assertIn("Sec-Ch-Ua", constants.BASE_HEADERS)

    def test_firefox_preset_via_config_data(self):
        # GIVEN / WHEN
        config = AmazonOrdersConfig(data={"browser": "firefox"})

        # THEN
        self.assertEqual(self._FIREFOX_UA, config.constants.BASE_HEADERS["User-Agent"])
        self.assertNotIn("Sec-Ch-Ua", config.constants.BASE_HEADERS)

    def test_chromium_preset_via_config_data(self):
        # GIVEN / WHEN
        config = AmazonOrdersConfig(data={"browser": "chromium"})

        # THEN
        self.assertEqual(self._CHROMIUM_UA, config.constants.BASE_HEADERS["User-Agent"])
        self.assertIn("Sec-Ch-Ua", config.constants.BASE_HEADERS)
        self.assertIn("Sec-Ch-Ua-Mobile", config.constants.BASE_HEADERS)
        self.assertIn("Sec-Ch-Ua-Platform", config.constants.BASE_HEADERS)

    def test_webkit_preset_via_config_data(self):
        # GIVEN / WHEN
        config = AmazonOrdersConfig(data={"browser": "webkit"})

        # THEN
        self.assertEqual(_BROWSER_PRESETS["webkit"]["User-Agent"], config.constants.BASE_HEADERS["User-Agent"])
        self.assertIn("Safari/", config.constants.BASE_HEADERS["User-Agent"])
        self.assertNotIn("Chrome/", config.constants.BASE_HEADERS["User-Agent"])
        self.assertNotIn("Sec-Ch-Ua", config.constants.BASE_HEADERS)
        self.assertNotIn("Sec-Fetch-User", config.constants.BASE_HEADERS)

    def test_chromium_preset_accept_header(self):
        # GIVEN / WHEN
        config = AmazonOrdersConfig(data={"browser": "chromium"})

        # THEN
        self.assertIn("image/avif", config.constants.BASE_HEADERS["Accept"])

    def test_firefox_preset_via_env_var(self):
        # GIVEN / WHEN
        with patch.dict(os.environ, {"AMAZON_BROWSER": "firefox"}):
            constants = Constants()

        # THEN
        self.assertEqual(self._FIREFOX_UA, constants.BASE_HEADERS["User-Agent"])

    def test_chromium_preset_via_env_var(self):
        # GIVEN / WHEN
        with patch.dict(os.environ, {"AMAZON_BROWSER": "chromium"}):
            constants = Constants()

        # THEN
        self.assertEqual(self._CHROMIUM_UA, constants.BASE_HEADERS["User-Agent"])
        self.assertIn("Sec-Ch-Ua", constants.BASE_HEADERS)

    def test_env_var_takes_precedence_over_config_data(self):
        # GIVEN / WHEN
        with patch.dict(os.environ, {"AMAZON_BROWSER": "firefox"}):
            config = AmazonOrdersConfig(data={"browser": "chromium"})

        # THEN
        self.assertEqual(self._FIREFOX_UA, config.constants.BASE_HEADERS["User-Agent"])

    def test_installed_chromium_browser_keeps_chromium_headers(self):
        # GIVEN / WHEN
        config = AmazonOrdersConfig(data={"browser": "chrome"})

        # THEN
        self.assertEqual(self._CHROMIUM_UA, config.constants.BASE_HEADERS["User-Agent"])
        self.assertIn("Sec-Ch-Ua", config.constants.BASE_HEADERS)

    def test_domain_and_chromium_preset_combined(self):
        # GIVEN / WHEN
        config = AmazonOrdersConfig(data={
            "browser": "chromium",
            "domain": "amazon.co.uk",
        })

        # THEN — chromium UA + UK Accept-Language from region override
        self.assertEqual(self._CHROMIUM_UA, config.constants.BASE_HEADERS["User-Agent"])
        self.assertIn("en-GB", config.constants.BASE_HEADERS["Accept-Language"])

    def test_domain_accept_language_overrides_browser_default(self):
        # GIVEN / WHEN — default (chromium) Accept-Language is en-US,en;q=0.9
        config_default = AmazonOrdersConfig(data={"domain": "amazon.co.uk"})
        config_ff = AmazonOrdersConfig(data={
            "browser": "firefox",
            "domain": "amazon.co.uk",
        })

        # THEN — both get the TLD-specific Accept-Language regardless of browser
        self.assertIn("en-GB", config_default.constants.BASE_HEADERS["Accept-Language"])
        self.assertIn("en-GB", config_ff.constants.BASE_HEADERS["Accept-Language"])

    def test_domain_co_jp_sets_yen_currency_symbol(self):
        # GIVEN / WHEN
        config = AmazonOrdersConfig(data={"domain": "amazon.co.jp"})

        # THEN
        self.assertEqual("https://www.amazon.co.jp", config.constants.BASE_URL)
        self.assertEqual("¥", config.constants.CURRENCY_SYMBOL)

    def test_format_currency_yen_without_decimals(self):
        # GIVEN
        constants = AmazonOrdersConfig(data={"domain": "amazon.co.jp"}).constants

        # WHEN / THEN
        self.assertEqual("¥1,980", constants.format_currency(1980))
        self.assertEqual("¥1,234,568", constants.format_currency(1234567.5))
        self.assertEqual("-¥1,980", constants.format_currency(-1980))
        self.assertEqual("¥0", constants.format_currency(-0.4))

    def test_format_currency_keeps_decimals(self):
        # GIVEN
        constants = AmazonOrdersConfig(data={"domain": "amazon.com"}).constants

        # WHEN / THEN
        self.assertEqual("$1,980.00", constants.format_currency(1980))
        self.assertEqual("-$1.99", constants.format_currency(-1.99))

    def test_domain_sets_region_assoc_handle(self):
        # GIVEN
        expected_assoc_handles = {
            "amazon.ae": "aeflex",
            "amazon.ca": "caflex",
            "amazon.co.jp": "jpflex",
            "amazon.co.uk": "gbflex",
            "amazon.co.za": "zaflex",
            "amazon.com.au": "auflex",
            "amazon.com.be": "beflex",
            "amazon.de": "deflex",
            "amazon.eg": "egflex",
            "amazon.es": "esflex",
            "amazon.fr": "frflex",
            "amazon.ie": "ieflex",
            "amazon.in": "inflex",
            "amazon.it": "itflex",
            "amazon.nl": "nlflex",
            "amazon.sa": "saflex",
            "amazon.se": "seflex",
            "amazon.sg": "sgflex",
        }

        for domain, expected_assoc_handle in expected_assoc_handles.items():
            with self.subTest(domain=domain):
                # WHEN
                config = AmazonOrdersConfig(data={"domain": domain})

                # THEN
                self.assertEqual(expected_assoc_handle,
                                 config.constants.SIGN_IN_QUERY_PARAMS["openid.assoc_handle"])
                self.assertIn(f"openid.assoc_handle={expected_assoc_handle}",
                              config.constants.BASE_HEADERS["Referer"])

    def test_domain_sets_region_authenticated_cookie(self):
        # GIVEN
        expected_cookies = {
            "amazon.ca": "x-acbca",
            "amazon.co.jp": "x-acbjp",
            "amazon.co.uk": "x-acbuk",
            "amazon.com.au": "x-acbau",
            "amazon.de": "x-acbde",
            "amazon.in": "x-acbin",
            "amazon.it": "x-acbit",
        }

        for domain, expected_cookie in expected_cookies.items():
            with self.subTest(domain=domain):
                # WHEN
                config = AmazonOrdersConfig(data={"domain": domain})

                # THEN
                self.assertEqual([expected_cookie], config.constants.COOKIES_SET_WHEN_AUTHENTICATED)

    def test_domain_com_keeps_default_sign_in_and_session_values(self):
        # GIVEN / WHEN
        config = AmazonOrdersConfig(data={"domain": "amazon.com"})

        # THEN
        self.assertEqual(Constants.SIGN_IN_QUERY_PARAMS, config.constants.SIGN_IN_QUERY_PARAMS)
        self.assertEqual(Constants.BASE_HEADERS["Referer"], config.constants.BASE_HEADERS["Referer"])
        self.assertEqual(["x-main"], config.constants.COOKIES_SET_WHEN_AUTHENTICATED)

    def test_domain_unknown_tld_keeps_default_sign_in_and_session_values(self):
        # GIVEN / WHEN
        config = AmazonOrdersConfig(data={"domain": "amazon.example"})

        # THEN
        self.assertEqual("usflex", config.constants.SIGN_IN_QUERY_PARAMS["openid.assoc_handle"])
        self.assertEqual(["x-main"], config.constants.COOKIES_SET_WHEN_AUTHENTICATED)
        self.assertEqual({}, config.constants.REQUEST_COOKIES)

    def test_domain_sets_region_language_cookie(self):
        # GIVEN
        expected_cookies = {
            "amazon.ae": {"lc-acbae": "en_AE"},
            "amazon.ca": {"lc-acbca": "en_CA"},
            "amazon.co.jp": {"lc-acbjp": "en_US"},
            "amazon.co.uk": {"lc-acbuk": "en_GB"},
            "amazon.co.za": {"lc-acbza": "en_ZA"},
            "amazon.com": {"lc-main": "en_US"},
            "amazon.com.au": {"lc-acbau": "en_AU"},
            "amazon.com.be": {"lc-acbbe": "en_GB"},
            "amazon.de": {"lc-acbde": "en_GB"},
            "amazon.eg": {"lc-acbeg": "en_AE"},
            "amazon.es": {"lc-acbes": "en_GB"},
            "amazon.fr": {"lc-acbfr": "en_GB"},
            "amazon.ie": {"lc-acbie": "en_IE"},
            "amazon.in": {"lc-acbin": "en_IN"},
            "amazon.it": {"lc-acbit": "en_GB"},
            "amazon.nl": {"lc-acbnl": "en_GB"},
            "amazon.sa": {"lc-acbsa": "en_AE"},
            "amazon.se": {"lc-acbse": "en_GB"},
            "amazon.sg": {"lc-acbsg": "en_SG"},
        }

        for domain, expected_cookie in expected_cookies.items():
            with self.subTest(domain=domain):
                # WHEN
                config = AmazonOrdersConfig(data={"domain": domain})

                # THEN
                self.assertEqual(expected_cookie, config.constants.REQUEST_COOKIES)

    def test_no_domain_sets_com_language_cookie(self):
        # GIVEN / WHEN
        constants = Constants()

        # THEN
        self.assertEqual({"lc-main": "en_US"}, constants.REQUEST_COOKIES)
        self.assertEqual({}, Constants.REQUEST_COOKIES)

    def test_language_cookie_and_accept_language_request_the_same_locale(self):
        for tld, site in REGION_SITES.items():
            if not site.english_locale:
                continue
            with self.subTest(tld=tld):
                # GIVEN / WHEN
                config = AmazonOrdersConfig(data={"domain": f"amazon.{tld}"})

                # THEN
                self.assertEqual(site.english_locale.replace("_", "-"),
                                 config.constants.BASE_HEADERS["Accept-Language"].split(",")[0],
                                 f"amazon.{tld}'s Accept-Language asks for a different locale than its cookie")

    def test_domain_does_not_override_constants_class_request_cookies(self):
        # GIVEN / WHEN
        config = AmazonOrdersConfig(data={
            "constants_class": "tests.unit.test_constants.RequestCookiesOverrideConstants",
            "domain": "amazon.fr",
        })

        # THEN
        self.assertEqual({"lc-acbfr": "fr_FR"}, config.constants.REQUEST_COOKIES)

    def test_domain_does_not_override_constants_class_sign_in_and_session_values(self):
        # GIVEN / WHEN
        config = AmazonOrdersConfig(data={
            "constants_class": "tests.unit.test_constants.RegionOverrideConstants",
            "domain": "amazon.co.uk",
        })

        # THEN
        self.assertEqual("customflex", config.constants.SIGN_IN_QUERY_PARAMS["openid.assoc_handle"])
        self.assertIn("openid.assoc_handle=customflex", config.constants.BASE_HEADERS["Referer"])
        self.assertEqual(["x-custom"], config.constants.COOKIES_SET_WHEN_AUTHENTICATED)
        self.assertEqual("https://www.amazon.co.uk/?ref_=nav_custrec_signin",
                         config.constants.SIGN_IN_QUERY_PARAMS["openid.return_to"])

    def test_parse_order_number_matches_by_shape_whatever_the_label(self):
        # GIVEN
        constants = Constants()

        # WHEN / THEN
        self.assertEqual("112-1234567-1234567", constants.parse_order_number("Order #112-1234567-1234567"))
        self.assertEqual("112-1234567-1234567", constants.parse_order_number("Order# 112-1234567-1234567"))
        self.assertEqual("302-1234567-1234567", constants.parse_order_number("Bestellnr. 302-1234567-1234567"))
        self.assertEqual("D01-1234567-1234567", constants.parse_order_number("Order #D01-1234567-1234567"))
        self.assertEqual("1234567890123456789", constants.parse_order_number("Refund: Order #1234567890123456789"))
        self.assertEqual("4000-123456-1234567", constants.parse_order_number("4000-123456-1234567"))

    def test_parse_order_number_no_order_number(self):
        # GIVEN
        constants = Constants()

        # WHEN / THEN
        self.assertIsNone(constants.parse_order_number("AMZN Mktp US"))
        self.assertIsNone(constants.parse_order_number("X112-1234567-1234567"))
        self.assertIsNone(constants.parse_order_number("12345678901234567890"))
        self.assertIsNone(constants.parse_order_number("4000-1234567-1234567"))

    def test_domain_sets_region_currency_symbol(self):
        # GIVEN
        expected_symbols = {
            "amazon.ae": "AED", "amazon.ca": "$", "amazon.co.za": "R", "amazon.com.au": "$", "amazon.com.be": "€",
            "amazon.com.br": "R$", "amazon.com.mx": "$", "amazon.com.tr": "TL",
            "amazon.de": "€", "amazon.eg": "EGP", "amazon.es": "€", "amazon.fr": "€", "amazon.ie": "€",
            "amazon.it": "€", "amazon.nl": "€", "amazon.pl": "zł", "amazon.sa": "SAR", "amazon.se": "kr",
        }

        for domain, expected_symbol in expected_symbols.items():
            with self.subTest(domain=domain):
                # WHEN
                config = AmazonOrdersConfig(data={"domain": domain})

                # THEN
                self.assertEqual(expected_symbol, config.constants.CURRENCY_SYMBOL)


class RegionOverrideConstants(Constants):
    SIGN_IN_QUERY_PARAMS = dict(Constants.SIGN_IN_QUERY_PARAMS, **{"openid.assoc_handle": "customflex"})
    COOKIES_SET_WHEN_AUTHENTICATED = ["x-custom"]


class RequestCookiesOverrideConstants(Constants):
    REQUEST_COOKIES = {"lc-acbfr": "fr_FR"}
