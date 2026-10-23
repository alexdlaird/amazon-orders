=================
Language Packages
=================

``amazon-orders`` reads Amazon's pages in English. Many Amazon sites can serve their pages in English, whatever
language they default to, so support for a site comes in three tiers:

- **amazon.com** — validated by a nightly integration run against the live site.
- **Any other Amazon site that offers English** (e.g. amazon.co.uk, or amazon.de): no
  language package needed, just set ``domain`` in the :class:`config <amazonorders.conf.AmazonOrdersConfig>` (or pass ``--domain`` on the CLI). Supported on a
  best-effort basis.
- **Any Amazon site, in another language** (a site with no English pages, or e.g. amazon.com in Spanish): install a
  language package. A language package lets ``amazon-orders`` read a site's pages in that language, by overriding
  the words, date and number formats, and page handling it parses them with, all through the config. It's validated
  by its own maintainer's integration run.

.. _supported-sites:

Supported Sites
---------------

To check whether a site offers English, open its language selector. If English is listed, the site is in the
second tier above. If it isn't, reading it needs a language package.

Sites in English
~~~~~~~~~~~~~~~~

These sites are supported on a best-effort basis, alongside amazon.com. This list is generated from the region data
``amazon-orders`` reads from Amazon's own pages, so it matches the version of the docs you're reading:

.. supported-sites::

If a site that offers English isn't listed, or doesn't work with ``domain``, please `open an issue`_, ideally with an
anonymized page from the site attached, or see `Adding a Site`_.

Available Language Packages
~~~~~~~~~~~~~~~~~~~~~~~~~~~

- None yet. Be the first! See `Building a Language Package`_ to get started.

.. note::

    Language packages are built, published, and maintained by their own authors, not in this repo. See
    `Getting Listed`_ to have yours added to these docs.

Adding a Site
-------------

Which Amazon sites offer English, and how to request it, is generated from Amazon's own pages, so a new site that
offers English is supported in the next release without a pull request. The cookie that marks it signed in can't be
read that way, since Amazon only sets it on sign-in, so a pull request adding it, from someone who uses that site, is
welcome.

To improve a site's support, open a pull request to ``amazon-orders`` itself with tests using real pages from that site
(anonymized). English wording that differs from amazon.com (e.g. British labels like "Postage & Packing") belongs there,
so every user of that site gets it.

A language package is the place for anything else: reading a site in a language other than English, or a fuller
implementation of a site with its own integration run and releases.

A language package can also target an English site, to replace the best-effort support of ``amazon-orders`` with its
own, validated by its own integration run. Fixes for an English site's pages still belong in ``amazon-orders`` itself
(see `Adding a Site`_), so every user of that site gets them, whether or not they install the package.

A language package changes what ``amazon-orders`` can read, not what it says: the CLI, error messages, and logs of
``amazon-orders`` are always in English, whichever package is installed, and translating them isn't planned.

Configuration
-------------

Install the language package, then set ``language_package`` in the :class:`config <amazonorders.conf.AmazonOrdersConfig>`.

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

.. tip::

    Before translating, check whether the site offers its pages in English (see `Supported Sites`_). If it does, the
    site belongs in ``amazon-orders`` itself, so see `Adding a Site`_ instead.

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
- **Request cookies** — set ``REQUEST_COOKIES`` on :class:`~amazonorders.constants.Constants` to the cookie that
  picks the site's page language. On a site that offers English, ``amazon-orders`` sets that cookie to English unless
  ``REQUEST_COOKIES`` or ``Accept-Language`` is overridden, so a package reading another language there should set it
  to that language (e.g.
  ``REQUEST_COOKIES = {"lc-acbde": "de_DE"}`` on amazon.de, or ``{"lc-main": "es_US"}`` on amazon.com). These are sent
  with every request to the active domain, replacing any cookie of the same name Amazon set.
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

If you need to enforce a minimum version with your language package, also check the installed version when the
package is imported, since an older version ignores an attribute it doesn't have without any error (e.g.
``REQUEST_COOKIES`` before 4.8.1):

.. code-block:: python

    from amazonorders import __version__
    from amazonorders.exception import AmazonOrdersError

    MINIMUM_VERSION = (4, 8, 1)

    if tuple(int(part) for part in __version__.split(".")[:3]) < MINIMUM_VERSION:
        raise AmazonOrdersError(f"my_language_package requires amazon-orders>=4.8.1, but {__version__} is installed")

Testing
-------

- Test against real pages saved from that version of Amazon (anonymized), rather than generated ones. The parse
  methods work offline on saved HTML, so pass each a config with your ``language_package`` set:
  :func:`~amazonorders.orders.AmazonOrders.parse_orders`,
  :func:`~amazonorders.orders.AmazonOrders.parse_order_details`, and
  :func:`~amazonorders.transactions.AmazonTransactions.parse_transactions`.
- Run an integration test against the live site at least weekly from your language package's own repo, with the
  account's credentials stored as secrets, so a change on Amazon's side is caught before your users find it. Running
  it more often signs in more often, which makes Amazon more likely to challenge the login, so weekly is usually
  enough. Start from the
  `integration.yml <https://github.com/alexdlaird/amazon-orders/blob/main/.github/workflows/integration.yml>`_
  workflow in ``amazon-orders``. GitHub disables a public repo's scheduled workflows after 60 days without activity,
  so check that yours is still enabled if your repo goes quiet.

Getting Listed
--------------

Once your language package is published and its scheduled integration run is passing,
`request a link <https://github.com/alexdlaird/amazon-orders/issues/new?template=new-language.yml>`_ and we'll add it
to `Available Language Packages`_. A listed package stays listed while it's maintained: its integration run keeps
passing, and issues about it get a response. If its integration run stays broken, or an issue goes unanswered, for
more than 30 days, we'll pause the listing until it's back on track.

If something your language package needs to override isn't exposed, please `open an issue`_ or a
`pull request <https://github.com/alexdlaird/amazon-orders/compare>`_.

.. _open an issue: https://github.com/alexdlaird/amazon-orders/issues/new?assignees=&labels=enhancement&projects=&template=enhancement.yml
