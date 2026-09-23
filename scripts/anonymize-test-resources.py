#!/usr/bin/env python

__copyright__ = "Copyright (c) 2024-2026 Alex Laird"
__license__ = "MIT"

import argparse
import datetime
import hashlib
import hmac
import json
import os
import re
import sys
from decimal import Decimal, ROUND_HALF_UP
from html import escape as html_escape
from typing import Dict, List, Set
from urllib.parse import quote, parse_qsl, urlencode, urlsplit, urlunsplit

from bs4 import BeautifulSoup, Comment, Tag

"""
Anonymize raw Amazon pages (saved with ``debug`` mode or fetched manually) so they can be committed as
test resources.

Usage:

    python scripts/anonymize-test-resources.py --rules ~/private/rules.json \\
        --output-dir tests/resources/de raw/history-2026-p1.html:orders/order-history-2026-0.html ...

``--rules`` points to a private JSON file that must never be committed:

    {
        "id_salt": "some random string, keeps fake order numbers stable between runs",
        "replace": [
            {"find": "Jane Doe", "replace": "Max Mustermann"},
            {"find": "Secret Street 1", "replace": "Musterstraße 1"}
        ],
        "sensitive": ["any other string that must not survive, e.g. a phone number"],
        "date_shift_days": -10,
        "amount_factor": 1.1
    }

``date_shift_days`` moves every date and ``amount_factor`` scales every amount, so the fixtures do not reveal
when and for how much things were bought. Keep both private, otherwise the real values can be recalculated.

A page may be followed by ``:cards=0,3,5`` to keep only those order cards of an order history page.

Recipient names and address lines found in the pages are added to the replacement rules automatically. After
writing, every output file is scanned for all sensitive values that were seen, and the script exits non-zero if
any survived. Always review the output manually before committing.
"""

FAKE_NAME = "Max Mustermann"
FAKE_ADDRESS_LINES = ["Musterstraße 1", "Hinterhaus", "10115 Berlin"]
FAKE_EMAIL = "kunde@example.com"
FAKE_CARD_DIGITS = "1234"
FAKE_CUSTOMER_ID = "A1B2C3D4E5F6G7"
FAKE_SELLER = "Beispielhändler GmbH"
FAKE_IMAGE_ID = "01TESTIMG0L"
FAKE_VIDEO_ID = "amzn1.dv.gti.00000000-0000-0000-0000-000000000000"
# Marketplace IDs are public and identify the store, not the customer (amazon.de, amazon.com)
PUBLIC_IDS = {"A1PA6795UKMFR9", "ATVPDKIKX0DER"}

# Product links outside of orders are ads, e.g. for the Amazon Visa card, and must keep their text
ORDER_ITEM_CONTAINERS = ["div.order-card", "[data-component='purchasedItems']"]
PRODUCT_TITLE_SELECTORS = ["[data-component='itemTitle']", ".yohtmlc-product-title"] + [
    f"{container} {link}" for container in ORDER_ITEM_CONTAINERS
    for link in ("a[href*='/dp/']", "a[href*='/gp/product/']", "a[href*='/gp/video/detail/']")]
PRODUCT_IMAGE_CONTAINER_SELECTORS = ["[data-component='itemImage']", ".product-image"] + ORDER_ITEM_CONTAINERS
PRODUCT_DETAIL_SELECTORS = ["[data-component='purchasedVariationDetails']", "[data-component='customizedItemDetails']",
                            "[data-component='substitutionDetails']", "[data-component='giftMessage']"]
ASIN_REGEX = re.compile(r"(?:/dp/|/gp/product/|/gp/video/detail/|amzn1\.asin\.|asins?[\"'=:%3Dd]+\s*\"?)"
                        r"([A-Z0-9]{10})\b")
ASIN_LIST_REGEX = re.compile(r"asins=([A-Z0-9]{10}(?:(?:%2C|,)[A-Z0-9]{10})*)")
SELLER_NAME_REGEX = re.compile(r"(?:Verkauf durch|Verkauft von|Sold by)\s*:?\s*(?:<[^>]+>\s*)*([^<\n]+?)\s*<")
SELLER_ID_REGEX = re.compile(r"(?:seller(?:ID|Id|id)?|recipientId|merchantId|merchant)(?:[\"'=:]|%3D|%22)+"
                             r"([A-Z0-9]{10,16})\b")
PRODUCT_IMAGE_REGEX = re.compile(r"(images/I/)[A-Za-z0-9+%-]+")
VIDEO_ID_REGEX = re.compile(r"amzn1\.dv\.gti\.[0-9a-f-]{36}")
STATEMENT_DESCRIPTOR_REGEX = re.compile(r'"statementDescriptor"\s*:\s*"([^"]*)"')
GERMAN_MONTHS = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober",
                 "November", "Dezember"]
GERMAN_DATE_REGEX = re.compile(r"\b(\d{1,2})\.(\s|\xa0|&nbsp;)(" + "|".join(GERMAN_MONTHS) + r")\b"
                               r"(?:(\s|\xa0|&nbsp;)(\d{4})\b)?")
GERMAN_AMOUNT_REGEX = re.compile(r"(?<![\d.,])(\d{1,3}(?:\.\d{3})+|\d+),(\d{2})(\s|\xa0|&nbsp;)?€")
US_EURO_AMOUNT_REGEX = re.compile(r"€(\d{1,3}(?:,\d{3})+|\d+)\.(\d{2})(?![\d])")
ORDER_ID_REGEX = re.compile(r"\b(\d{3}|D\d{2})-(\d{7})-(\d{7})\b")
EMAIL_REGEX = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
CARD_DIGITS_REGEXES = [
    re.compile(r"((?:•|\*|&bull;|\\u2022){2,}\s*)(\d{2,4})\b"),
    re.compile(r"(\"lastDigits\"\s*:\s*\")(\d{2,4})(\")"),
    re.compile(r"((?:endet auf|ending in)\s+)(\d{2,4})\b", re.IGNORECASE),
]
CUSTOMER_ID_REGEXES = [re.compile(r"(\"customerId\"\s*:\s*\")([A-Z0-9]{10,20})(\")"),
                       re.compile(r"(data-raw-id=\")([A-Z0-9]{10,20})(\")")]
PHONE_REGEX = re.compile(r"((?:Telefon(?:nummer)?|Phone)\s*:?\s*)(\+?[\d][\d\s/()-]{5,}\d)", re.IGNORECASE)
KEEP_SCRIPT_ID_PREFIXES = ("shipToData", "__NEXT_DATA__")
REMOVE_SELECTORS = ["header", "footer", "#navbar", "#navbar-main", "#nav-belt", "#nav-main", "#navFooter",
                    "#nav-flyout-anchor", "#nav-flyout-ewc", "#rhf", "#skiplink", "iframe", "noscript", "style",
                    "link", "meta:not([charset])"]
REDACT_QUERY_KEYS = re.compile(r"(ship|package|track|itemid|lineitem|token|session|csrf|arb|customer|address|sig|"
                               r"encrypted|encoded|pd_rd|pf_rd|qid|sr|crid|cid|ref_?id|contractid|ats|requestid)", re.IGNORECASE)
TOKEN_VALUE_REGEX = re.compile(r"^[A-Za-z0-9+/=_%.-]{40,}$")
# Parsers select on these, and their values are hashes, not personal data
KEEP_ATTRIBUTES = ("id", "class", "name", "for")
WALLET_ID_REGEX = re.compile(r"amzn1\.pm\.wallet\.[A-Za-z0-9+/=_-]+")
# Carrier free text may name a neighbour or drop-off location, e.g. "von einem Nachbarn <Name> in Hausnummer ..."
CARRIER_FREE_TEXT_REGEX = re.compile(r"Hausnummer|Abgabeort|Nachbarn? [A-ZÄÖÜ]|neighbou?r [A-Z]")
FAKE_CARRIER_TEXT = "Die Sendung wurde einem Nachbarn übergeben"
JSON_TOKEN_REGEX = re.compile(r'"(\w*[Tt]oken|lastEvaluatedPageKey|csrf\w*)"(\s*:\s*)"([^"]{12,})"')
EXPIRATION_REGEX = re.compile(r'"(\w*[Ee]xpiration\w*)"\s*:\s*\{\s*"year"\s*:\s*\d+\s*,\s*"month"\s*:\s*\d+\s*\}')
JWT_REGEX = re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")
ADDRESS_SELECTORS = ["li.displayAddressFullName", "li.displayAddressAddressLine1", "li.displayAddressAddressLine2",
                     "li.displayAddressCityStateOrRegionPostalCode", "li.displayAddressPhoneNumber",
                     "[data-component='shippingAddress'] li", "div.displayAddressDiv li"]


class Anonymizer:
    def __init__(self, rules: Dict) -> None:
        self.salt = str(rules.get("id_salt") or "amazon-orders").encode("utf-8")
        self.replace: List[Dict[str, str]] = list(rules.get("replace", []))
        self.sensitive: Set[str] = set(rules.get("sensitive", []))
        self.order_ids: Dict[str, str] = {}
        self.customer_ids: Set[str] = set()
        self.card_digits: Set[str] = set()
        self.date_shift = datetime.timedelta(days=int(rules.get("date_shift_days", 0)))
        self.amount_factor = Decimal(str(rules.get("amount_factor", 1)))
        self.titles: Dict[str, str] = {}
        self.asins: Dict[str, str] = {}
        self.sellers: List[str] = []
        self.seller_ids: Dict[str, str] = {}

    def collect_identifiers(self, html: str) -> None:
        """Harvest customer IDs and card digits so they can be replaced wherever they appear, not only in context."""
        for regex in CUSTOMER_ID_REGEXES:
            self.customer_ids.update(m.group(2) for m in regex.finditer(html))
        for regex in CARD_DIGITS_REGEXES:
            self.card_digits.update(m.group(2) for m in regex.finditer(html) if m.group(2) != FAKE_CARD_DIGITS)
        self.sensitive.update(self.customer_ids)
        self.sensitive.update(self.card_digits)

    def fake_order_id(self, match: re.Match) -> str:
        original = match.group(0)
        if original not in self.order_ids:
            digest = hmac.new(self.salt, original.encode("utf-8"), hashlib.sha256).hexdigest()
            digits = str(int(digest, 16))[:14].rjust(14, "0")
            self.order_ids[original] = f"{match.group(1)}-{digits[:7]}-{digits[7:]}"
            self.sensitive.add(original)
        return self.order_ids[original]

    def collect_product_rules(self, soup: BeautifulSoup, raw_html: str) -> None:
        """Harvest product titles, ASINs and sellers, because what was bought is as personal as who bought it."""
        for selector in PRODUCT_TITLE_SELECTORS:
            for tag in soup.select(selector):
                self._add_product_title(tag.get_text(" "))
        # Only product images, payment method logos have alt texts like "Amazon Visa"
        for tag in soup.select(", ".join(f"{selector} img[alt]" for selector in PRODUCT_IMAGE_CONTAINER_SELECTORS)):
            self._add_product_title(str(tag["alt"]))
        asins = ASIN_REGEX.findall(raw_html)
        for asin_list in ASIN_LIST_REGEX.findall(raw_html):
            asins.extend(re.split(r"%2C|,", asin_list))
        for asin in asins:
            if asin not in self.asins and not asin.isalpha():
                self.asins[asin] = f"B0TEST{len(self.asins) + 1:04d}"
                self.sensitive.add(asin)
        for name in SELLER_NAME_REGEX.findall(raw_html):
            name = re.sub(r"\s+", " ", name).strip()
            if len(name) >= 3 and not name.lower().startswith("amazon") and name not in self.sellers:
                self.sellers.append(name)
                self.sensitive.add(name)
        for tag in soup.select("[data-component='orderedMerchant'] a"):
            name = re.sub(r"\s+", " ", tag.get_text(" ")).strip()
            if len(name) >= 3 and not name.lower().startswith("amazon") and name not in self.sellers:
                self.sellers.append(name)
                self.sensitive.add(name)
        for seller_id in SELLER_ID_REGEX.findall(raw_html):
            if seller_id not in PUBLIC_IDS and seller_id not in self.seller_ids:
                self.seller_ids[seller_id] = f"A0TESTSELLER{len(self.seller_ids) + 1:02d}"
                self.sensitive.add(seller_id)

    def _add_product_title(self, text: str) -> None:
        title = re.sub(r"\s+", " ", text).strip()
        if len(title) >= 4 and title not in self.titles:
            self.titles[title] = f"Testartikel {len(self.titles) + 1}"
            self.sensitive.add(title)

    def neutralize_products(self, soup: BeautifulSoup) -> None:
        titles = sorted(self.titles.items(), key=lambda t: len(t[0]), reverse=True)
        sellers = sorted(self.sellers, key=len, reverse=True)

        def neutralize(value: str) -> str:
            collapsed = re.sub(r"\s+", " ", value)
            changed = False
            for title, fake in titles:
                if title in collapsed:
                    collapsed, changed = collapsed.replace(title, fake), True
            for seller in sellers:
                if seller in collapsed:
                    collapsed, changed = collapsed.replace(seller, FAKE_SELLER), True
            return collapsed if changed else value

        for text in soup.find_all(string=True):
            if isinstance(text, Comment):
                continue
            new = neutralize(str(text))
            if new != str(text):
                text.replace_with(new)
        for tag in soup.find_all(True):
            for attr, value in list(tag.attrs.items()):
                if isinstance(value, str):
                    tag[attr] = neutralize(value)
        for selector in PRODUCT_DETAIL_SELECTORS:
            for tag in soup.select(selector):
                for text in tag.find_all(string=lambda t: t.strip() != ""):
                    self.sensitive.add(re.sub(r"\s+", " ", str(text)).strip())
                    text.replace_with("Details")

    def collect_address_rules(self, soup: BeautifulSoup) -> None:
        """Harvest recipient names and address lines, including those embedded in templates and popovers."""
        fragments = [soup]
        for tag in soup.select("script[id^='shipToData']"):
            fragments.append(BeautifulSoup(tag.string or "", "html.parser"))
        for tag in soup.select("[data-a-popover]"):
            try:
                inline = json.loads(str(tag["data-a-popover"])).get("inlineContent")
            except (ValueError, AttributeError):
                inline = None
            if inline:
                fragments.append(BeautifulSoup(inline, "html.parser"))

        known = {rule["find"] for rule in self.replace}

        def add(value: str, fake: str) -> None:
            if len(value) >= 3 and value not in known and value.lower() not in ("deutschland", "germany"):
                self.replace.append({"find": value, "replace": fake})
                self.sensitive.add(value)
                known.add(value)

        for fragment in fragments:
            # Order history cards: name in <h5>, then "street<br>city postal code", then the country
            for popover in fragment.select("[id^='a-popover-shippingAddress']"):
                for row in popover.select(".a-row"):
                    for line in row.stripped_strings:
                        line = re.sub(r"\s+", " ", line)
                        if row.find("h5"):
                            add(line, FAKE_NAME)
                        elif re.search(r"\b\d{5}\b", line):
                            add(line, FAKE_ADDRESS_LINES[2])
                        else:
                            add(line, FAKE_ADDRESS_LINES[0])
            for selector in ADDRESS_SELECTORS:
                for tag in fragment.select(selector):
                    value = re.sub(r"\s+", " ", tag.get_text(" ")).strip()
                    if len(value) < 3 or value in known or value.lower() in ("deutschland", "germany"):
                        continue
                    classes = " ".join(tag.get("class", []))
                    if "FullName" in classes:
                        fake = FAKE_NAME
                    elif "PhoneNumber" in classes:
                        fake = "Telefon: 030 1234567"
                    elif "AddressLine2" in classes:
                        fake = FAKE_ADDRESS_LINES[1]
                    elif "PostalCode" in classes or re.match(r"^\d{5}\b", value):
                        fake = FAKE_ADDRESS_LINES[2]
                    else:
                        fake = FAKE_ADDRESS_LINES[0]
                    self.replace.append({"find": value, "replace": fake})
                    self.sensitive.add(value)
                    known.add(value)

    def clean_structure(self, soup: BeautifulSoup) -> None:
        self.neutralize_products(soup)
        for tag in soup.find_all("script"):
            if not str(tag.get("id", "")).startswith(KEEP_SCRIPT_ID_PREFIXES):
                tag.decompose()
        for selector in REMOVE_SELECTORS:
            for tag in soup.select(selector):
                tag.decompose()
        for text in soup.find_all(string=CARRIER_FREE_TEXT_REGEX):
            if not isinstance(text, Comment) and text.parent.name != "script":
                self.sensitive.add(re.sub(r"\s+", " ", str(text)).strip())
                text.replace_with(FAKE_CARRIER_TEXT)
        for comment in soup.find_all(string=lambda s: isinstance(s, Comment)):
            comment.extract()
        for tag in soup.find_all("input"):
            if tag.get("type") == "hidden" and tag.get("value"):
                if len(str(tag["value"])) >= 12:
                    self.sensitive.add(str(tag["value"]))
                tag["value"] = "REDACTED"
        for tag in soup.find_all(True):
            if not isinstance(tag, Tag):
                continue
            for attr, value in list(tag.attrs.items()):
                if not isinstance(value, str):
                    continue
                if attr in ("href", "src", "action", "data-url", "data-href") and "?" in value:
                    tag[attr] = self.clean_url(value)
                elif attr not in KEEP_ATTRIBUTES and TOKEN_VALUE_REGEX.match(value) and \
                        not value.startswith(("http", "/")):
                    self.sensitive.add(value)
                    tag[attr] = "REDACTED"

    def shift_dates(self, html: str) -> str:
        years = [int(y) for y in re.findall(r"\b(20\d\d)\b", " ".join(m.group(0) for m in GERMAN_DATE_REGEX.finditer(html)))]
        # Dates like "Zugestellt: 1. August" have no year, assume the most recent one on the page
        default_year = max(years) if years else datetime.date.today().year

        def shift(match: re.Match) -> str:
            day, space, month, year_space, year = match.groups()
            try:
                date = datetime.date(int(year or default_year), GERMAN_MONTHS.index(month) + 1, int(day))
            except ValueError:
                return match.group(0)
            date += self.date_shift
            new_day = f"{date.day:02d}" if len(day) == 2 else str(date.day)
            result = f"{new_day}.{space}{GERMAN_MONTHS[date.month - 1]}"
            return result + f"{year_space}{date.year}" if year else result

        return GERMAN_DATE_REGEX.sub(shift, html)

    def scale_amounts(self, html: str) -> str:
        def scale(whole: str, cents: str, thousands: str) -> str:
            value = Decimal(whole.replace(thousands, "") + "." + cents) * self.amount_factor
            whole_new, cents_new = f"{value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}".split(".")
            grouped = f"{int(whole_new):,}".replace(",", thousands)
            return grouped + ("," if thousands == "." else ".") + cents_new

        html = GERMAN_AMOUNT_REGEX.sub(
            lambda m: scale(m.group(1), m.group(2), ".") + (m.group(3) or "") + "€", html)
        return US_EURO_AMOUNT_REGEX.sub(lambda m: "€" + scale(m.group(1), m.group(2), ","), html)

    def clean_url(self, url: str) -> str:
        parts = urlsplit(url)
        query = []
        for key, value in parse_qsl(parts.query, keep_blank_values=True):
            if REDACT_QUERY_KEYS.search(key) and value:
                if len(value) >= 8:
                    self.sensitive.add(value)
                value = "REDACTED"
            query.append((key, value))
        return urlunsplit(parts._replace(query=urlencode(query, safe="-")))

    def clean_text(self, html: str) -> str:
        for rule in sorted(self.replace, key=lambda r: len(r["find"]), reverse=True):
            html = re.sub(re.escape(rule["find"]), rule["replace"], html, flags=re.IGNORECASE)
            for variant in (json.dumps(rule["find"])[1:-1], json.dumps(rule["find"], ensure_ascii=False)[1:-1]):
                html = html.replace(variant, rule["replace"])
        html = ORDER_ID_REGEX.sub(self.fake_order_id, html)
        for title, fake in sorted(self.titles.items(), key=lambda t: len(t[0]), reverse=True):
            # Titles may also be embedded in JSON (escaped) or in text nodes BeautifulSoup kept escaped
            for variant in {json.dumps(title)[1:-1], json.dumps(title, ensure_ascii=False)[1:-1],
                            html_escape(title, quote=False), html_escape(title)}:
                html = html.replace(variant, fake)
        for identifier, fake in list(self.asins.items()) + list(self.seller_ids.items()):
            # IDs may directly follow a URL-encoded comma ("%2C"), so a plain word boundary is not enough
            html = re.sub(r"(?:(?<=%2C)|(?<![A-Za-z0-9]))" + identifier + r"(?![A-Za-z0-9])", fake, html)
        html = PRODUCT_IMAGE_REGEX.sub(r"\g<1>" + FAKE_IMAGE_ID, html)
        html = VIDEO_ID_REGEX.sub(FAKE_VIDEO_ID, html)
        html = STATEMENT_DESCRIPTOR_REGEX.sub(
            lambda m: m.group(0) if re.search(r"AMZN|AMAZON", m.group(1).upper()) or not m.group(1)
            else self._track(m, 1, "BEISPIELHAENDLER"), html)
        html = WALLET_ID_REGEX.sub(lambda m: self._track(m, 0, "amzn1.pm.wallet.REDACTED"), html)
        html = EXPIRATION_REGEX.sub(r'"\g<1>":{"year":2030,"month":1}', html)
        html = JSON_TOKEN_REGEX.sub(lambda m: self._track(m, 3, "REDACTED"), html)
        html = JWT_REGEX.sub(lambda m: self._track(m, 0, "REDACTED"), html)
        for email in set(EMAIL_REGEX.findall(html)):
            if email != FAKE_EMAIL:
                self.sensitive.add(email)
                html = html.replace(email, FAKE_EMAIL)
        for regex in CARD_DIGITS_REGEXES:
            html = regex.sub(lambda m: self._track(m, 2, FAKE_CARD_DIGITS), html)
        for customer_id in self.customer_ids:
            html = html.replace(customer_id, FAKE_CUSTOMER_ID)
        for digits in self.card_digits:
            # Card digits are often rendered in their own element, separate from the "••••" prefix
            html = re.sub(r">(\s*)" + re.escape(digits) + r"(\s*)<", r">\g<1>" + FAKE_CARD_DIGITS + r"\g<2><", html)
        html = self.shift_dates(html)
        html = self.scale_amounts(html)
        html = PHONE_REGEX.sub(lambda m: self._track(m, 2, "030 1234567"), html)
        # Tokens redacted in one attribute may be repeated elsewhere, e.g. URL-encoded inside ad slot JSON
        for value in sorted((v for v in self.sensitive if len(v) >= 12 and "@" not in v), key=len, reverse=True):
            for variant in {value, quote(value, safe=""), quote(quote(value, safe=""), safe="")}:
                html = html.replace(variant, "REDACTED")
        return html

    def _track(self, match: re.Match, group: int, fake: str) -> str:
        value = match.group(group)
        if value != fake:
            self.sensitive.add(value)
        return match.group(0).replace(value, fake, 1) if value != fake else match.group(0)

    def leftovers(self, html: str) -> List[str]:
        found = []
        for value in self.sensitive:
            # Short values like card digits are only checked in context, a bare "1234" may be a price
            if len(value) <= 4:
                if re.search(r"(•|\*|endet auf|ending in|lastDigits\"\s*:\s*\")\s*" + re.escape(value), html) or \
                        re.search(r">\s*" + re.escape(value) + r"\s*<", html):
                    found.append(value)
            elif value.lower() in html.lower():
                found.append(value)
        return found


def main() -> None:
    parser = argparse.ArgumentParser(description="Anonymize raw Amazon pages for use as test resources.")
    parser.add_argument("--rules", required=True, help="Private JSON rules file (never commit it).")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--extra-sensitive-file", action="append", default=[],
                        help="JSON file whose values must not survive (e.g. the cookie jar).")
    parser.add_argument("pages", nargs="+", help="raw_path:output_relative_path[:cards=0,3,5]")
    args = parser.parse_args()

    with open(os.path.expanduser(args.rules), encoding="utf-8") as f:
        anonymizer = Anonymizer(json.load(f))
    for path in args.extra_sensitive_file:
        with open(os.path.expanduser(path), encoding="utf-8") as f:
            data = json.load(f)
        anonymizer.sensitive.update(v for v in (data.values() if isinstance(data, dict) else data)
                                    if isinstance(v, str) and len(v) >= 12)

    pairs = [page.split(":") for page in args.pages]
    soups = []
    for raw_path, *_ in pairs:
        with open(os.path.expanduser(raw_path), encoding="utf-8") as f:
            raw = f.read()
        anonymizer.collect_identifiers(raw)
        soup = BeautifulSoup(raw, "html.parser")
        anonymizer.collect_address_rules(soup)
        anonymizer.collect_product_rules(soup, raw)
        soups.append(soup)

    written = []
    for (_, out_rel, *options), soup in zip(pairs, soups):
        for option in options:
            if option.startswith("cards="):
                keep = {int(i) for i in option[len("cards="):].split(",")}
                for index, card in enumerate(soup.select("div.order-card")):
                    if index not in keep:
                        card.decompose()
        anonymizer.clean_structure(soup)
        html = anonymizer.clean_text(str(soup))
        out_rel = ORDER_ID_REGEX.sub(anonymizer.fake_order_id, out_rel)
        out_path = os.path.join(args.output_dir, out_rel)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        written.append(out_path)

    failed = False
    for out_path in written:
        with open(out_path, encoding="utf-8") as f:
            leftovers = anonymizer.leftovers(f.read())
        size = os.path.getsize(out_path) // 1024
        if leftovers:
            failed = True
            print(f"LEAK {out_path} ({size} KB): {len(leftovers)} sensitive value(s) survived")
            with open(out_path, encoding="utf-8") as f:
                html = f.read()
            for value in leftovers:
                # Show only a masked hint and the surrounding markup, never the value itself
                index = html.lower().find(value.lower())
                context = html[max(0, index - 80):index + len(value) + 40] if index >= 0 else ""
                print(f"     {value[:2]}…({len(value)} chars): {re.sub(r'\s+', ' ', context.replace(value, '<X>'))}")
        else:
            print(f"ok   {out_path} ({size} KB)")
    print(f"{len(anonymizer.order_ids)} order numbers replaced, {len(anonymizer.replace)} text rules applied, "
          f"{len(anonymizer.sensitive)} sensitive values checked.")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
