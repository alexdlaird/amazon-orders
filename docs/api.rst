=================
API Documentation
=================

This part of the documentation covers the interfaces used to develop with ``amazon-orders``.

Main Interface
--------------

.. automodule:: amazonorders.orders
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: amazonorders.prime
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: amazonorders.transactions
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: amazonorders.gift_cards
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: amazonorders.paging
    :members:
    :undoc-members:
    :show-inheritance:

Session Management
------------------

Sign-in is |amazon-auth|_'s. :class:`~amazonorders.session.AmazonSession` is its session, building an
:class:`~amazonorders.conf.AmazonOrdersConfig` when no ``config`` is given (see :doc:`amazonauth:api`).

.. automodule:: amazonorders.session
    :members:
    :imported-members:
    :inherited-members:
    :undoc-members:
    :show-inheritance:


Configuration
-------------
.. automodule:: amazonorders.conf
    :members:
    :imported-members:
    :inherited-members:
    :undoc-members:
    :show-inheritance:

.. py:data:: DEFAULT_COOKIE_JAR_SITE
    :module: amazonorders.conf
    :value: 'amazon.com'

    The Amazon site whose session is kept in the default ``cookie_jar_path`` itself, rather than in a jar of its own.

.. automodule:: amazonorders.constants
    :members:
    :inherited-members:
    :undoc-members:
    :show-inheritance:

.. automodule:: amazonorders.output
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: amazonorders.selectors
    :members:
    :imported-members:
    :inherited-members:
    :undoc-members:
    :show-inheritance:

Entities
--------

.. automodule:: amazonorders.entity.parsable
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: amazonorders.entity.family_member
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: amazonorders.entity.item
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: amazonorders.entity.invoice
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: amazonorders.entity.order
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: amazonorders.entity.order_search_result
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: amazonorders.entity.prime_payment
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: amazonorders.entity.recipient
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: amazonorders.entity.seller
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: amazonorders.entity.shipment
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: amazonorders.entity.tracking
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: amazonorders.entity.transaction
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: amazonorders.entity.gift_card_activity
    :members:
    :undoc-members:
    :show-inheritance:

Exceptions
----------

.. automodule:: amazonorders.exception
    :members:
    :ignore-module-all:
    :undoc-members:
    :show-inheritance:

.. py:exception:: AmazonOrdersError(error, meta=None)
    :module: amazonorders.exception
    :canonical: amazonauth.exception.AmazonAuthError

    Bases: Exception

    Raised when a general ``amazon-orders`` error has occurred.

    .. py:attribute:: meta
        :type: Optional[Dict[str, Any]]

        Metadata for context around the error that was raised.

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

.. py:exception:: AmazonOrdersChallengeUnsolvedError(error, meta=None)
    :module: amazonorders.exception
    :canonical: amazonauth.exception.AmazonAuthChallengeUnsolvedError

    Bases: :exc:`AmazonOrdersError`

    Raised when a sign-in challenge form can't handle the challenge it was given (e.g. a solver without its API key,
    or one that opens a browser window without a display), so the next form registered for the challenge is tried.
    If none can, the error is raised.

.. py:exception:: AmazonOrdersWafSolverError(error, meta=None)
    :module: amazonorders.exception
    :canonical: amazonauth.exception.AmazonAuthWafSolverError

    Bases: :exc:`AmazonOrdersChallengeUnsolvedError`

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
    :undoc-members:
    :show-inheritance:

