#!/usr/bin/env python

__copyright__ = "Copyright (c) 2024 Alex Laird"
__license__ = "MIT"

import json
import os
import re
import sys

from bs4 import BeautifulSoup

from amazonorders.constants import ORDER_HISTORY_URL, ORDER_DETAILS_URL
from amazonorders.session import AmazonSession

ROOT_DIR = os.path.normpath(
    os.path.join(os.path.abspath(os.path.dirname(__file__)), ".."))


def _obfuscate(response_parsed, hide_data_rules):
    cleaned = str(response_parsed)
    for rule in hide_data_rules:
        pattern = re.compile(rule["find_pattern"], re.IGNORECASE)
        cleaned = pattern.sub(rule["replace"], cleaned)
    return BeautifulSoup(cleaned, "html.parser")


def build_test_resources(args):
    """
    The purpose of this script is to pull the same pages used for integration tests,
    obfuscate the data as needed, and then store versions of those HTML files in tests/resources
    so unit tests can be run against the same data.

    This script should be invoked using `make build-test-resources` and requires AMAZON_USERNAME
    and AMAZON_PASSWORD environment variables to be set.

    To use this script to generate orders that correspond correctly to the unit tests, contact the
    owner of the GitHub repo.
    """

    if not (os.environ.get("AMAZON_USERNAME") and os.environ.get("AMAZON_PASSWORD")):
        print(
            "AMAZON_USERNAME and AMAZON_PASSWORD environment variables not set")

        sys.exit(1)

    amazon_session = AmazonSession(os.environ["AMAZON_USERNAME"],
                                   os.environ["AMAZON_PASSWORD"])
    amazon_session.login()

    pages_to_download = [
        {"type": "order-history", "year": "2010", "start-index": "0"},
        {"type": "order-history", "year": "2010", "start-index": "10"},
        {"type": "order-history", "year": "2018", "start-index": "0"},
        {"type": "order-history", "year": "2020", "start-index": "40"},
        {"type": "order-history", "year": "2020", "start-index": "50"},
        {"type": "order-history", "year": "2023", "start-index": "10"},
        {"type": "order-details", "order-id": "112-0399923-3070642"},
        {"type": "order-details", "order-id": "114-9460922-7737063"},
        {"type": "order-details", "order-id": "112-2961628-4757846"},
        {"type": "order-details", "order-id": "112-9685975-5907428"},
        {"type": "order-details", "order-id": "113-1625648-3437067"},
    ]

    """
    This variable should contain a JSON blob that matches this format:
    
    [
        {"find_pattern": "Some Sensitive Data (case will be ignored)", "replace": "Obfuscated Replacement"},
        {"find_pattern": "555 My Private Address (and regex pattern can be used)", "replace": "555 My Public Address"},
        {"find_pattern": "Secret City, VT 22222", "replace": "San Francisco, CA 94016"},
        {"find_pattern": "card ending in 1234", "replace": "card ending in 4321"}
    ]
    """
    hide_data_rules = json.loads(os.environ["HIDE_DATA_RULES"])

    if not hide_data_rules:
        print("HIDE_DATA_RULES environment variables not set, see script for details")

        sys.exit(1)

    for page in pages_to_download:
        if page["type"] == "order-details":
            url = f"{ORDER_DETAILS_URL}?orderID={page['order-id']}"
            response = amazon_session.get(url)
            response_parsed = BeautifulSoup(response.text, "html.parser")

            cleaned_response = _obfuscate(response_parsed, hide_data_rules)

            page_name = f"order-details-{page['order-id']}.html"
        else:
            url = f"{ORDER_HISTORY_URL}?timeFilter=year-{page['year']}&startIndex={page['start-index']}"
            response = amazon_session.get(url)
            response_parsed = BeautifulSoup(response.text, "html.parser")

            cleaned_response = _obfuscate(response_parsed, hide_data_rules)

            page_name = f"order-history-{page['year']}-{page['start-index']}.html"

        with open(os.path.join(ROOT_DIR, "tests", "resources", page_name), "w",
                  encoding="utf-8") as html_file:
            html_file.write(str(cleaned_response))

    print(
        "\nDONE: Test resources update from live data. Be sure to verify data was properly "
        "obfuscated before committing any changes.")


if __name__ == "__main__":
    build_test_resources(sys.argv)
