=================
API Documentation
=================

This part of the documentation covers the interfaces used to develop with ``amazon-orders``.

Main Interface
--------------

.. automodule:: amazonorders.orders
    :members:
    :private-members:
    :undoc-members:
    :show-inheritance:

.. automodule:: amazonorders.prime
    :members:
    :private-members:
    :undoc-members:
    :show-inheritance:

.. automodule:: amazonorders.transactions
    :members:
    :private-members:
    :undoc-members:
    :show-inheritance:

.. automodule:: amazonorders.gift_cards
    :members:
    :private-members:
    :undoc-members:
    :show-inheritance:

.. automodule:: amazonorders.paging
    :members:
    :private-members:
    :undoc-members:
    :show-inheritance:

Session Management
------------------

.. automodule:: amazonorders.session
    :members:
    :imported-members:
    :inherited-members:
    :private-members:
    :undoc-members:
    :show-inheritance:

.. automodule:: amazonorders.forms
    :members:
    :private-members:
    :undoc-members:
    :show-inheritance:

Challenge Solvers
-----------------

.. automodule:: amazonorders.contrib.waf.base
    :members:
    :private-members:
    :undoc-members:
    :show-inheritance:

.. automodule:: amazonorders.contrib.waf.capsolver
    :members:
    :private-members:
    :undoc-members:
    :show-inheritance:

.. automodule:: amazonorders.contrib.waf.anticaptcha
    :members:
    :private-members:
    :undoc-members:
    :show-inheritance:

.. automodule:: amazonorders.contrib.waf.twocaptcha
    :members:
    :private-members:
    :undoc-members:
    :show-inheritance:

.. automodule:: amazonorders.contrib.browser.playwright
    :members:
    :private-members:
    :undoc-members:
    :show-inheritance:

Configuration
-------------
.. automodule:: amazonorders.conf
    :members:
    :imported-members:
    :inherited-members:
    :private-members:
    :undoc-members:
    :show-inheritance:

.. py:data:: DEFAULT_COOKIE_JAR_SITE
    :module: amazonorders.conf
    :value: 'amazon.com'

    The Amazon site whose session is kept in the default ``cookie_jar_path`` itself, rather than in a jar of its own.

.. automodule:: amazonorders.constants
    :members:
    :inherited-members:
    :private-members:
    :undoc-members:
    :show-inheritance:

.. automodule:: amazonorders.output
    :members:
    :private-members:
    :undoc-members:
    :show-inheritance:

.. automodule:: amazonorders.selectors
    :members:
    :imported-members:
    :inherited-members:
    :private-members:
    :undoc-members:
    :show-inheritance:

Entities
--------

.. automodule:: amazonorders.entity.parsable
    :members:
    :private-members:
    :undoc-members:
    :show-inheritance:

.. automodule:: amazonorders.entity.family_member
    :members:
    :private-members:
    :undoc-members:
    :show-inheritance:

.. automodule:: amazonorders.entity.item
    :members:
    :private-members:
    :undoc-members:
    :show-inheritance:

.. automodule:: amazonorders.entity.invoice
    :members:
    :private-members:
    :undoc-members:
    :show-inheritance:

.. automodule:: amazonorders.entity.order
    :members:
    :private-members:
    :undoc-members:
    :show-inheritance:

.. automodule:: amazonorders.entity.order_search_result
    :members:
    :private-members:
    :undoc-members:
    :show-inheritance:

.. automodule:: amazonorders.entity.prime_payment
    :members:
    :private-members:
    :undoc-members:
    :show-inheritance:

.. automodule:: amazonorders.entity.recipient
    :members:
    :private-members:
    :undoc-members:
    :show-inheritance:

.. automodule:: amazonorders.entity.seller
    :members:
    :private-members:
    :undoc-members:
    :show-inheritance:

.. automodule:: amazonorders.entity.shipment
    :members:
    :private-members:
    :undoc-members:
    :show-inheritance:

.. automodule:: amazonorders.entity.tracking
    :members:
    :private-members:
    :undoc-members:
    :show-inheritance:

.. automodule:: amazonorders.entity.transaction
    :members:
    :private-members:
    :undoc-members:
    :show-inheritance:

.. automodule:: amazonorders.entity.gift_card_activity
    :members:
    :private-members:
    :undoc-members:
    :show-inheritance:

Exceptions
----------

.. automodule:: amazonorders.exception
    :members:
    :ignore-module-all:
    :private-members:
    :undoc-members:
    :show-inheritance:

.. py:exception:: AmazonOrdersError(error, meta=None)
    :module: amazonorders.exception
    :canonical: amazonauth.exception.AmazonAuthError

    Bases: Exception

    Raised when a general ``amazon-orders`` error has occurred.

    .. py:attribute:: meta
        :type: Optional[Dict[str, Any]]

        Metadata for context around the error was raised.

.. py:exception:: AmazonOrdersAuthError(error, meta=None)
    :module: amazonorders.exception
    :canonical: amazonauth.exception.AmazonAuthSignInError

    Bases: :exc:`AmazonOrdersError`

    Raised when an ``amazon-orders`` authentication error has occurred.

.. py:exception:: AmazonOrdersAuthRedirectError(error, meta=None)
    :module: amazonorders.exception
    :canonical: amazonauth.exception.AmazonAuthRedirectError

    Bases: :exc:`AmazonOrdersAuthError`

    Raised when an ``amazon-orders`` session that was previously authenticated redirects to login, indicating the
    likely need to reauthenticate.

.. py:exception:: AmazonOrdersWafSolverError(error, meta=None)
    :module: amazonorders.exception
    :canonical: amazonauth.exception.AmazonAuthWafSolverError

    Bases: :exc:`AmazonOrdersError`

    Raised when a third-party WAF solver fails (e.g. its balance ran out, its API key was rejected, or the service
    is down), rather than Amazon rejecting a solved challenge. ``meta["provider"]`` is the solver's name, and
    ``meta["provider_error"]`` is the error it gave.

.. py:exception:: AmazonOrdersBrowserNotInstalledError(error, meta=None)
    :module: amazonorders.exception
    :canonical: amazonauth.exception.AmazonAuthBrowserNotInstalledError

    Bases: :exc:`AmazonOrdersError`

    Raised when no browser is installed to sign in with. ``meta["browser_types"]`` lists the Playwright browser types
    that can be installed in its place, the default first.

Utility Functions
-----------------

.. automodule:: amazonorders.util
    :members:
    :ignore-module-all:
    :private-members:
    :undoc-members:
    :show-inheritance:

.. autoclass:: amazonorders.util.AmazonSessionResponse
    :members:
    :undoc-members:
    :show-inheritance:

.. autofunction:: amazonorders.util.cleanup_html_text

.. autofunction:: amazonorders.util.has_display

.. autofunction:: amazonorders.util.load_class

.. autofunction:: amazonorders.util.select

.. autofunction:: amazonorders.util.select_one
