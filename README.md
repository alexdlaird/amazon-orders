<p align="center"><img alt="amazon-orders - A Python libray (and CLI) for Amazon order history" src="https://amazon-orders.readthedocs.io/_images/logo.png" /></p>

[![Version](https://img.shields.io/pypi/v/amazon-orders)](https://pypi.org/project/amazon-orders)
[![Python Versions](https://img.shields.io/pypi/pyversions/amazon-orders.svg)](https://pypi.org/project/amazon-orders)
[![Coverage](https://img.shields.io/codecov/c/github/alexdlaird/amazon-orders)](https://codecov.io/gh/alexdlaird/amazon-orders)
[![Build](https://img.shields.io/github/actions/workflow/status/alexdlaird/amazon-orders/build.yml)](https://github.com/alexdlaird/amazon-orders/actions/workflows/build.yml)
[![Docs](https://img.shields.io/readthedocs/amazon-orders)](https://amazon-orders.readthedocs.io)
[![GitHub License](https://img.shields.io/github/license/alexdlaird/amazon-orders)](https://github.com/alexdlaird/amazon-orders/blob/main/LICENSE)

`amazon-orders` is an unofficial library that provides a Python API (and CLI) for Amazon order history.

This package works by parsing data from Amazon's consumer-facing website. A periodic build validates functionality
to ensure its stability, but as Amazon provides no official API to use, this package may break at any time (so check
often to ensure you're on the latest version).

Only the English, `.com` version of Amazon is officially supported.

## Installation

`amazon-orders` is available on [PyPI](https://pypi.org/project/amazon-orders/) and can be installed and/or upgraded using `pip`:

```sh
pip install amazon-orders --upgrade
```

That's it! `amazon-orders` is now available as a package to your Python projects and from the command line.

If pinning, be sure to use a wildcard for the [minor version](https://semver.org/) (ex. `==4.0.*`, not `==4.0.18`) to
ensure you always get the latest stable release.

## Basic Usage

You'll use [`AmazonSession`](https://amazon-orders.readthedocs.io/api.html#amazonorders.session.AmazonSession) to
authenticate your Amazon account, then [`AmazonOrders`](https://amazon-orders.readthedocs.io/api.html#amazonorders.orders.AmazonOrders)
and [`AmazonTransactions`](https://amazon-orders.readthedocs.io/api.html#amazonorders.transactions.AmazonTransactions)
to interact with account data. [`get_order_history`](https://amazon-orders.readthedocs.io/api.html#amazonorders.orders.AmazonOrders.get_order_history)
and [`get_order`](https://amazon-orders.readthedocs.io/api.html#amazonorders.orders.AmazonOrders.get_order) are good places to start.

```python
from amazonorders.session import AmazonSession
from amazonorders.orders import AmazonOrders

amazon_session = AmazonSession("<AMAZON_EMAIL>",
                               "<AMAZON_PASSWORD>")
amazon_session.login()

amazon_orders = AmazonOrders(amazon_session)

# Get orders from a specific year
orders = amazon_orders.get_order_history(year=2023)

# Or use time filters for recent orders
orders = amazon_orders.get_order_history(time_filter="last30")  # Last 30 days
orders = amazon_orders.get_order_history(time_filter="months-3")  # Past 3 months

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

### Automating Authentication

Authentication can be automated by (in order of precedence) storing credentials in environment variables, passing them
to [`AmazonSession`](https://amazon-orders.readthedocs.io/api.html#amazonorders.session.AmazonSession), or storing them
in [`AmazonOrdersConfig`](https://amazon-orders.readthedocs.io/api.html#amazonorders.conf.AmazonOrdersConfig). The
environment variables `amazon-orders` looks for are:

- `AMAZON_USERNAME`
- `AMAZON_PASSWORD`
- `AMAZON_OTP_SECRET_KEY` (see [docs for usage](https://amazon-orders.readthedocs.io/api.html#amazonorders.session.AmazonSession.otp_secret_key))

## Documentation

For more advanced usage, `amazon-orders`'s official documentation is available
at [Read the Docs](http://amazon-orders.readthedocs.io).

## Contributing

If you would like to get involved, be sure to review
the [Contribution Guide](https://github.com/alexdlaird/amazon-orders/blob/main/CONTRIBUTING.rst).

Want to contribute financially? If you've found `amazon-orders`
useful, [sponsorship](https://github.com/sponsors/alexdlaird) would
also be greatly appreciated!
