.. image:: https://badge.fury.io/py/amazon-orders.svg
    :target: https://badge.fury.io/py/amazon-orders
.. image:: https://github.com/alexdlaird/amazon-orders-python/actions/workflows/build.yml/badge.svg
    :target: https://github.com/alexdlaird/amazon-orders-python/actions/workflows/build.yml
.. image:: https://codecov.io/gh/alexdlaird/amazon-orders-python/branch/main/graph/badge.svg
    :target: https://codecov.io/gh/alexdlaird/amazon-orders-python
.. image:: https://img.shields.io/pypi/pyversions/amazon-orders.svg
    :target: https://pypi.org/project/amazon-orders/
.. image:: https://img.shields.io/pypi/l/amazon-orders.svg
    :target: https://pypi.org/project/amazon-orders/

*************
Amazon Orders
*************

``amazon-orders`` is an unofficial library that provides a command line
interface alongside a programmatic API that can be used to interact with
Amazon.com’s consumer-facing website.

This works by parsing website data from Amazon.com. A nightly
build validates functionality to ensure its stability, but as Amazon
provides no official API to use, this package may break at any time.
This package only supports the English version of the website.

Installation
============

``amazon-orders`` is available on
`PyPI <https://pypi.org/project/amazon-orders/>`__ and can be installed
using ``pip``:

.. code:: sh

    pip install amazon-orders

That’s it! ``amazon-orders`` is now available as a Python package is
available from the command line.

Basic Usage
===========

Execute ``amazon-orders`` from the command line with:

.. code:: sh

    amazon-orders --username <AMAZON_EMAIL> --password <AMAZON_PASSWORD> history

Or use ``amazon-orders`` programmatically:

.. code:: python

    from amazonorders.session import AmazonSession
    from amazonorders.orders import AmazonOrders

    amazon_session = AmazonSession("<AMAZON_EMAIL>", "<AMAZON_PASSWORD>")
    amazon_session.login()

    amazon_orders = AmazonOrders(amazon_session)
    orders = amazon_orders.get_order_history(year=2023)

    for order in orders:
        print("{} - {}".format(order.order_number, order.grand_total))

Dive Deeper
===========

For more advanced usage, dive deeper in to the rest of the documentation.

.. toctree::
   :maxdepth: 2

   api

.. include:: ../CONTRIBUTING.rst
