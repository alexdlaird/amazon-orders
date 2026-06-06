__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import os
from unittest.mock import patch

from amazonorders.conf import AmazonOrdersConfig
from amazonorders.constants import Constants, _BROWSER_PRESETS
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

    def test_config_data_takes_precedence_over_env_var(self):
        # GIVEN / WHEN — env says chromium, config says firefox
        with patch.dict(os.environ, {"AMAZON_BROWSER": "chromium"}):
            config = AmazonOrdersConfig(data={"browser": "firefox"})

        # THEN — config wins
        self.assertEqual(self._FIREFOX_UA, config.constants.BASE_HEADERS["User-Agent"])

    def test_unknown_browser_logs_warning_and_keeps_headers(self):
        # GIVEN / WHEN
        with self.assertLogs("amazonorders.constants", level="WARNING") as logs:
            config2 = AmazonOrdersConfig(data={"browser": "safari"})

        # THEN — UA unchanged (falls back to class-level chromium default)
        self.assertTrue(any("safari" in m for m in logs.output))
        self.assertEqual(self._CHROMIUM_UA, config2.constants.BASE_HEADERS["User-Agent"])

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
