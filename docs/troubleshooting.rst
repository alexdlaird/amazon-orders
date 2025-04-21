===============
Troubleshooting
===============

Enable Debug Mode
-----------------

``debug`` mode does a few main things:

1. Sets ``logger`` levels to ``DEBUG``
2. Sends ``logger`` output to ``stderr``, so you'll see it on the console when using the CLI
3. Any HTML page parsed will also be be saved locally

To enable ``debug`` mode when using the CLI, simply pass the ``--debug`` flag, which works with any
command:

.. code-block:: shell

  amazon-orders --debug history

To enable ``debug`` mode through a Python script, you need to pass ``debug=True`` to
:class:`~amazonorders.session.AmazonSession`:

.. code-block:: python

    from amazonorders.session import AmazonSession
    from amazonorders.orders import AmazonOrders

    amazon_session = AmazonSession("<AMAZON_EMAIL>",
                                   "<AMAZON_PASSWORD>",
                                   debug=True)
    amazon_session.login()

    amazon_orders = AmazonOrders(amazon_session)
    orders = amazon_orders.get_order_history()

Integrating with Amazon.com via scraping is complicated and requires ``form`` data from the
website's HTML. Before submitting a bug report or requesting a new feature, try running
``amazon-orders`` one of the ways described above, and if any console output or generated HTML
files are relevant to the issue, attach them to your request.

Broken After Previously Working
-------------------------------

If you have successfully integrated with ``amazon-orders``, and an existing script or CLI
command stops working, a likely cause is that something changed on an associated Amazon.com page.
This could be that Amazon changed the layout of a page, renamed or refactored a field, or
something else.

To see what the effected page looks like, `enable debug mode`_, then rerun your code. Running in
``debug`` mode will save parsed HTML files locally for you so that you can inspect the DOM and compare it to
the parsing code within ``amazon-orders``. This may give you some insight in to what changed.
In ``amazon-orders``, look for code that uses `BeautifulSoup's CSS select() methods <https://www.crummy.com/software/BeautifulSoup/bs4/doc/#css-selectors-through-the-css-property>`_.

More advanced troubleshooting can be done by extending :class:`~amazonorders.selectors.Selectors` and
:class:`~amazonorders.constants.Constants`, for instance to try different CSS selectors for parsing a field. When these
classes are extended, use ``AmazonOrdersConfig.selectors_class`` and  ``AmazonOrdersConfig.constants_class`` to provide
override classes.

If you identify the issue, please `submit a bug report <https://github.com/alexdlaird/amazon-orders/issues/new?assignees=&labels=bug&projects=&template=bug-report.yml>`_.
If you're able to resolve the issue, please `also submit a PR <https://github.com/alexdlaird/amazon-orders/compare>`_
so others can benefit.

Found an Unknown Page in Auth Flow
----------------------------------

If you get an error during :func:`~amazonorders.session.AmazonSession.login()` saying you've encountered an unknown
page, you've found a page in the login flow that we haven't. Amazon has many different routes through
authentication, and is always adding more, so this is bound to happen. Hopefully you'll consider implementing the
solution to this auth flow and contributing it back to the repo.

Auth forms are actually relatively simple to implement. To get started investigating, `enable debug mode`_, then try
to login again. With ``debug`` mode enabled, the new page will be saved locally as an HTML file that you can open
and inspect.

Have a look at the HTML source of the new page, specifically the ``<form>`` tag, and look in ``forms.py`` to see how
other auth forms are implemented. You'll need to create a new class that inherits from
:class:`~amazonorders.forms.AuthForm`, override :func:`~amazonorders.forms.AuthForm.fill_form`, and manually pass
a list to :func:`~amazonorders.session.AmazonSession.auth_forms` that includes the new form.

Once you've implemented and tested the new form, `submit a PR <https://github.com/alexdlaird/amazon-orders/compare>`_
for maximum karma!

Found a Missing / Broken Field on an Entity
-------------------------------------------

If you find that a useful field on an entity (for instance, an :class:`~amazonorders.entity.order.Order` or an
:class:`~amazonorders.entity.item.Item`) is missing (or one that exists isn't being populated for you), consider
contributing it! Fields are populated by simple ``_parse()`` methods on the entity, and many fields are able to
utilize :class:`~amazonorders.entity.parsable.Parsable`'s :func:`~amazonorders.entity.parsable.Parsable.simple_parse`
function, which just needs a selector.

If you can't fetch the field's value with just a selector, implementing a new ``_parse()`` function on the
entity will give you a lot more flexibility.

Once you've implemented and tested the new field, `submit a PR <https://github.com/alexdlaird/amazon-orders/compare>`_!
