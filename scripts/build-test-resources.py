#!/usr/bin/env python

"""
The purpose of this script is to pull the same pages used for integration tests,
obfuscate the data as needed, and then store versions of those HTML files in tests/resources
so unit tests can be run against the same data.
"""

import os
import sys

from amazonorders.session import AmazonSession

from bs4 import BeautifulSoup

if not (os.environ.get("AMAZON_USERNAME") and os.environ.get("AMAZON_PASSWORD")):
    print("AMAZON_USERNAME and AMAZON_PASSWORD environment variables not set")

    sys.exit(1)

amazon_session = AmazonSession(os.environ["AMAZON_USERNAME"], os.environ["AMAZON_USERNAME"])
amazon_session.login()

# TODO: list of all Amazon order history and order details pages we want to get
pages_to_download = [
    "https://www.amazon.com/gp/your-account/order-details?orderID=112-0399923-3070642",
    "https://www.amazon.com/gp/your-account/order-details?orderID=114-9460922-7737063",
    "https://www.amazon.com/gp/your-account/order-details?orderID=112-2961628-4757846",
    "https://www.amazon.com/gp/your-account/order-details?orderID=112-9685975-5907428",
    "https://www.amazon.com/gp/your-account/order-details?orderID=113-1625648-3437067",
]
for page in pages_to_download:
    response = amazon_session.get(page)
    response_parsed = BeautifulSoup(response.text, "html.parser")

    # TODO: obfuscate

    # TODO: the page name should include the order ID, or history page
    page_name = amazon_session._get_page_from_url(amazon_session.last_response.url)
    with open(os.path.join("tests", "resources", page_name), "w", encoding="utf-8") as html_file:
        html_file.write(str(response_parsed))

print("\nDONE: Test resources update from live data. Be sure to verify data was properly "
      "obfuscated before committing any changes.")
