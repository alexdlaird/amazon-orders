# AUTO-GENERATED — DO NOT EDIT.
# Refreshed nightly from Amazon's own pages, signed out, via:
#   scripts/generate-region-data.py

__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

from typing import Dict, NamedTuple, Optional


class RegionSite(NamedTuple):
    #: The English locale the site offers (e.g. ``en_GB``), or ``None`` if it offers no English.
    english_locale: Optional[str]
    #: The cookie the site picks its page language from (e.g. ``lc-acbde``).
    language_cookie: Optional[str]
    #: The ``openid.assoc_handle`` the site's sign-in uses (e.g. ``deflex``).
    assoc_handle: Optional[str]
    #: The currency symbol the site's prices are shown with (e.g. ``€``).
    currency_symbol: Optional[str]


#: Every Amazon site Amazon lists, and what each offers.
REGION_SITES: Dict[str, RegionSite] = {
    "ae": RegionSite(
        english_locale='en_AE',
        language_cookie='lc-acbae',
        assoc_handle='aeflex',
        currency_symbol='AED',
    ),
    "ca": RegionSite(
        english_locale='en_CA',
        language_cookie='lc-acbca',
        assoc_handle='caflex',
        currency_symbol='$',
    ),
    "co.jp": RegionSite(
        english_locale='en_US',
        language_cookie='lc-acbjp',
        assoc_handle='jpflex',
        currency_symbol='¥',
    ),
    "co.uk": RegionSite(
        english_locale='en_GB',
        language_cookie='lc-acbuk',
        assoc_handle='gbflex',
        currency_symbol='£',
    ),
    "co.za": RegionSite(
        english_locale='en_ZA',
        language_cookie='lc-acbza',
        assoc_handle='zaflex',
        currency_symbol='R',
    ),
    "com": RegionSite(
        english_locale='en_US',
        language_cookie='lc-main',
        assoc_handle='usflex',
        currency_symbol='$',
    ),
    "com.au": RegionSite(
        english_locale='en_AU',
        language_cookie='lc-acbau',
        assoc_handle='auflex',
        currency_symbol='$',
    ),
    "com.be": RegionSite(
        english_locale='en_GB',
        language_cookie='lc-acbbe',
        assoc_handle='beflex',
        currency_symbol='€',
    ),
    "com.br": RegionSite(
        english_locale=None,
        language_cookie='lc-acbbr',
        assoc_handle='brflex',
        currency_symbol='R$',
    ),
    "com.mx": RegionSite(
        english_locale=None,
        language_cookie='lc-acbmx',
        assoc_handle='mxflex',
        currency_symbol='$',
    ),
    "com.tr": RegionSite(
        english_locale=None,
        language_cookie='lc-acbtr',
        assoc_handle='trflex',
        currency_symbol='TL',
    ),
    "de": RegionSite(
        english_locale='en_GB',
        language_cookie='lc-acbde',
        assoc_handle='deflex',
        currency_symbol='€',
    ),
    "eg": RegionSite(
        english_locale='en_AE',
        language_cookie='lc-acbeg',
        assoc_handle='egflex',
        currency_symbol='EGP',
    ),
    "es": RegionSite(
        english_locale='en_GB',
        language_cookie='lc-acbes',
        assoc_handle='esflex',
        currency_symbol='€',
    ),
    "fr": RegionSite(
        english_locale='en_GB',
        language_cookie='lc-acbfr',
        assoc_handle='frflex',
        currency_symbol='€',
    ),
    "ie": RegionSite(
        english_locale='en_IE',
        language_cookie='lc-acbie',
        assoc_handle='ieflex',
        currency_symbol='€',
    ),
    "in": RegionSite(
        english_locale='en_IN',
        language_cookie='lc-acbin',
        assoc_handle='inflex',
        currency_symbol='₹',
    ),
    "it": RegionSite(
        english_locale='en_GB',
        language_cookie='lc-acbit',
        assoc_handle='itflex',
        currency_symbol='€',
    ),
    "nl": RegionSite(
        english_locale='en_GB',
        language_cookie='lc-acbnl',
        assoc_handle='nlflex',
        currency_symbol='€',
    ),
    "pl": RegionSite(
        english_locale=None,
        language_cookie='lc-acbpl',
        assoc_handle='plflex',
        currency_symbol='zł',
    ),
    "sa": RegionSite(
        english_locale='en_AE',
        language_cookie='lc-acbsa',
        assoc_handle='saflex',
        currency_symbol='SAR',
    ),
    "se": RegionSite(
        english_locale='en_GB',
        language_cookie='lc-acbse',
        assoc_handle='seflex',
        currency_symbol='kr',
    ),
    "sg": RegionSite(
        english_locale='en_SG',
        language_cookie='lc-acbsg',
        assoc_handle='sgflex',
        currency_symbol='S$',
    ),
}
