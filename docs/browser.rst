====================
Browser Automation
====================

Amazon sometimes presents JavaScript-based challenges during sign-in that can't be solved by sending HTTP requests
alone. The ``browser`` extra handles these with a browser, and also lets you sign in on Amazon's own page (see
:ref:`Secure Sign-In <secure-sign-in>`).

Browser automation is part of `amazon-auth <https://amazon-auth.readthedocs.io>`_, the authentication package
``amazon-orders`` is built on. This page covers getting started from ``amazon-orders``; :doc:`amazonauth:browser` in
its docs covers each challenge, choosing a browser, and customizing the sign-in.

.. _browser-installation:

Installation
------------

Add the ``browser`` extra:

.. code-block:: shell

    pip install amazon-orders[browser]

``amazon-orders`` uses Chrome by default, then Edge if Chrome isn't installed, then Playwright's Chromium if neither
is. To use another browser, set ``browser`` in the :class:`config <amazonorders.conf.AmazonOrdersConfig>` (see
:doc:`amazonauth:browser`).

Handling Challenges
-------------------

To have challenges handled with a headless browser, add the browser forms to ``auth_forms_classes`` in the
:class:`config <amazonorders.conf.AmazonOrdersConfig>` (``~/.config/amazonorders/config.yml``), in this order:

.. code-block:: yaml

    auth_forms_classes:
      - amazonauth.contrib.browser.playwright.PlaywrightAcicForm
      - amazonauth.contrib.browser.playwright.PlaywrightJSAuthForm

``PlaywrightAcicForm`` handles Amazon's ACIC challenge page, and ``PlaywrightJSAuthForm`` its JavaScript bot-detection
page. To solve an AWS WAF challenge yourself in a visible browser window instead of with a :doc:`WAF solver <waf>`,
also add ``amazonauth.contrib.browser.playwright.PlaywrightManualWafForm`` (see :ref:`amazonauth:manual-waf-solving`).
