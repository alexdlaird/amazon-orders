__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import os
import re
import tempfile
import time
import warnings

from parameterized import parameterized
from requests import RequestException

from amazonorders.conf import AmazonOrdersConfig
from amazonorders.region_data import REGION_SITES
from amazonorders.session import AmazonSession
from tests.testcase import TestCase

HTML_LANG_REGEX = re.compile(r'<html[^>]*\blang="([^"]+)"')
NON_ENGLISH_ACCEPT_LANGUAGE = "de-DE,de;q=0.9"
ROBOT_PAGE_MARKERS = ["/errors/validateCaptcha", "api-services-support@amazon.com"]
REQUEST_TIMEOUT_SECONDS = 30
FETCH_ATTEMPTS = 2
RETRY_DELAY_SECONDS = 30


def as_language_tag(locale):
    return locale.replace("_", "-").lower()


class SiteCheckInconclusiveError(Exception):
    def __init__(self, url, reason):
        super().__init__(f"{url} {reason}")
        self.url = url
        self.reason = reason


class TestIntegrationSites(TestCase):
    """
    Signed-out checks that ``amazon-orders`` gets English pages from every site its region data says offers them, so
    a best-effort site's drift is caught nightly. The region data itself is generated from Amazon's own pages by
    ``make generate-region-data``; these check that requesting pages the way ``amazon-orders`` does still works. Each
    site's page is requested with a non-English ``Accept-Language``, so English pages prove its language cookie works.

    A blocked or failed request (a robot page, a 5xx, or a timeout) is retried once, then skipped as inconclusive, so
    only a definite mismatch fails.
    """

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def given_signed_out_session(self, tld):
        site_dir = os.path.join(self.temp_dir.name, tld)
        config = AmazonOrdersConfig(config_path=os.path.join(site_dir, "config.yml"),
                                    data={"domain": f"amazon.{tld}",
                                          "cookie_jar_path": os.path.join(site_dir, "cookies.json"),
                                          "output_dir": os.path.join(site_dir, "output"),
                                          "request_timeout": REQUEST_TIMEOUT_SECONDS})
        return AmazonSession(config=config)

    def get_preferences_page(self, amazon_session):
        base_url = amazon_session.config.constants.BASE_URL
        return self._fetch_with_retry(amazon_session, f"{base_url}/customer-preferences/edit?ie=UTF8",
                                      {"Accept-Language": NON_ENGLISH_ACCEPT_LANGUAGE})

    def _fetch_with_retry(self, amazon_session, url, headers):
        for attempt in range(1, FETCH_ATTEMPTS + 1):
            try:
                return self._fetch(amazon_session, url, headers)
            except SiteCheckInconclusiveError as e:
                if attempt == FETCH_ATTEMPTS:
                    message = f"Check inconclusive: {e}"
                    warnings.warn(message)
                    self.skipTest(message)
                time.sleep(RETRY_DELAY_SECONDS)

    def _fetch(self, amazon_session, url, headers):
        try:
            response = amazon_session.get(url, headers=headers).response
        except RequestException as e:
            raise SiteCheckInconclusiveError(url, f"failed: {e}") from e

        if response.status_code >= 500:
            raise SiteCheckInconclusiveError(url, f"returned {response.status_code}")
        if any(marker in response.text for marker in ROBOT_PAGE_MARKERS):
            raise SiteCheckInconclusiveError(url, "returned a robot check page")
        response.raise_for_status()

        return response.text

    @parameterized.expand(sorted(tld for tld, site in REGION_SITES.items() if site.english_locale))
    def test_language_cookie_selects_english(self, tld):
        # GIVEN
        amazon_session = self.given_signed_out_session(tld)
        cookie_name, requested_locale = next(iter(amazon_session.config.constants.REQUEST_COOKIES.items()))

        # WHEN
        page = self.get_preferences_page(amazon_session)

        # THEN
        page_languages = HTML_LANG_REGEX.findall(page)
        self.assertTrue(page_languages, f"amazon.{tld}'s preferences page no longer sets <html lang>")
        self.assertEqual(as_language_tag(requested_locale), page_languages[0].lower(),
                         f"amazon.{tld}'s {cookie_name} cookie no longer selects {requested_locale} pages")
