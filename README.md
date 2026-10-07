<p align="center"><img alt="amazon-orders - A Python library (and CLI) for Amazon order history" src="https://amazon-orders.readthedocs.io/_images/logo.png" /></p>

[![Version](https://img.shields.io/pypi/v/amazon-orders)](https://pypi.org/project/amazon-orders)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/amazon-orders)](https://pypistats.org/packages/amazon-orders)
[![Python Versions](https://img.shields.io/pypi/pyversions/amazon-orders.svg)](https://pypi.org/project/amazon-orders)
[![Coverage](https://img.shields.io/codecov/c/github/alexdlaird/amazon-orders)](https://codecov.io/gh/alexdlaird/amazon-orders)
[![Build](https://img.shields.io/github/actions/workflow/status/alexdlaird/amazon-orders/build.yml)](https://github.com/alexdlaird/amazon-orders/actions/workflows/build.yml)
[![Docs](https://img.shields.io/readthedocs/amazon-orders)](https://amazon-orders.readthedocs.io)
[![GitHub License](https://img.shields.io/github/license/alexdlaird/amazon-orders)](https://github.com/alexdlaird/amazon-orders/blob/main/LICENSE)

`amazon-orders` is an unofficial library that provides a Python API (and CLI) for Amazon order history, line items, and transactions.

> **Note:** This package works by parsing data from Amazon's consumer-facing website. A periodic build validates
> functionality to ensure its stability, but as Amazon provides no official API to use, older versions of this
> package may break at any time, so it's recommended that you use the latest version.

## Installation

`amazon-orders` is available on [PyPI](https://pypi.org/project/amazon-orders/) and can be installed and/or upgraded using `pip`:

```sh
pip install amazon-orders --upgrade
```

That's it! `amazon-orders` is now available as a package to your Python projects and from the command line.

If pinning, be sure to use a wildcard for the [minor version](https://semver.org/) (e.g. `==4.9.*`, not `==4.9.0`) to
ensure you always get the latest stable release.

## Basic Usage

You'll use [`AmazonSession`](https://amazon-orders.readthedocs.io/api.html#amazonorders.session.AmazonSession) to
authenticate your Amazon account, then [`AmazonOrders`](https://amazon-orders.readthedocs.io/api.html#amazonorders.orders.AmazonOrders),
[`AmazonTransactions`](https://amazon-orders.readthedocs.io/api.html#amazonorders.transactions.AmazonTransactions),
[`AmazonGiftCards`](https://amazon-orders.readthedocs.io/api.html#amazonorders.gift_cards.AmazonGiftCards),
and [`AmazonPrime`](https://amazon-orders.readthedocs.io/api.html#amazonorders.prime.AmazonPrime)
to interact with account data. [`get_order_history`](https://amazon-orders.readthedocs.io/api.html#amazonorders.orders.AmazonOrders.get_order_history)
and [`get_order`](https://amazon-orders.readthedocs.io/api.html#amazonorders.orders.AmazonOrders.get_order) are good places to start.

```python
from amazonorders.constants import Constants
from amazonorders.session import AmazonSession
from amazonorders.orders import AmazonOrders

amazon_session = AmazonSession("<AMAZON_EMAIL>",
                               "<AMAZON_PASSWORD>")
amazon_session.login()

amazon_orders = AmazonOrders(amazon_session)

# Get orders from a specific year
orders = amazon_orders.get_order_history(year=2023)

# Or use time filters for recent orders
orders = amazon_orders.get_order_history(time_filter=Constants.LAST_30_DAYS_TIME_FILTER)
orders = amazon_orders.get_order_history(time_filter=Constants.LAST_3_MONTHS_TIME_FILTER)

for order in orders:
    print(f"{order.order_number} - {order.grand_total}")
```

If the fields you're looking for aren't populated with the above, set `full_details=True` (or pass `--full-details` to
the `history` CLI command), since by default it is `False` (enabling it slows down querying, since an additional
request for each order is necessary). Have a look at the [Order](https://amazon-orders.readthedocs.io/api.html#amazonorders.entity.order.Order) entity's docs to see what fields are only
populated with full details.

### Command Line Usage

You can also run any command available to the main Python interface from the command line:

```sh
amazon-orders login
amazon-orders history --year 2023
amazon-orders history --last-30-days
amazon-orders history --last-3-months
```

### Output Formats

The `history`, `order`, `invoice-pdfs`, `transactions`, `order-transactions`, `gift-card-activity`, `family-members`,
and `prime-payments` commands accept `--output`, which renders Orders, Invoice PDFs, Transactions, Gift Card activity,
Amazon Household members, and Prime payments as `text` (the default), `json`, `yaml`, or `csv`. Progress messages are
written to `stderr`, so redirecting `stdout` captures only the data.

```sh
amazon-orders history --year 2023 --output json > orders.json
amazon-orders history --last-30-days --output csv > orders.csv
```

To serialize from Python instead, every entity has [`to_dict()`](https://amazon-orders.readthedocs.io/api.html#amazonorders.entity.parsable.Parsable.to_dict),
which converts it and its nested entities to a `dict` of primitives.

```python
import json

from amazonorders.orders import AmazonOrders

amazon_orders = AmazonOrders(amazon_session)
orders = amazon_orders.get_order_history(year=2023)

# [{"order_number": "112-9685975-5907428", "grand_total": 35.98, ...}]
print(json.dumps([order.to_dict() for order in orders], indent=2))
```

See [`OutputFormatter`](https://amazon-orders.readthedocs.io/api.html#amazonorders.output.OutputFormatter) for each format's contract, and to override how
entities are rendered.

### Secure Sign-In

The most secure way to use `amazon-orders` is to sign in on Amazon's own page, in a browser window, so `amazon-orders`
never needs to store your credentials:

```sh
amazon-orders login --browser
```

The session is persisted, so neither the CLI nor the Python API needs credentials:

```python
from amazonorders.session import AmazonSession

amazon_session = AmazonSession()
amazon_session.login()
```

This requires a display and the `browser` extra (see [Browser Automation](https://amazon-orders.readthedocs.io/browser.html#installation) to install it).

### Automating Authentication

Authentication can be automated by (in order of precedence) storing credentials in environment variables, passing them
to [`AmazonSession`](https://amazon-orders.readthedocs.io/api.html#amazonorders.session.AmazonSession), or storing them
in [`AmazonOrdersConfig`](https://amazon-orders.readthedocs.io/api.html#amazonorders.conf.AmazonOrdersConfig). The
environment variables `amazon-orders` looks for are:

- `AMAZON_USERNAME`
- `AMAZON_PASSWORD`
- `AMAZON_OTP_SECRET_KEY` (see [`otp_secret_key`](https://amazon-orders.readthedocs.io/api.html#amazonorders.session.AmazonSession.otp_secret_key))

Any other config value can be set the same way, as `AMAZON_<KEY>` (see [`AmazonOrdersConfig`](https://amazon-orders.readthedocs.io/api.html#amazonorders.conf.AmazonOrdersConfig)).

A configured username also applies to `amazon-orders login --browser`: it's filled in and submitted for you, so the
browser opens on Amazon's password or passkey step. The browser never fills in your password.

### Languages and Regions

`amazon-orders` reads Amazon's pages in English. The `.com` site is validated nightly.

- **Any other site that offers English** (e.g. `amazon.co.uk`, or `amazon.de`): set the
  `domain` config option. These are supported on a best-effort basis. See
  [Supported Sites](https://amazon-orders.readthedocs.io/language-packages.html#supported-sites).
- **Any site, in another language**: install a language package and set `language_package`. A language package
  lets `amazon-orders` read the site's pages; its own CLI and messages stay in English. See
  [Language Packages](https://amazon-orders.readthedocs.io/language-packages.html).

### AI Assistants

An AI assistant has two ways to use `amazon-orders`. One that runs commands uses the CLI or the library directly, just
as shown above. Any MCP client gets the same as tools through
[`amazon-orders-mcp`](https://github.com/alexdlaird/amazon-orders-mcp#readme), a server built on `amazon-orders` — see
its README for setup.

The server signs you in with a browser, so it needs a display. Without one, use the CLI or library with
[Automating Authentication](#automating-authentication).

## Documentation

For more advanced usage, `amazon-orders`'s official documentation is available
at [Read the Docs](http://amazon-orders.readthedocs.io), including
[handling login challenges](https://amazon-orders.readthedocs.io/index.html#handling-challenges) (AWS WAF and JavaScript
checks, with optional extras) and [troubleshooting](https://amazon-orders.readthedocs.io/troubleshooting.html).

## Contributing

If you would like to get involved, be sure to review
the [Contribution Guide](https://github.com/alexdlaird/amazon-orders/blob/main/CONTRIBUTING.rst).

Want to contribute financially? If you've found `amazon-orders`
useful, [sponsorship](https://github.com/sponsors/alexdlaird) would
also be greatly appreciated!
