.. rst-class:: hide-header

*************************************************************************************************
Amazon Orders - A Python library (and CLI) for Amazon order history, line items, and transactions
*************************************************************************************************

.. only:: html

   .. image:: _static/logo-light.png
      :alt: amazon-orders - A Python library (and CLI) for Amazon order history, line items, and transactions
      :align: center
      :width: 560px
      :class: hero-logo only-light

   .. image:: _static/logo-dark.png
      :alt: amazon-orders - A Python library (and CLI) for Amazon order history, line items, and transactions
      :align: center
      :width: 560px
      :class: hero-logo only-dark

.. only:: not html

   .. image:: _html/_images/logo.png
      :alt: amazon-orders - A Python library (and CLI) for Amazon order history, line items, and transactions
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

``amazon-orders`` is an unofficial library that provides a Python API (and CLI) for Amazon order history, line items, and transactions.

``amazon-orders`` core supports Amazon's English ``.com`` site, validated nightly. Other English Amazon sites can be
targeted with the ``domain`` config option, and other languages plug in through
:doc:`language packages <language-packages>`.

.. note::

    This package works by parsing data from Amazon's consumer-facing website. A periodic build validates
    functionality to ensure its stability, but as Amazon provides no official API to use, older versions of
    this package may break at any time, so it's recommended that you use the latest version.

Installation
============

``amazon-orders`` is available on
`PyPI <https://pypi.org/project/amazon-orders/>`__ and can be installed and/or upgraded
using ``pip``:

.. code:: sh

    pip install amazon-orders --upgrade

That's it! ``amazon-orders`` is now available as a package to your Python projects and from the command line.

If pinning, be sure to use a wildcard for the `minor version <https://semver.org/>`_ (e.g. ``==4.8.*``, not ``==4.8.0``)
to ensure you always get the latest stable release.

Basic Usage
===========

You'll use :class:`~amazonorders.session.AmazonSession` to authenticate your Amazon account, then
:class:`~amazonorders.orders.AmazonOrders`, :class:`~amazonorders.transactions.AmazonTransactions`, and
:class:`~amazonorders.gift_cards.AmazonGiftCards` to interact with account data.
:func:`~amazonorders.orders.AmazonOrders.get_order_history` and
:func:`~amazonorders.orders.AmazonOrders.get_order` are good places to start.

.. code:: python

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

If the fields you're looking for aren't populated with the above, set ``full_details=True`` (or pass ``--full-details``
to the ``history`` CLI command), since by default it is ``False`` (enabling it slows down querying, since an additional
request for each order is necessary). Have a look at the :class:`~amazonorders.entity.order.Order` entity's docs to see
what fields are only populated with full details.

Secure Sign-In
--------------

The most secure way to use ``amazon-orders`` is to sign in on Amazon's own page, in a browser window, so your password,
one-time passcode, and any challenge never reach ``amazon-orders``:

.. code:: sh

    amazon-orders login --browser

The session is persisted, so neither the CLI nor the Python API needs credentials:

.. code:: python

    from amazonorders.session import AmazonSession

    amazon_session = AmazonSession()
    amazon_session.login()

See :doc:`browser` for details.

Command Line Usage
------------------

You can also run any command available to the main Python interface from the command line:

.. code:: sh

    amazon-orders login
    amazon-orders history --year 2023
    amazon-orders history --last-30-days
    amazon-orders history --last-3-months

Output Formats
--------------

The ``history``, ``order``, ``transactions``, ``order-transactions``, and ``gift-card-activity`` commands accept
``--output``, which renders Orders, Transactions, and Gift Card activity as ``text`` (the default), ``json``,
``yaml``, or ``csv``. Progress messages are written to ``stderr``, so redirecting ``stdout`` captures only the data.

.. code:: sh

    amazon-orders history --year 2023 --output json > orders.json
    amazon-orders history --last-30-days --output csv > orders.csv

To serialize from Python instead, every entity has :func:`~amazonorders.entity.parsable.Parsable.to_dict`,
which converts it and its nested entities to a ``dict`` of primitives.

.. code:: python

    import json

    from amazonorders.orders import AmazonOrders

    amazon_orders = AmazonOrders(amazon_session)
    orders = amazon_orders.get_order_history(year=2023)

    # [{"order_number": "112-9685975-5907428", "grand_total": 35.98, ...}]
    print(json.dumps([order.to_dict() for order in orders], indent=2))

See :class:`~amazonorders.output.OutputFormatter` for each format's contract, and to override how
entities are rendered.

Automating Authentication
-------------------------

Authentication can be automated by (in order of precedence) storing credentials in environment variables, passing them
to :class:`~amazonorders.session.AmazonSession`, or storing them in :class:`~amazonorders.conf.AmazonOrdersConfig`. The
environment variables ``amazon-orders`` looks for are:

- ``AMAZON_USERNAME``
- ``AMAZON_PASSWORD``
- ``AMAZON_OTP_SECRET_KEY`` (see :attr:`~amazonorders.session.AmazonSession.otp_secret_key`)

To enable **WAF auto-solve** via a third-party integration, install with the relevant extra:

.. code:: sh

    pip install amazon-orders[capsolver]
    pip install amazon-orders[anticaptcha]
    pip install amazon-orders[2captcha]

See :doc:`waf` for details.

To enable **browser-based challenge handling** (ACIC and JavaScript bot-detection pages) via
a headless browser, install with the ``browser`` extra:

.. code:: sh

    pip install amazon-orders[browser]
    playwright install chromium

See :doc:`browser` for details.

For **legacy Captcha auto-solve** on Python <=3.12, install with ``captcha`` extra:

.. code:: sh

    pip install amazon-orders[captcha]

See :ref:`Login Challenges <login-challenges>` for details.

Languages and Regions
---------------------

``amazon-orders`` core supports the English ``.com`` site, validated nightly.

- **Other English sites** (e.g. ``amazon.ca``, ``amazon.co.uk``): set the ``domain`` config option.
- **Other languages**: install a language package and set ``language_package``. See :doc:`language-packages`.

.. _known-limitations:

Known Limitations
-----------------

- Amazon Business accounts are not supported
- Device not remembered for OTP
    - Amazon will sometimes re-prompt for OTP even when a device has been remembered.
    - The recommended workaround for this is persisting the :attr:`~amazonorders.session.AmazonSession.otp_secret_key`
      in the config or the environment so that re-prompts are auto-solved.
    - See `issue #55 <https://github.com/alexdlaird/amazon-orders/issues/55>`_ for more details.

Dive Deeper
===========

For more advanced usage, dive deeper in to the rest of the documentation.

.. toctree::
   :maxdepth: 2

   api
   waf
   browser
   language-packages
   troubleshooting

.. include:: ../CONTRIBUTING.rst
