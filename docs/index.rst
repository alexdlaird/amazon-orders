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
break at any time. Pin the `minor (not patch) version <https://semver.org/>`_ wildcard (ex. ``==4.0.*``,
not ``==4.0.0``) to ensure you always get the latest stable release.

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

Authentication can be automated by (in order of precedence) storing credentials in environment variables, passing them
to :class:`~amazonorders.session.AmazonSession`, or storing them :class:`~amazonorders.conf.AmazonOrdersConfig`. The
environment variables ``amazon-orders`` looks for are:

- ``AMAZON_USERNAME``
- ``AMAZON_PASSWORD``
- ``AMAZON_OTP_SECRET_KEY`` (see `docs for usage <https://amazon-orders.readthedocs.io/api.html#amazonorders.session.AmazonSession.otp_secret_key>`_)

Known Limitations
-----------------

- Non-English, non-``.com`` versions of Amazon are unsupported
    - Some have reported success with some non-``.com`` sites (ex. ``amazon.ca`` in Canada), so other similar
      English-based versions of Amazon may work by chance. However, we do not run nightly regressions against
      other versions of the site, and as such do not say they are officially supported.
    - If you fork the repo, override ``AMAZON_BASE_URL`` with an English, non-``.com`` version of the site, and use
      your own credentials with the ``integration.yml`` workflow to setup a nightly regression run, please
      `contact us <mailto:contact@alexlaird.com>`_ and we will start mentioning support for that version of the site.
    - See `issue #15 <https://github.com/alexdlaird/amazon-orders/issues/15>`_ for more details.
- Some Puzzle CAPTCHAs are unsupported
    - While some CAPTCHAs can be auto-solved, and static image-based ones will be opened so the user can solve them
      manually, interactive CAPTCHAs—like Amazon's new puzzle-based CAPTCHAs—will block ``amazon-orders`` from being
      able to login.
    - See `issue #45 <https://github.com/alexdlaird/amazon-orders/issues/45>`_ for more details.

Dive Deeper
===========

For more advanced usage, dive deeper in to the rest of the documentation.

.. toctree::
   :maxdepth: 2

   api
   troubleshooting

.. include:: ../CONTRIBUTING.rst
