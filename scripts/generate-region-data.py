#!/usr/bin/env python

__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import importlib.util
import os
import re
import sys
import time
from collections import Counter
from typing import NamedTuple, Optional

import requests

ROOT_DIR = os.path.normpath(
    os.path.join(os.path.abspath(os.path.dirname(__file__)), ".."))
sys.path.insert(0, ROOT_DIR)

from amazonorders.conf import AmazonOrdersConfig  # noqa: E402
from amazonorders.constants import _REGION_CURRENCY_OVERRIDES  # noqa: E402

REGION_DATA_PATH = os.path.join(ROOT_DIR, "amazonorders", "region_data.py")
REPORT_PATH = os.path.join(ROOT_DIR, "build", "region-data-report.md")

COUNTRY_SELECTOR_URL = "https://www.amazon.com/customer-preferences/country?ie=UTF8"
COUNTRY_SELECTOR_SITE_REGEX = re.compile(r'<option value="https://www\.amazon\.([a-z.]+)/\?ref_=icp_country')
LOCALE_ID_REGEX = re.compile(r'"localeId":"([a-z]{2}_[A-Z]{2})"')
HTML_LANG_REGEX = re.compile(r'<html[^>]*\blang="([a-z]{2})-([a-z]{2})"', re.IGNORECASE)
SIGN_IN_HANDLE_REGEX = re.compile(r"/ap/(?:signin|register)\?openid\.return_to=[^\"']*?openid\.assoc_handle=(\w+)")
LANGUAGE_COOKIE_REGEX = re.compile(r"^(lc-[\w-]+)=([a-z]{2}_[A-Z]{2})")
CURRENCY_COOKIE_NAME = "i18n-prefs"
CURRENCY_COOKIE_REGEX = re.compile(rf"^{CURRENCY_COOKIE_NAME}=([A-Z]{{3}})")
LOCAL_CURRENCIES_REGEX = re.compile(r'"popularCurrenciesWithLocalCurrency"\s*:\s*\[(.*?)\]', re.DOTALL)
CURRENCY_CODE_REGEX = re.compile(r'"code"\s*:\s*"([A-Z]{3})"')
BESTSELLER_PRICE_REGEX = re.compile(r'p13n-sc-price[^"]*"[^>]*>([^<]+)<')
SINGLE_PRICE_REGEX = re.compile(r"^([^\d\s]*)\s*\d[\d.,]*\s*([^\d\s]*)$")
ROBOT_PAGE_MARKERS = ["/errors/validateCaptcha", "api-services-support@amazon.com"]

ENGLISH_ACCEPT_LANGUAGE = "en-US,en;q=0.9"
REQUEST_TIMEOUT_SECONDS = 30
FETCH_ATTEMPTS = 2
RETRY_DELAY_SECONDS = 30
DELAY_BETWEEN_REQUESTS_SECONDS = 2
MINIMUM_PRICES_FOR_CURRENCY = 5

REGION_SITE_FIELDS = [
    ("english_locale", "The English locale the site offers (e.g. ``en_GB``), or ``None`` if it offers no English."),
    ("language_cookie", "The cookie the site picks its page language from (e.g. ``lc-acbde``)."),
    ("assoc_handle", "The ``openid.assoc_handle`` the site's sign-in uses (e.g. ``deflex``)."),
    ("currency_symbol", "The currency symbol the site's prices are shown with (e.g. ``€``)."),
]

RegionSite = NamedTuple("RegionSite", [(field, Optional[str]) for field, _ in REGION_SITE_FIELDS])

REGION_DATA_TEMPLATE = '''# AUTO-GENERATED — DO NOT EDIT.
# Refreshed nightly from Amazon's own pages, signed out, via:
#   scripts/generate-region-data.py

__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

from typing import Dict, NamedTuple, Optional


class RegionSite(NamedTuple):
{fields}

#: Every Amazon site Amazon lists, and what each offers.
REGION_SITES: Dict[str, RegionSite] = {{
{entries}}}
'''

REGION_SITE_FIELD_TEMPLATE = '''    #: {doc}
    {field}: Optional[str]
'''

REGION_SITE_TEMPLATE = '''    "{tld}": RegionSite(
{values}    ),
'''


class SiteUnreadableError(Exception):
    def __init__(self, url, reason):
        super().__init__(f"{url} {reason}")
        self.url = url
        self.reason = reason


class SiteWithoutSignInError(SiteUnreadableError):
    def __init__(self, url):
        super().__init__(url, "has no sign-in")


def _request_headers(url):
    base_headers = AmazonOrdersConfig(data={"domain": url.split("/")[2]}).constants.BASE_HEADERS
    return {**base_headers, "Accept-Language": ENGLISH_ACCEPT_LANGUAGE}


def _fetch(url, cookies=None):
    try:
        response = requests.get(url, headers=_request_headers(url), cookies=cookies,
                                timeout=REQUEST_TIMEOUT_SECONDS)
    except requests.RequestException as e:
        raise SiteUnreadableError(url, f"failed: {e}") from e

    if response.status_code != 200:
        raise SiteUnreadableError(url, f"returned {response.status_code}")
    if any(marker in response.text for marker in ROBOT_PAGE_MARKERS):
        raise SiteUnreadableError(url, "returned a robot check page")

    return response


def _with_retry(read, url, *args):
    for attempt in range(1, FETCH_ATTEMPTS + 1):
        try:
            return read(url, *args)
        except SiteUnreadableError:
            if attempt == FETCH_ATTEMPTS:
                raise
            time.sleep(RETRY_DELAY_SECONDS)


def _read_listed_sites(url):
    sites = sorted(set(COUNTRY_SELECTOR_SITE_REGEX.findall(_fetch(url).text)))
    if not sites:
        raise SiteUnreadableError(url, "lists no sites")
    return sites


def _read_set_cookie(response, cookie_regex):
    for header in response.raw.headers.getlist("Set-Cookie"):
        match = cookie_regex.match(header)
        if match:
            return match.groups()
    return None


def _read_offered_locales(page):
    listed_locales = set(LOCALE_ID_REGEX.findall(page))
    if listed_locales:
        return listed_locales
    return {f"{language.lower()}_{country.upper()}" for language, country in HTML_LANG_REGEX.findall(page)[:1]}


def _read_local_currency(response):
    """
    A site that converts prices to the visitor's currency sets ``i18n-prefs`` to that currency (USD from a US IP),
    but lists its own currency first in its popular currencies. A site that doesn't convert lists none, and sets
    ``i18n-prefs`` to its own currency.
    """
    local_currencies = LOCAL_CURRENCIES_REGEX.search(response.text)
    listed_codes = CURRENCY_CODE_REGEX.findall(local_currencies.group(1)) if local_currencies else []
    if listed_codes:
        return listed_codes[0]
    currency_cookie = _read_set_cookie(response, CURRENCY_COOKIE_REGEX)
    return currency_cookie[0] if currency_cookie else None


def _read_preferences(url):
    response = _fetch(url)
    page = response.text

    assoc_handles = set(SIGN_IN_HANDLE_REGEX.findall(page))
    if not assoc_handles:
        raise SiteWithoutSignInError(url)
    if len(assoc_handles) != 1:
        raise SiteUnreadableError(url, f"shows {len(assoc_handles)} sign-in handles")

    language_cookie, cookie_locale = _read_set_cookie(response, LANGUAGE_COOKIE_REGEX) or (None, None)
    english_locales = sorted(locale for locale in _read_offered_locales(page) if locale.startswith("en_"))
    english_locale = cookie_locale if cookie_locale in english_locales else next(iter(english_locales), None)
    if english_locale and not language_cookie:
        raise SiteUnreadableError(url, "offers English but set no language cookie")

    return ({"english_locale": english_locale,
             "language_cookie": language_cookie,
             "assoc_handle": assoc_handles.pop()},
            _read_local_currency(response))


def _currency_request_cookies(preferences, local_currency):
    cookies = {CURRENCY_COOKIE_NAME: local_currency} if local_currency else {}
    if preferences["english_locale"]:
        cookies[preferences["language_cookie"]] = preferences["english_locale"]
    return cookies


def _read_currency_symbol(url, cookies):
    symbols = Counter()
    for price in BESTSELLER_PRICE_REGEX.findall(_fetch(url, cookies).text):
        single_price = SINGLE_PRICE_REGEX.match(price.replace("\xa0", " ").strip())
        if single_price:
            symbols[single_price.group(1) or single_price.group(2)] += 1

    if sum(symbols.values()) < MINIMUM_PRICES_FOR_CURRENCY:
        raise SiteUnreadableError(url, f"shows {sum(symbols.values())} prices")
    if len(symbols) != 1:
        raise SiteUnreadableError(url, f"shows prices in more than one currency ({dict(symbols)})")

    return next(iter(symbols))


def _load_region_data_module():
    spec = importlib.util.spec_from_file_location("region_data", REGION_DATA_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _as_region_site(site):
    return RegionSite(**{field: getattr(site, field, None) for field in RegionSite._fields})


def _render_region_data(region_sites):
    fields = "".join(REGION_SITE_FIELD_TEMPLATE.format(field=field, doc=doc) for field, doc in REGION_SITE_FIELDS)
    entries = "".join(REGION_SITE_TEMPLATE.format(tld=tld, values="".join(f"        {field}={value!r},\n"
                                                                          for field, value in site._asdict().items()))
                      for tld, site in sorted(region_sites.items()))
    return REGION_DATA_TEMPLATE.format(fields=fields, entries=entries)


def _describe_changes(existing_sites, region_sites):
    changes = []
    for tld in sorted(set(existing_sites) | set(region_sites)):
        before, after = existing_sites.get(tld), region_sites.get(tld)
        if before == after:
            continue
        if before is None:
            changes.append(f"- Added amazon.{tld}: {_describe_site(after)}")
        elif after is None:
            changes.append(f"- Removed amazon.{tld}, which Amazon no longer lists")
        else:
            changed_fields = [f"{field} {getattr(before, field)!r} → {getattr(after, field)!r}"
                              for field in after._fields if getattr(before, field) != getattr(after, field)]
            changes.append(f"- Changed amazon.{tld}: {', '.join(changed_fields)}")
    return changes


def _describe_site(site):
    return ", ".join(f"{field} {value!r}" for field, value in site._asdict().items())


def _describe_follow_ups(region_sites):
    follow_ups = []
    for tld, site in sorted(region_sites.items()):
        override = _REGION_CURRENCY_OVERRIDES.get(tld)
        if site.english_locale and not site.currency_symbol and not override:
            follow_ups.append(f"- [ ] amazon.{tld}: verify the currency symbol its pages show, for "
                              f"`_REGION_CURRENCY_OVERRIDES`")
        elif override and override == site.currency_symbol:
            follow_ups.append(f"- [ ] amazon.{tld}: its `_REGION_CURRENCY_OVERRIDES` entry now matches Amazon's "
                              f"pages, so it can be removed")
        elif override and site.currency_symbol:
            follow_ups.append(f"- [ ] amazon.{tld}: its `_REGION_CURRENCY_OVERRIDES` entry {override!r} differs "
                              f"from its pages' {site.currency_symbol!r}; check which is right")
    return follow_ups


def _build_report(changes, unreadable_sites, follow_ups):
    sections = ["## Changes", *(changes or ["- None"])]
    if unreadable_sites:
        sections += ["", "## Kept unchanged (couldn't be read)", *unreadable_sites]
    if follow_ups:
        sections += ["", "## Follow-ups", *follow_ups]
    return "\n".join(sections) + "\n"


def _read_site(tld, existing_site, unreadable_sites):
    base_url = f"https://www.amazon.{tld}"
    try:
        preferences, local_currency = _with_retry(_read_preferences, f"{base_url}/customer-preferences/edit?ie=UTF8")
    except SiteWithoutSignInError as e:
        if not existing_site:
            return None
        unreadable_sites.append(f"- amazon.{tld}: {e.reason}")
        return _as_region_site(existing_site)
    except SiteUnreadableError as e:
        unreadable_sites.append(f"- amazon.{tld}: {e.reason}")
        return _as_region_site(existing_site) if existing_site else None

    time.sleep(DELAY_BETWEEN_REQUESTS_SECONDS)
    try:
        currency_symbol = _with_retry(_read_currency_symbol, f"{base_url}/gp/bestsellers",
                                      _currency_request_cookies(preferences, local_currency))
    except SiteUnreadableError as e:
        unreadable_sites.append(f"- amazon.{tld}'s currency symbol: {e.reason}")
        currency_symbol = getattr(existing_site, "currency_symbol", None)

    return RegionSite(**preferences, currency_symbol=currency_symbol)


def generate_region_data(args):
    """
    The purpose of this script is to generate ``amazonorders/region_data.py`` from Amazon's own pages, signed out:
    the sites Amazon lists in its country selector and, for each, the English locale it offers, the cookie that
    selects it, and its sign-in handle (from its language preferences page), and the currency symbol its prices are
    shown with (from its bestsellers page, in its own currency rather than one converted for the visitor).

    Anything that can't be read (a robot page, an error, or a page missing what's needed) keeps its existing value, so
    a blocked request never removes a site. A site is only removed when Amazon stops listing it. A listed site with no
    sign-in at all (e.g. one that's app-only) isn't added, since ``amazon-orders`` couldn't sign in to it. A report of the
    changes is written to ``build/region-data-report.md``.

    This script should be invoked using ``make generate-region-data``.
    """
    existing_sites = {tld: _as_region_site(site) for tld, site in _load_region_data_module().REGION_SITES.items()}

    try:
        listed_sites = _with_retry(_read_listed_sites, COUNTRY_SELECTOR_URL)
    except SiteUnreadableError as e:
        print(f"Amazon's site list couldn't be read, so nothing was changed: {e}")

        sys.exit(1)

    region_sites = {}
    unreadable_sites = []
    for tld in listed_sites:
        time.sleep(DELAY_BETWEEN_REQUESTS_SECONDS)
        region_site = _read_site(tld, existing_sites.get(tld), unreadable_sites)
        if region_site:
            region_sites[tld] = region_site

    with open(REGION_DATA_PATH, "w", encoding="utf-8") as region_data_file:
        region_data_file.write(_render_region_data(region_sites))

    report = _build_report(_describe_changes(existing_sites, region_sites), unreadable_sites,
                           _describe_follow_ups(region_sites))
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as report_file:
        report_file.write(report)

    print(report)


if __name__ == "__main__":
    generate_region_data(sys.argv)
