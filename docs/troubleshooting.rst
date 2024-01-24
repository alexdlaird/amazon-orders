===============
Troubleshooting
===============

Enabling Debug and Outputting HTML Files
----------------------------------------

``debug`` mode does a main things:

1. Sets ``logger`` levels to ``DEBUG``
2. Sends ``logger`` output to ``stderr`, so you'll see it on the console when using the CLI
3. Any HTML page parsed will also be output as a file

That last one is especially important for debugging issues.

To enable ``debug`` mode when using the CLI, simply pass the ``--debug`` flag, it works with any
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
website. Before submitting a bug report or requesting a new feature, you'll need to run
``amazon-orders`` one of the ways described above, and provide all console output along with any
relevant generated HTML files, otherwise it is not possible for us to work on your request.