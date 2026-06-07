====================
Browser Automation
====================

Amazon sometimes presents JavaScript-based challenges during login that cannot be solved
by sending HTTP requests alone — the page requires a real browser to execute its scripts. The
``[browser]`` extra handles these challenges by running a headless browser and bridging the
resulting session back into ``amazon-orders``.

.. note::

    The ``[browser]`` extra handles JavaScript authentication challenges, not image Captchas. For legacy
    OCR-based image Captchas, see the ``[captcha]`` extra in :doc:`troubleshooting`. For the standalone
    AWS WAF JavaScript challenge (which can appear independently of an ACIC page), see :doc:`waf`.

Three challenge types are covered:

- **ACIC** (Amazon Challenge and Identity Component) — the ``#aa-challenge-page-captcha-container``
  challenge page. If an embedded WAF challenge is present inside the ACIC page, it can be solved
  automatically when a WAF solver extra is also configured, or handled manually (see below).
- **JS bot detection** — the ``"verify that you're not a robot / Enable JavaScript"`` page.
  :class:`~amazonorders.contrib.browser.playwright.PlaywrightJSAuthForm` is a best-effort handler
  for this; effectiveness depends on whether the challenge resolves in a real browser without a
  visual puzzle.
- **AWS WAF (manual)** (Web Application Firewall) — :class:`~amazonorders.contrib.browser.playwright.PlaywrightManualWafForm` opens a visible browser
  window for you to solve the challenge yourself, suitable when a display is available.

Installation
------------

Add the ``[browser]`` extra:

.. code-block:: shell

    pip install amazon-orders[browser]

Then install the Chromium browser binary:

.. code-block:: shell

    playwright install chromium

Configuration
-------------

Choosing a Browser
~~~~~~~~~~~~~~~~~~

``amazon-orders`` supports both Chromium (default) and Firefox user agents. Set ``browser``
in your ``~/.config/amazonorders/config.yml`` to switch:

.. code-block:: yaml

    browser: firefox

Or as an environment variable:

.. code-block:: shell

    export AMAZON_BROWSER=firefox

Or pass it inline when constructing :class:`~amazonorders.conf.AmazonOrdersConfig`:

.. code-block:: python

    from amazonorders.conf import AmazonOrdersConfig
    from amazonorders.session import AmazonSession

    config = AmazonOrdersConfig(data={"browser": "firefox"})
    session = AmazonSession(..., config=config)

Firefox is particularly useful on **ARM64 Linux**, where prebuilt Chromium binaries are
unavailable. When using Firefox, install the Firefox binary instead of Chromium:

.. code-block:: shell

    playwright install firefox

Registering Forms
~~~~~~~~~~~~~~~~~

Register one or both forms in your ``~/.config/amazonorders/config.yml``:

.. code-block:: yaml

    auth_forms_classes:
      - amazonorders.contrib.browser.playwright.PlaywrightAcicForm
      - amazonorders.contrib.browser.playwright.PlaywrightJSAuthForm

:class:`~amazonorders.contrib.browser.playwright.PlaywrightAcicForm` handles the ACIC challenge
page and should be registered first. :class:`~amazonorders.contrib.browser.playwright.PlaywrightJSAuthForm`
is the best-effort fallback for the pure JS bot-detection page, and should be registered after.

.. _manual-waf-solving:

Manual WAF Solving
------------------

:class:`~amazonorders.contrib.browser.playwright.PlaywrightManualWafForm` opens a **visible**
browser window, lets you solve the WAF challenge yourself, and automatically harvests the
resulting cookies once the browser navigates away from the challenge page.

Because it requires a display and a user at the keyboard, it is intended for local/interactive
use only — not headless servers or CI.

Register it in your ``~/.config/amazonorders/config.yml``:

.. code-block:: yaml

    auth_forms_classes:
      - amazonorders.contrib.browser.playwright.PlaywrightManualWafForm

It can be combined with other forms. For example, to handle both the ACIC challenge (headless)
and a standalone WAF challenge (manual):

.. code-block:: yaml

    auth_forms_classes:
      - amazonorders.contrib.browser.playwright.PlaywrightAcicForm
      - amazonorders.contrib.browser.playwright.PlaywrightManualWafForm

Combining with a WAF Solver
---------------------------

Amazon sometimes embeds a WAF challenge inside the ACIC challenge page. When this happens, the
headless browser alone cannot solve it. Two options are available:

- **Manual** — register ``PlaywrightManualWafForm`` alongside ``PlaywrightAcicForm``. A visible
  browser window opens for you to solve the embedded WAF challenge yourself. No WAF solver extra
  is required.

  .. code-block:: yaml

      auth_forms_classes:
        - amazonorders.contrib.browser.playwright.PlaywrightAcicForm
        - amazonorders.contrib.browser.playwright.PlaywrightManualWafForm

- **Automated** — register a :doc:`WAF solver extra <waf>` alongside ``PlaywrightAcicForm``.
  ``PlaywrightAcicForm`` will detect the embedded WAF challenge, delegate to the solver, and inject
  the resulting token before the challenge resolves — all without additional configuration.

  .. code-block:: yaml

      auth_forms_classes:
        - amazonorders.contrib.browser.playwright.PlaywrightAcicForm
        - amazonorders.contrib.waf.capsolver.CapSolverWafForm

  ``PlaywrightJSAuthForm`` is omitted here because ``CapSolverWafForm`` handles the JS bot-detection
  page on its own in this configuration.

If a supported extra isn't working for you, please
`open an issue <https://github.com/alexdlaird/amazon-orders/issues/new?assignees=&labels=bug&projects=&template=bug-report.yml>`_
or a `pull request <https://github.com/alexdlaird/amazon-orders/compare>`_.
