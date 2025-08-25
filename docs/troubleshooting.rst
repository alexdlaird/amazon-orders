===============
Troubleshooting
===============

Enable Debug Mode
-----------------

Enabling ``debug`` mode does a few main things:

1. Sets ``logger`` levels to ``DEBUG``
2. Sends ``logger`` output to ``stderr``, so you'll see it on the console when using the CLI
3. HTML pages will be be saved locally

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
    orders = amazon_orders.get_order_history()

To enable ``debug`` mode when using the CLI, pass the ``--debug`` flag, which works with any
command:

.. code-block:: shell

  amazon-orders --debug history

Integrating with Amazon.com via scraping is complicated and requires ``form`` data from the
website's HTML. Before submitting a bug report or requesting a new feature, try running
``amazon-orders`` one of the ways described above, and if any console output or generated HTML
files are relevant to the issue, attach them to your request.

Captcha Blocking Login
----------------------

Captchas like `Amazon's puzzle-based WAF Captchas <https://docs.aws.amazon.com/waf/latest/developerguide/waf-captcha-puzzle-examples.html>`_
require JavaScript and block ``amazon-orders`` from being able to log in (see `issue #45 <https://github.com/alexdlaird/amazon-orders/issues/45>`_
for more details).

To attempt to fully automate login, you need to minimize how often (if at all) you are presented with Captcha
challenges. There is no perfect workaround to this, as when and how challenges are presented is at the discretion of
Amazon, but there are at least a few ways you can try to reduce the likelihood you will be presented with
Captcha challenges:

- Ensure credentials are correct. Too many failed login attempts in a short period of time increases the chances of
  being given a Captcha challenge. Persisting authentication in the config or the environment (see `docs <https://amazon-orders.readthedocs.io/api.html#amazonorders.session.AmazonSession.username>`_)
  can help ensure passwords are never entered incorrectly.
- Wait several hours (sometimes over a day is necessary) before trying again.
- Enable 2FA. One-time password (OTP) challenges during login can be auto-solved with :attr:`~amazonorders.session.AmazonSession.otp_secret_key`,
  and having this security measure enabled seems to reduce the frequency of Captcha challenges.
- Use a browser to manually solve the Captcha, as doing so may reduce the likelihood Amazon will continue to give you
  Captcha challenges from ``amazon-orders``.

    - In your browser, visit https://www.amazon.com/errors/validateCaptcha to solve a Captcha challenge while logged
      in to your account.

    - Logout of your account, then log back in. Amazon may present you with a different Captcha flow in this case,
      which may be the one that needs to be solved for them to stop prompting you.

    - Captcha challenges are more often presented to unknown devices. If possible, first manually login from a browser on
      the device on which you're using ``amazon-orders``.

Slow Parsing / Malformed Data
-----------------------------

By default, ``amazon-orders`` uses ``html.parser``, Python's `built-in HTML parser <https://docs.python.org/3/library/html.parser.html>`_.
There are some situations where this parsers is not preferred, either because it is slower than other options, or in
some cases it leads to parsing issues, where fields like ``title``, ``currency``, etc. are populated with mangled data.
``amazon-orders`` should work with any `BeautifulSoup-compatible HTML parser <https://www.crummy.com/software/BeautifulSoup/bs4/doc/#installing-a-parser>`_,
and many prefer to use `lxml <https://pypi.org/project/lxml/>`_ instead. If another parser is installed, you can change
the parser ``amazon-orders`` will use with ``AmazonOrdersConfig.bs4_parser``.

Concurrency Workers Exhausted
-----------------------------

If you see this or similar errors, you may need to tweak ``AmazonOrdersConfig.thread_pool_size``. Increasing it is the
likely solution, but doing so may also have an effect on how many active URL connections to Amazon can be executed at
any given time, so adjusting both may be necessary. See also `URL Connection Pool Full`_.

URL Connection Pool Full
------------------------

.. code-block:: sh

    WARNING:requests.packages.urllib3.connectionpool:HttpConnectionPool
    is full, discarding connection:

If you see this or similar errors, you may need to tweak ``AmazonOrdersConfig.connection_pool_size``. Increasing it is
the likely solution, but the issue may also be linked to the number of async tasks being executed at a given time.
Adjusting one or both of these values up or down may be necessary to find the correct threshold. See also
`Concurrency Workers Exhausted`_.

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
