===============
Troubleshooting
===============

Enable Debug Mode
-----------------

``debug`` mode does a few main things:

1. Sets ``logger`` levels to ``DEBUG``
2. Sends ``logger`` output to ``stderr``, so you'll see it on the console when using the CLI
3. Any HTML page parsed will also be output as a file

To enable ``debug`` mode when using the CLI, simply pass the ``--debug`` flag, which works with any
command:

.. code-block:: shell

  amazon-orders --debug history

To enable ``debug`` mode through a Python script, you need to pass ``debug=True`` to every
``amazonorders`` class you instantiate:

.. code-block:: python

    from amazonorders.session import AmazonSession
    from amazonorders.orders import AmazonOrders

    amazon_session = AmazonSession("<AMAZON_EMAIL>",
                                   "<AMAZON_PASSWORD>",
                                   debug=True)
    amazon_session.login()

    amazon_orders = AmazonOrders(amazon_session,
                                 debug=True)
    orders = amazon_orders.get_order_history()

Integrating with Amazon.com via scraping is complicated and requires ``form`` data from the
website. Before submitting a bug report or requesting a new feature, try running
``amazon-orders`` one of the ways described above, and if any console output or generated HTML
files are relevant to the issue, attach them to your request.

Broken After Previously Working
-------------------------------

If you have successfully integrated with ``amazon-orders`` and an existing script, app, or CLI
command stops working, a likely cause is that something changed on an associated Amazon.com page.
This could be that Amazon changed the layout of a page, renamed or refactored a field, or
something else.

To see what the effected page looks like, `enable debug mode`_, then rerun your code. Opening the
various HTML pages debug mode generates to inspect fields and compare that to the parsing code within
``amazon-orders`` may give you some insight in to what changed—in ``amazon-orders``, look for code
that uses `BeautifulSoup's CSS select() methods <https://www.crummy.com/software/BeautifulSoup/bs4/doc/#css-selectors-through-the-css-property>`_.
Many selector strings used by ``amazon-orders`` are defined in variables in ``constants.py`` and can be
easily overriden.

If you identify the issue, please `submit a bug report <https://github.com/alexdlaird/amazon-orders-python/issues/new?assignees=&labels=bug&projects=&template=bug-report.yml>`_.
If you're able to resolve the issue, please `also submit a PR <https://github.com/alexdlaird/amazon-orders-python/compare>`_
so others can benefit.

Found a New Auth Flow
---------------------

If you find an auth flow that isn't yet implemented, it's because we haven't encountered it. Amazon has many different
routes through authentication, and is always adding more, so we hope you'll consider implementing the new page you
found and contributing it back to the repo. Auth forms are actually relatively simple to implement.

1. `Enable debug mode`_. Then rerun your code so you encounter the new auth page again.
   Since ``debug`` mode is enabled, the page will be output locally as an HTML file for you. Open the source of the
   page, and find the ``<form>``.
2. Have a look at the other forms in ``forms.py``. Create a new class that inherits from :class:`~amazonorders.forms.AuthForm`.
   Most likely you'll only need to override the :func:`~amazonorders.forms.AuthForm.fill_form` in your new class.
3. Add your newly implemented form to the ``AUTH_FORMS`` list in ``session.py``.
4. Put the HTML for your new auth page in ``tests/resources`` (generify sensitive data, if any, first), then in
   ``test_session.py`` implement a test that covers your new auth flow.

With all of the above complete, fork the repo and commit your changes, then `submit a PR <https://github.com/alexdlaird/amazon-orders-python/compare>`_
for maximum karma!

Found a Missing Field on an Entity
----------------------------------

If you find a field on an entity has not yet been implemented, please contribute it! Entity fields are represented
pretty simply, just by a ``_parse()`` method on the entity. For example, let's say the ``quantity`` field on an :class:`~amazonorders.entity.item.Item`
was missing.

Identify the best DOM selector for fecthing this field, then implement that in a new ``_parse()`` method:

.. code-block:: python

    def _parse_quantity(self) -> Optional[int]:
        tag = self.parsed.select_one("span.item-view-qty")
        if tag:
            return int(tag.text.strip())
        else:
            return None

Then in ``Item.__init__()`` you would need to populate the new field with its parse method:

.. code-block:: python

    def __init__(self,
                 parsed: Tag) -> None:
        # Previous code ...
        self.quantity = self.safe_parse(self._parse_quantity)

Note that :func:`~amazonorders.entity.parsable.Parsable.safe_parse` is helper method that makes sure we don't break anything, so if perhaps the field is not
always present, a ``logger`` warning would be thrown when the parsing fails, but the newly added field wouldn't break
anyone's existing code.

Put a HTML that has this field in ``tests/resources`` (generify sensitive data, if any, first) and write a test that
populates it (see ``test_orders.py`` for similar examples). Note that ``make test`` must still pass, all changes
must be `additive`, because any previous iteration of page parsing may still be live for someone else's account.

With all of the above complete, fork the repo and commit your changes, then `submit a PR <https://github.com/alexdlaird/amazon-orders-python/compare>`_
for maximum karma!