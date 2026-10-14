====================
Browser Automation
====================

Amazon sometimes presents JavaScript-based challenges during login that cannot be solved
by sending HTTP requests alone — the page requires a real browser to execute its scripts. The
``[browser]`` extra handles these challenges by running a headless browser and bridging the
resulting session back into ``amazon-orders``.

.. note::

    The ``[browser]`` extra also lets you sign in on Amazon's own page, see :ref:`Secure Sign-In <secure-sign-in>`.
    This page covers handling JavaScript authentication challenges, not image Captchas. For legacy OCR-based
    image Captchas, see the ``[captcha]`` extra in :doc:`troubleshooting`. For the standalone AWS WAF JavaScript
    challenge (which can appear independently of an ACIC page), see :doc:`waf`.

Three challenge types are covered:

- **ACIC** (Amazon Challenge and Identity Component) — the ``#aa-challenge-page-captcha-container``
  challenge page. Amazon may embed a WAF token challenge, a visual grid Puzzle (e.g. "Choose all the
  buckets"), or both. These can be solved automatically when a WAF solver extra is also configured,
  or handled manually (see below).
- **JS bot detection** — the ``"verify that you're not a robot / Enable JavaScript"`` page.
  :class:`~amazonorders.contrib.browser.playwright.PlaywrightJSAuthForm` is a best-effort handler
  for this; effectiveness depends on whether the challenge resolves in a real browser without a
  visual puzzle.
- **AWS WAF (manual)** (Web Application Firewall) — :class:`~amazonorders.contrib.browser.playwright.PlaywrightManualWafForm` opens a visible browser
  window for you to solve the challenge yourself, suitable when a display is available.

.. _browser-installation:

Installation
------------

Add the ``[browser]`` extra:

.. code-block:: shell

    pip install amazon-orders[browser]

Configuration
-------------

Choosing a Browser
~~~~~~~~~~~~~~~~~~

``amazon-orders`` uses Chrome by default, falling back to Playwright's Chromium if Chrome isn't installed. To
use a different browser, set ``browser`` in the :class:`config <amazonorders.conf.AmazonOrdersConfig>`.

Any browser `Playwright supports <https://playwright.dev/python/docs/browsers>`_ works, either one that's installed,
e.g. ``msedge``, or one Playwright installs, e.g. ``firefox``. For any other, set
``browser_executable_path`` to its path.

On **ARM64 Linux**, where Chrome and Playwright's Chromium are unavailable, use ``firefox``.

Registering Forms
~~~~~~~~~~~~~~~~~

Add one or both forms to ``auth_forms_classes`` in the :class:`config <amazonorders.conf.AmazonOrdersConfig>`, in
this order: ``amazonorders.contrib.browser.playwright.PlaywrightAcicForm``, then
``amazonorders.contrib.browser.playwright.PlaywrightJSAuthForm``.

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
use only — not headless environments.

Add ``amazonorders.contrib.browser.playwright.PlaywrightManualWafForm`` to ``auth_forms_classes`` in the
:class:`config <amazonorders.conf.AmazonOrdersConfig>`. It can be combined with other forms, for example after
``PlaywrightAcicForm`` to handle both the ACIC challenge (headless) and a standalone WAF challenge (manual).

Combining with a WAF Solver
---------------------------

Amazon sometimes embeds challenges inside the ACIC page — either a WAF token challenge, a visual
grid Puzzle (e.g. "Choose all the buckets"), or both. When this happens, the headless browser alone
cannot solve them. Two options are available:

- **Manual** — register ``PlaywrightManualWafForm`` alongside ``PlaywrightAcicForm``. The ACIC
  browser itself opens visibly and hands the embedded challenge — whether a WAF token challenge or
  a visual grid Puzzle — to you to solve yourself. No WAF solver extra is required.

- **Automated** — register a :doc:`WAF solver extra <waf>` alongside ``PlaywrightAcicForm``.
  ``PlaywrightAcicForm`` will detect and solve embedded challenges automatically — whether WAF
  token or Puzzle — all without additional configuration. ``PlaywrightJSAuthForm`` isn't needed here, since
  the WAF solver handles the JS bot-detection page on its own.

If a supported extra isn't working for you, please
`open an issue <https://github.com/alexdlaird/amazon-orders/issues/new?assignees=&labels=bug&projects=&template=bug-report.yml>`_
or a `pull request <https://github.com/alexdlaird/amazon-orders/compare>`_.
