#!/usr/bin/env python

import os
import sys

from amazonorders.session import AmazonSession

if not (os.environ.get("AMAZON_USERNAME") and os.environ.get(
        "AMAZON_PASSWORD")):
    print("AMAZON_USERNAME and AMAZON_PASSWORD environment variables not set")

    sys.exit(1)

amazon_session = AmazonSession(os.environ["AMAZON_USERNAME"], os.environ["AMAZON_USERNAME"])
amazon_session.login()

# TODO: implement the script that pulls down latest tests/resources files, which can be committed on occassion to ensure unit tests are working with latest parsable data

