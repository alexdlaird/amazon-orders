#!/usr/bin/env python

import os
import sys

from amazonorders.session import AmazonSession

from bs4 import BeautifulSoup

__author__ = "Alex Laird"
__copyright__ = "Copyright 2024, Alex Laird"
__version__ = "0.0.5"


def build_test_resources(args):
    """
    The purpose of this script is to pull the same pages used for integration tests,
    obfuscate the data as needed, and then store versions of those HTML files in tests/resources
    so unit tests can be run against the same data.

    This script should be invoked using `make build-test-resources` and requires AMAZON_USERNAME
    and AMAZON_PASSWORD environment variables to be set.
    """

    if not (os.environ.get("AMAZON_USERNAME") and os.environ.get("AMAZON_PASSWORD")):
        print("AMAZON_USERNAME and AMAZON_PASSWORD environment variables not set")

        sys.exit(1)

    amazon_session = AmazonSession(os.environ["AMAZON_USERNAME"], os.environ["AMAZON_USERNAME"], debug=True)
    amazon_session.login()

    # TODO: list of all Amazon order history and order details pages we want to get
    pages_to_download = [
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

    for page in pages_to_download:
        if page["type"] == "order-details":
            url = "https://www.amazon.com/gp/your-account/order-details?orderID={}".format(page["order-id"]),
            response = amazon_session.get(url)
            response_parsed = BeautifulSoup(response.text, "html.parser")

            # TODO: obfuscate

            page_name = "order-details-{}.html".format(page["order-id"])
        else:
            url = "https://www.amazon.com/your-orders/orders?timeFilter=year-{}&startIndex={}".format(page["year"],
                                                                                                      page[
                                                                                                          "start-index"])
            response = amazon_session.get(url)
            response_parsed = BeautifulSoup(response.text, "html.parser")

            # TODO: obfuscate

            page_name = "order-history-{}-{}.html".format(page["year"], page["start-index"])

        with open(os.path.join("tests", "resources", page_name), "w", encoding="utf-8") as html_file:
            html_file.write(str(response_parsed))

    print("\nDONE: Test resources update from live data. Be sure to verify data was properly "
          "obfuscated before committing any changes.")


if __name__ == "__main__":
    build_test_resources(sys.argv)
