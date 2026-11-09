===============
Troubleshooting
===============

Enable Debug Mode
-----------------

Enabling ``debug`` mode does a few main things:

1. Sets ``logger`` levels to ``DEBUG``
2. Sends ``logger`` output to ``stderr``, so you'll see it on the console when using the CLI
3. HTML pages will be saved locally

To enable ``debug`` mode in Python, you need to pass ``debug=True`` to
:class:`~amazonorders.session.AmazonSession`:

.. code-block:: python

    from amazonorders.session import AmazonSession
    from amazonorders.orders import AmazonOrders

    amazon_session = AmazonSession("<AMAZON_EMAIL>",
                                   "<AMAZON_PASSWORD>",
                                   debug=True)
    amazon_session.login()

    amazon_orders = AmazonOrders(amazon_session)
    orders = amazon_orders.get_orders()

To enable ``debug`` mode when using the CLI, pass the ``--debug`` flag, which works with any
command:

.. code-block:: shell

  amazon-orders --debug history

Integrating with Amazon.com via scraping is complicated and requires ``form`` data from the
website's HTML. Before submitting a bug report or requesting a new feature, try running
``amazon-orders`` one of the ways described above, and if any console output or generated HTML
files are relevant to the issue, attach them to your request.

.. _login-challenges:

Authentication
--------------

Sign-in, and the challenges Amazon may present during it, are handled by
|amazon-auth|_, which ``amazon-orders`` builds on. If you're having trouble
signing in, see its :doc:`troubleshooting <amazonauth:troubleshooting>`: :ref:`amazonauth:login-challenges` covers the
opt-in extras that handle Amazon's challenges, and it also covers what to do when sign-in reaches a page it doesn't
recognize. Sign-in bugs and pull requests belong in |amazon-auth|_'s
`issues <https://github.com/alexdlaird/amazon-auth/issues>`_.

Slow Parsing / Malformed Data
-----------------------------

By default, ``amazon-orders`` uses ``html.parser``, Python's `built-in HTML parser <https://docs.python.org/3/library/html.parser.html>`_.
There are some situations where this parser is not preferred, either because it is slower than other options, or in
some cases it leads to parsing issues, where fields like ``title``, ``currency``, etc. are populated with mangled data.
``amazon-orders`` should work with any `BeautifulSoup-compatible HTML parser <https://www.crummy.com/software/BeautifulSoup/bs4/doc/#installing-a-parser>`_,
and many prefer to use `lxml <https://pypi.org/project/lxml/>`_ instead. If another parser is installed, you can change
the parser ``amazon-orders`` will use by setting ``bs4_parser`` in the :class:`config <amazonorders.conf.AmazonOrdersConfig>`.

Concurrency Workers Exhausted
-----------------------------

If you see this or similar errors, you may need to tweak ``thread_pool_size`` in the :class:`config <amazonorders.conf.AmazonOrdersConfig>`. Increasing it is the
likely solution, but doing so may also have an effect on how many active URL connections to Amazon can be executed at
any given time, so adjusting both may be necessary. See also `URL Connection Pool Full`_.

URL Connection Pool Full
------------------------

.. code-block:: sh

    WARNING:requests.packages.urllib3.connectionpool:HttpConnectionPool
    is full, discarding connection:

If you see this or similar errors, you may need to tweak ``connection_pool_size`` in the
:class:`config <amazonorders.conf.AmazonOrdersConfig>`. Increasing it is
the likely solution, but the issue may also be linked to the number of async tasks being executed at a given time.
Adjusting one or both of these values up or down may be necessary to find the correct threshold. See also
`Concurrency Workers Exhausted`_.

Broken After Previously Working
-------------------------------

If you have successfully integrated with ``amazon-orders``, and an existing script or CLI
command stops working, a likely cause is that something changed on an associated Amazon.com page.
This could be that Amazon changed the layout of a page, renamed or refactored a field, or
something else.

To see what the affected page looks like, `enable debug mode`_, then rerun your code. Running in
``debug`` mode will save parsed HTML files locally for you so that you can inspect the DOM and compare it to
the parsing code within ``amazon-orders``. This may give you some insight in to what changed.
In ``amazon-orders``, look for code that uses `BeautifulSoup's CSS select() methods <https://www.crummy.com/software/BeautifulSoup/bs4/doc/#css-selectors-through-the-css-property>`_.

More advanced troubleshooting can be done by extending :class:`~amazonorders.selectors.Selectors`,
:class:`~amazonorders.constants.Constants`, and :class:`~amazonorders.transactions.TransactionsPage`, for instance to
try different CSS selectors for parsing a field. When these classes are extended, set ``selectors_class``,
``constants_class``, and ``transactions_page_class`` in the :class:`config <amazonorders.conf.AmazonOrdersConfig>` to provide override classes.

If you identify the issue, please `submit a bug report <https://github.com/alexdlaird/amazon-orders/issues/new?assignees=&labels=bug&projects=&template=bug-report.yml>`_.
If you're able to resolve the issue, please `also submit a PR <https://github.com/alexdlaird/amazon-orders/compare>`_
so others can benefit.

Found a Missing / Broken Field on an Entity
-------------------------------------------

If you find that a useful field on an entity (for instance, an :class:`~amazonorders.entity.order.Order` or an
:class:`~amazonorders.entity.item.Item`) is missing (or one that exists isn't being populated for you), consider
contributing it! Fields are populated by simple ``_parse()`` methods on the entity, and many fields are able to
utilize :class:`~amazonorders.entity.parsable.Parsable`'s :func:`~amazonorders.entity.parsable.Parsable.simple_parse`
function, which just needs a selector.

To tell a field that broke from one the page doesn't have, check the entity's
:attr:`~amazonorders.entity.parsable.Parsable.parse_failures`, which lists the fields that could not be parsed.

If you can't fetch the field's value with just a selector, implementing a new ``_parse()`` function on the
entity will give you a lot more flexibility.

Once you've implemented and tested the new field, `submit a PR <https://github.com/alexdlaird/amazon-orders/compare>`_!
