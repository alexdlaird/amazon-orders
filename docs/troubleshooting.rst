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
that uses `BeautifulSoups CSS select() methods <https://www.crummy.com/software/BeautifulSoup/bs4/doc/#css-selectors-through-the-css-property>`_.
Many selector strings used by ``amazon-orders``, including those in ``session.py`` and ``orders.py``,
are defined in variables at that top of the files and can be easily overriden.

If you identify the issue, please `submit a bug report <https://github.com/alexdlaird/amazon-orders-python/issues/new?assignees=&labels=bug&projects=&template=bug-report.yml>`_.
If you're able to resolve the issue, please `also submit a PR <https://github.com/alexdlaird/amazon-orders-python/compare>`_
so others can benefit.