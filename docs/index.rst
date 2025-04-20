.. rst-class:: hide-header

******************************************************************
Amazon Orders - A Python libray (and CLI) for Amazon order history
******************************************************************

.. image:: _html/logo.png
   :alt: amazon-orders - A Python libray (and CLI) for Amazon order history
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
   :target: https://amazon-orders.readthedocs.io
.. image:: https://img.shields.io/github/license/alexdlaird/amazon-orders
   :target: https://github.com/alexdlaird/amazon-orders

``amazon-orders`` is an unofficial library that provides a Python API (and CLI) for Amazon order history

This package works by parsing data from Amazon's consumer-facing website. A periodic build validates
functionality to ensure its stability, but as Amazon provides no official API to use, this package may
break at any time. Pin the `minor (not patch) version <https://semver.org/>`_ wildcard (ex. ``==3.2.*``,
not ``==3.2.18``) to ensure you always get the latest stable release.

This package only officially supports the English, ``.com`` version of Amazon.

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

Or to use ``amazon-orders`` programmatically, `get_order_history() <https://amazon-orders.readthedocs.io/api.html#amazonorders.orders.AmazonOrders.get_order_history>`_
and `get_order() <https://amazon-orders.readthedocs.io/api.html#amazonorders.orders.AmazonOrders.get_order>`_ are good
places to start:

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

If desired fields are populated as ``None``, set ``full_details=True`` (or pass ``--full-details`` to the ``history``
command), since by default it is ``False`` (it will slow down querying). Have a look at `the Order entity's docs <https://amazon-orders.readthedocs.io/api.html#amazonorders.entity.order.Order>`_
to see what fields are only populated with full details.

Automating Authentication
-------------------------

One of the simplest ways to automate authentication is to take advantage of some of the environment variables that
``amazon-orders`` looks for. These include:

- ``AMAZON_USERNAME`` - Amazon email address
- ``AMAZON_PASSWORD`` - Amazon password
- ``OTP_SECRET_KEY`` - The secret key Amazon provides when manually adding a 2FA authenticator app—setting this will auto-solve one-time password challenges

Dive Deeper
===========

For more advanced usage, dive deeper in to the rest of the documentation.

.. toctree::
   :maxdepth: 2

   api
   troubleshooting

.. include:: ../CONTRIBUTING.rst
