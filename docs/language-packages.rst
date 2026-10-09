=================
Language Packages
=================

``amazon-orders`` implements English, along with international date and currency formats. Support for other
languages comes from separately published language packages. A language package can override the words, date and
currency formats, and Transactions page handling ``amazon-orders`` uses to parse Amazon's pages, all through the
config.

Other English Amazon sites don't need a language package: set the ``domain`` config option (or pass ``--domain`` on
the CLI). URLs, headers, the currency symbol, and sign-in values adjust for known domains, and anything else a site
needs can be overridden by subclassing :class:`~amazonorders.constants.Constants` and setting ``constants_class``.

.. note::

    Language packages are built, published, and maintained by their own authors, not in this repo. See
    `Getting Listed`_ to have yours added to these docs.

Available Language Packages
---------------------------

- None yet. Be the first! See `Building a Language Package`_ to get started.

Configuration
-------------

Install the language package, then set ``language_package`` in your ``~/.config/amazonorders/config.yml``:

.. code-block:: yaml

    language_package: my_language_package

Or set it from the command line:

.. code-block:: shell

    amazon-orders update-config language_package my_language_package

Or pass it inline when constructing :class:`~amazonorders.conf.AmazonOrdersConfig`:

.. code-block:: python

    from amazonorders.conf import AmazonOrdersConfig
    from amazonorders.session import AmazonSession

    config = AmazonOrdersConfig(data={"language_package": "my_language_package"})
    amazon_session = AmazonSession("<AMAZON_EMAIL>",
                                   "<AMAZON_PASSWORD>",
                                   config=config)

Set ``domain`` (or pass ``--domain``) to the Amazon site the language package targets.

For each class config option left at its default, ``amazon-orders`` uses the class of the same name from the
language package, if it defines one as a subclass of the default:

- ``constants_class`` uses ``Constants``
- ``selectors_class`` uses ``Selectors``
- ``transactions_page_class`` uses ``TransactionsPage``
- ``transaction_class`` uses ``Transaction``
- ``order_class`` uses ``Order``
- ``shipment_class`` uses ``Shipment``
- ``item_class`` uses ``Item``

Any ``*_class`` set in the config to something other than its default takes precedence over the language package. A
``*_class`` set to its default counts as not set, since saving the config writes out every default.

Building a Language Package
---------------------------

A language package is a Python package that subclasses the defaults and overrides only what differs. The classes
must be importable from the package itself, for instance in its ``__init__.py``:

.. code-block:: python

    from amazonorders import constants, selectors


    class Selectors(selectors.Selectors):
        FIELD_ITEM_SELLER_TEXT = "<SOLD_BY_TEXT>"
        FIELD_SELLER_NAME_PREFIX = "<SOLD_BY_TEXT>"
        FIELD_ORDER_GRAND_TOTAL_LABELS = ["<grand total label>"]
        FIELD_ORDER_SUBTOTAL_LABELS = ["<subtotal label>"]
        TRANSACTION_HISTORY_EMPTY_TEXT = "<no transactions text>"


    class Constants(constants.Constants):
        SIGNED_OUT_TEXT = "<SIGNED_OUT_TEXT>"

        def parse_date(self, value, fuzzy=False):
            # Parse the site's date format, e.g. month names in another language
            ...

Only define the classes your language package needs to change, since any it omits keep their defaults. For a
complete example, have a look at
`example_language_package.py <https://github.com/alexdlaird/amazon-orders/blob/main/tests/unit/example_language_package.py>`_,
which overrides every word and parse method below, and is tested against real pages with their English replaced by
placeholder text.

- **Words** — attributes on :class:`~amazonorders.selectors.Selectors`, alongside the selector each is used with
  (CSS selectors can be overridden here too, if the site's markup is different). The suffix of an attribute's name
  says how it's used:

    - ``_LABELS`` — lists matched, in order, against an Order's lowercase subtotal rows. A label is a substring
      of the row, or a compiled regex for a label that's also part of a longer one (e.g. ``re.compile(r"\btotal")``
      matches "total" but not "subtotal"). A row's text can start with whitespace, so anchor a regex with
      ``^\s*`` rather than ``^``
    - ``_PREFIX`` and ``_SUFFIX`` — split off the selected value
    - ``_TEXT`` — contained in the selected value (or, for an Order status shown on its own, equal to it)
    - ``_REGEX`` — extracts from the selected value, where a ``{count}`` placeholder matches a whole number

- **Formats** — methods on :class:`~amazonorders.constants.Constants`:
  :func:`~amazonorders.constants.Constants.parse_currency`, :func:`~amazonorders.constants.Constants.parse_date`,
  :func:`~amazonorders.constants.Constants.parse_count`, and
  :func:`~amazonorders.constants.Constants.parse_order_number`, and
  :func:`~amazonorders.constants.Constants.format_currency` for output. Currency and number parsing already accept
  either decimal mark, so only override these for formats the defaults can't parse (e.g. month names in another
  language).
- **Request headers** — set ``BASE_HEADERS`` on :class:`~amazonorders.constants.Constants`, for instance to ask for
  the site's language with ``Accept-Language``
  (``BASE_HEADERS = {**constants.Constants.BASE_HEADERS, "Accept-Language": "<LANGUAGE>"}``). A header set here isn't
  replaced by the ``browser`` option.
- **Transactions page** — if the site builds this page differently (for instance, rendering it from embedded data or
  loading more pages from an API), subclass :class:`~amazonorders.transactions.TransactionsPage` and override
  :func:`~amazonorders.transactions.TransactionsPage.get_page` and
  :func:`~amazonorders.transactions.TransactionsPage.parse_page`. For a page that renders its Transactions as data
  rather than HTML, build each with :func:`~amazonorders.entity.transaction.Transaction.from_fields`.
- **Entities** — :class:`~amazonorders.entity.order.Order`, :class:`~amazonorders.entity.shipment.Shipment`,
  :class:`~amazonorders.entity.item.Item`, and :class:`~amazonorders.entity.transaction.Transaction` can be subclassed
  for anything the above doesn't cover. Their ``_parse_*``
  methods are private, though, so an override of one isn't covered under `Compatibility`_.

Compatibility
-------------

Starting with ``amazon-orders`` 4.7.0, everything a language package relies on is kept stable:

- Attributes and methods on ``Selectors`` and ``Constants`` without a leading underscore
- ``TransactionsPage.get_page`` and ``TransactionsPage.parse_page``, and ``Transaction.from_fields``
- The ``language_package`` and ``*_class`` config options

These will only be renamed or removed in a major release. New ones may be added in any release, so set your
package's minimum version to the release that added the newest one you use, and cap it below the next major version
(e.g. ``amazon-orders>=4.7.0,<5``).

Testing
-------

- Test against real pages saved from that version of Amazon (anonymized), rather than generated ones. The parse
  methods work offline on saved HTML, so pass each a config with your ``language_package`` set:
  :func:`~amazonorders.orders.AmazonOrders.parse_order_history`,
  :func:`~amazonorders.orders.AmazonOrders.parse_order_details`, and
  :func:`~amazonorders.transactions.AmazonTransactions.parse_transactions`.
- Run a nightly integration test against the live site from your language package's own repo, with the account's
  credentials stored as secrets, so a change on Amazon's side is caught before your users find it. Start from the
  `integration.yml <https://github.com/alexdlaird/amazon-orders/blob/main/.github/workflows/integration.yml>`_
  workflow in ``amazon-orders``.

Getting Listed
--------------

Once your language package is published and its nightly run is passing,
`request a link <https://github.com/alexdlaird/amazon-orders/issues/new?template=new-language.yml>`_ and we'll add it
to `Available Language Packages`_. A listed package stays listed while it's maintained: its nightly run keeps passing,
and issues about it get a response. If its nightly run stays broken, or an issue goes unanswered, for more than 30
days, we'll pause the listing until it's back on track.

If something your language package needs to override isn't exposed, please
`open an issue <https://github.com/alexdlaird/amazon-orders/issues/new?assignees=&labels=enhancement&projects=&template=enhancement.yml>`_
or a `pull request <https://github.com/alexdlaird/amazon-orders/compare>`_.
