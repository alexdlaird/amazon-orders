<p align="center"><img alt="amazon-orders - A Python libray (and CLI) for Amazon order history" src="https://amazon-orders.readthedocs.io/_images/logo.png" /></p>

[![Version](https://img.shields.io/pypi/v/amazon-orders)](https://pypi.org/project/amazon-orders)
[![Python Versions](https://img.shields.io/pypi/pyversions/amazon-orders.svg)](https://pypi.org/project/amazon-orders)
[![Coverage](https://img.shields.io/codecov/c/github/alexdlaird/amazon-orders)](https://codecov.io/gh/alexdlaird/amazon-orders)
[![Build](https://img.shields.io/github/actions/workflow/status/alexdlaird/amazon-orders/build.yml)](https://github.com/alexdlaird/amazon-orders/actions/workflows/build.yml)
[![Docs](https://img.shields.io/readthedocs/amazon-orders)](https://amazon-orders.readthedocs.io)
[![GitHub License](https://img.shields.io/github/license/alexdlaird/amazon-orders)](https://github.com/alexdlaird/amazon-orders/blob/main/LICENSE)

`amazon-orders` is an unofficial library that provides a Python API (and CLI) for Amazon order history.

This package works by parsing data from Amazon's consumer-facing website. A periodic build validates functionality
to ensure its stability, but as Amazon provides no official API to use, this package may break at any time. Pin
the [minor (not patch) version](https://semver.org/) wildcard (ex. `==1.1.*`, not `==1.1.4`) to ensure you always get the latest
stable release.

This package only officially supports the English, `.com` version of Amazon.

## Installation

`amazon-orders` is available on [PyPI](https://pypi.org/project/amazon-orders/) and can be installed using `pip`:

```sh
pip install amazon-orders
```

That's it! `amazon-orders` is now available as a Python package is available from the command line.

## Basic Usage

Execute `amazon-orders` from the command line with:

```sh
amazon-orders --username <AMAZON_EMAIL> --password <AMAZON_PASSWORD> history
```

Or use `amazon-orders` programmatically:

```python
from amazonorders.session import AmazonSession
from amazonorders.orders import AmazonOrders

amazon_session = AmazonSession("<AMAZON_EMAIL>",
                               "<AMAZON_PASSWORD>")
amazon_session.login()

amazon_orders = AmazonOrders(amazon_session)
orders = amazon_orders.get_order_history(year=2023)

for order in orders:
    print(f"{order.order_number} - {order.grand_total}")
```

## Documentation

For more advanced usage, `amazon-orders`'s official documentation is available
at [http://amazon-orders.readthedocs.io](http://amazon-orders.readthedocs.io).

## Contributing

If you would like to get involved, be sure to review
the [Contribution Guide](https://github.com/alexdlaird/amazon-orders/blob/main/CONTRIBUTING.rst).

Want to contribute financially? If you've found `amazon-orders`
useful, [sponsorship](https://github.com/sponsors/alexdlaird) would
also be greatly appreciated!