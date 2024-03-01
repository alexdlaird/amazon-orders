.. rst-class:: hide-header

*************
Amazon Orders
*************

.. image:: _html/logo.png
   :alt: amazon-orders - a python library
   :align: center

|

.. image:: https://img.shields.io/pypi/v/amazon-orders
   :target: https://pypi.org/project/amazon-orders
.. image:: https://img.shields.io/pypi/pyversions/amazon-orders.svg
   :target: https://pypi.org/project/amazon-orders
.. image:: https://img.shields.io/codecov/c/github/alexdlaird/amazon-orders
   :target: https://codecov.io/gh/alexdlaird/amazon-orders
.. image:: https://img.shields.io/github/actions/workflow/status/alexdlaird/amazon-orders/build.yml
   :target: https://github.com/alexdlaird/amazon-orders/actions/workflows/build.yml
.. image:: https://img.shields.io/readthedocs/amazon-orders
   :target: https://amazon-orders.readthedocs.io/en/latest
.. image:: https://img.shields.io/github/license/alexdlaird/amazon-orders
   :target: https://github.com/alexdlaird/amazon-orders

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

    amazon_session = AmazonSession("<AMAZON_EMAIL>",
                                   "<AMAZON_PASSWORD>")
    amazon_session.login()

    amazon_orders = AmazonOrders(amazon_session)
    orders = amazon_orders.get_order_history(year=2023)

    for order in orders:
        print(f"{order.order_number} - {order.grand_total}")

Dive Deeper
===========

For more advanced usage, dive deeper in to the rest of the documentation.

.. toctree::
   :maxdepth: 2

   api
   troubleshooting

.. include:: ../CONTRIBUTING.rst
