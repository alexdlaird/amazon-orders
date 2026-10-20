#!/usr/bin/env python

__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import json
import os
import re
import sys

REDACTED_VALUE = "REDACTED"

#: The cookies whose values are kept, as pairs of patterns their name and value must each match in full. Every other
#: cookie's value is redacted, since Amazon adds new session cookies without notice.
NON_SENSITIVE_COOKIES = [
    (re.compile(r"lc-[a-z]+"), re.compile(r"[a-z]{2}_[A-Z]{2}")),
    (re.compile(r"i18n-prefs"), re.compile(r"[A-Z]{3}")),
]


def _is_non_sensitive(cookie):
    return any(name_pattern.fullmatch(cookie["name"]) and value_pattern.fullmatch(str(cookie["value"]))
               for name_pattern, value_pattern in NON_SENSITIVE_COOKIES)


def redact_cookies(cookies):
    return [cookie if _is_non_sensitive(cookie) else {**cookie, "value": REDACTED_VALUE} for cookie in cookies]


def redact_cookie_jar(cookie_jar_path):
    """
    Redact the values of the cookies in a cookie jar written by ``AmazonSession``, in place, so it can be shared
    (for instance, as a CI artifact) without sharing the session. Names, domains, paths, expiry, and secure flags are
    kept, so it's still useful for debugging which cookies Amazon set.

    :param cookie_jar_path: The path to the cookie jar.
    :return: ``True`` if the cookie jar was redacted, ``False`` if it doesn't exist.
    """
    if not os.path.exists(cookie_jar_path):
        return False

    with open(cookie_jar_path, "r", encoding="utf-8") as f:
        redacted_cookies = redact_cookies(json.load(f))

    with open(cookie_jar_path, "w", encoding="utf-8") as f:
        json.dump(redacted_cookies, f)

    return True


def main(args):
    if len(args) != 2:
        print(f"Usage: {args[0]} <cookie-jar-path>")

        sys.exit(1)

    cookie_jar_path = args[1]
    if redact_cookie_jar(cookie_jar_path):
        print(f"Redacted cookie values in {cookie_jar_path}")
    else:
        print(f"{cookie_jar_path} doesn't exist, so there's nothing to redact")


if __name__ == "__main__":
    main(sys.argv)
