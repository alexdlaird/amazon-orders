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
- **JS bot detection** — the ``"verify that you're not a robot / Enable JavaScript"`` page, and Akamai Bot
  Manager's interstitial, a blank page that verifies the browser and then reloads, which Amazon sometimes serves in
  place of a page. :class:`~amazonorders.contrib.browser.playwright.PlaywrightJSAuthForm` is a best-effort handler
  for these; effectiveness depends on whether the challenge resolves in a real browser without a
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

``amazon-orders`` uses Chrome by default, then Edge if Chrome isn't installed, then Playwright's Chromium if
neither is. To use a different browser, set ``browser`` in the :class:`config <amazonorders.conf.AmazonOrdersConfig>`.

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
is the best-effort fallback for the pure JS bot-detection page and Akamai's interstitial, and should be registered
after.

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

.. _remote-sign-in:

Signing In From Another Device
------------------------------

:ref:`Secure Sign-In <secure-sign-in>` opens a browser window, so it needs a display. On a machine without one, like a
server or a container, sign in from a browser on another device, like your phone, instead:

.. code-block:: shell

    amazon-orders login --remote

This prints a one-time link. The page it opens shows Amazon's sign-in page, from a browser running headless on the
machine, and passes your clicks, taps, scrolling and typing on to it, so you sign in on Amazon's own page, with a
one-time passcode if Amazon asks for one. Once you're signed in, the session is persisted as with ``login --browser``.

- The link works once, for 10 minutes (``remote_login_timeout``, in seconds). Any browser can show its page, but the
  first one to click or type on it is the only one that can use it from then on, so a link scanner that opens it
  doesn't use it up.
- What you type passes through the machine on its way to Amazon's page, and ``amazon-orders`` keeps and logs none of
  it. Open the link over HTTPS, or through ``localhost``, e.g. an SSH tunnel.
- The browser can only reach Amazon's hosts, so it loads nothing but Amazon's pages and what they need, even through
  a redirect, and it opens no other windows. Behind a proxy (``HTTPS_PROXY``), the proxy looks up the hosts it
  connects to, so it's the proxy that keeps redirects off your network.
- Passkeys can't be used from another device: sign in with your password. On a phone, the page's Paste button pastes
  it from a password manager.
- It needs a Chromium-based browser (see Choosing a Browser, above). On ARM64 Linux, install
  your distribution's Chromium and set ``browser_executable_path`` to it.

The page is served on ``127.0.0.1:8765`` while the sign-in runs, and the link is ``http://localhost:8765/<secret>``.
To open it from another device, forward the port, e.g. with ``ssh -L 8765:127.0.0.1:8765 <machine>`` from that
device, or serve it elsewhere with these :class:`config <amazonorders.conf.AmazonOrdersConfig>` values:

- ``remote_login_host`` and ``remote_login_port``: the address to listen on. In a container, listen on ``0.0.0.0``
  and publish the port to a single address, e.g. ``-p 127.0.0.1:8765:8765``.
- ``remote_login_url``: the address the link starts with, e.g. ``https://example.com/amazon-sign-in/`` behind a
  reverse proxy, which may serve the page under any path.

For instance, in a container:

.. code-block:: shell

    docker run -it --rm -p 127.0.0.1:8765:8765 -e AMAZON_REMOTE_LOGIN_HOST=0.0.0.0 \
        -v amazon-orders:/root/.config/amazonorders <image> amazon-orders login --remote

From Python, :class:`~amazonorders.contrib.browser.remote.PlaywrightRemoteLogin` does the same. Give it a
:class:`~amazonorders.contrib.browser.remote.RemoteLoginServer` to serve several sign-ins from one long-running
server, e.g. for each Amazon site:

.. code-block:: python

    from amazonorders.contrib.browser.remote import PlaywrightRemoteLogin, RemoteLoginServer
    from amazonorders.session import AmazonSession

    server = RemoteLoginServer(host="0.0.0.0", url="https://example.com/amazon-sign-in/")
    server.start()

    remote_login = PlaywrightRemoteLogin(AmazonSession(), server=server)
    print(remote_login.url)  # Give this to the person signing in
    remote_login.login()  # Blocks until they've signed in, or the sign-in ends

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
  token or Puzzle — all without additional configuration. ``PlaywrightJSAuthForm`` is only needed here for
  Akamai's interstitial, since the WAF solver handles the JS bot-detection page on its own.

If a supported extra isn't working for you, please
`open an issue <https://github.com/alexdlaird/amazon-orders/issues/new?assignees=&labels=bug&projects=&template=bug-report.yml>`_
or a `pull request <https://github.com/alexdlaird/amazon-orders/compare>`_.
