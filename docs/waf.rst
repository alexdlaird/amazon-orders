======================
Solving WAF Challenges
======================

Amazon may present an `AWS WAF (Web Application Firewall) <https://docs.aws.amazon.com/waf/latest/developerguide/waf-captcha-puzzle-examples.html>`_
JavaScript challenge during login. ``amazon-orders`` ships built-in support for solving these via third-party
solver services as opt-in extras. Once one is configured, ``amazon-orders login`` clears the challenge
automatically.

.. note::

    For the legacy OCR-based image Captcha, see the ``[captcha]`` extra in :doc:`troubleshooting`. WAF
    challenges and image Captchas are distinct mechanisms — this page covers the JavaScript-based WAF
    flow only.

    Amazon's ACIC challenge (``/ax/aaut/verify/ap/challenge``) may embed a WAF token challenge, a
    visual grid Puzzle, or both inside its page. The :doc:`browser` extra handles the ACIC page
    automatically, and when a WAF solver extra is also configured it will solve any embedded
    challenges as part of the same flow without any additional configuration.

If a display is available and you prefer to handle the challenge interactively, the ``[browser]``
extra provides :class:`~amazonorders.contrib.browser.playwright.PlaywrightManualWafForm`, which
opens a **visible** browser window so you can solve the WAF challenge yourself. See :ref:`manual-waf-solving`
in :doc:`browser` for setup.

The supported API-based providers are:

- `CapSolver <https://capsolver.com>`_
- `Anti-Captcha <https://anti-captcha.com>`_
- `2Captcha <https://2captcha.com>`_

Each provider follows the same setup: add its extra, set its API key as an environment variable, and
register the form in your config.

CapSolver
---------

Add the ``[capsolver]`` extra:

.. code-block:: shell

    pip install amazon-orders[capsolver]

Set your API key as an environment variable (or via :class:`~amazonorders.conf.AmazonOrdersConfig`):

.. code-block:: shell

    export CAPSOLVER_API_KEY=your-capsolver-key

Register the form in your ``~/.config/amazonorders/config.yml``:

.. code-block:: yaml

    auth_forms_classes:
      - amazonorders.contrib.waf.capsolver.CapSolverWafForm

Now ``amazon-orders login`` will clear any AWS WAF challenge it encounters during authentication.

Anti-Captcha
------------

Add the ``[anticaptcha]`` extra:

.. code-block:: shell

    pip install amazon-orders[anticaptcha]

Set your API key as an environment variable (or via :class:`~amazonorders.conf.AmazonOrdersConfig`):

.. code-block:: shell

    export ANTICAPTCHA_API_KEY=your-anticaptcha-key

Register the form in your ``~/.config/amazonorders/config.yml``:

.. code-block:: yaml

    auth_forms_classes:
      - amazonorders.contrib.waf.anticaptcha.AntiCaptchaWafForm

2Captcha
--------

Add the ``[2captcha]`` extra:

.. code-block:: shell

    pip install amazon-orders[2captcha]

Set your API key as an environment variable (or via :class:`~amazonorders.conf.AmazonOrdersConfig`):

.. code-block:: shell

    export TWOCAPTCHA_API_KEY=your-2captcha-key

Register the form in your ``~/.config/amazonorders/config.yml``:

.. code-block:: yaml

    auth_forms_classes:
      - amazonorders.contrib.waf.twocaptcha.TwoCaptchaWafForm

Writing Your Own
----------------

The ``auth_forms_classes`` config option accepts any
:class:`~amazonorders.forms.AuthForm` subclass, so you can integrate any provider you like. Subclass
:class:`~amazonorders.contrib.waf.base.AwsWafForm` and implement
``_solve_token(url, goku, challenge_script) -> str`` to call the service of your choice and return the
resulting ``aws-waf-token`` cookie value:

.. code-block:: python

    from amazonorders.contrib.waf.base import AwsWafForm


    class MyCustomWafForm(AwsWafForm):
        API_KEY_ENV_VAR = "MY_PROVIDER_API_KEY"

        def _solve_token(self, url, goku, challenge_script):
            ...

To also support visual grid Puzzles, override ``_solve_visual_captcha(url, image_data, question)``
and return a list of zero-based grid cell indices that match the target object:

.. code-block:: python

        def _solve_visual_captcha(self, url, image_data, question):
            # image_data is a list of 9 base64-encoded PNG tile images
            # question is the target object (e.g. "the buckets")
            ...

Once registered in ``auth_forms_classes``, your form participates in the same auth chain as the built-in providers.

If a supported extra isn't working for you, please
`open an issue <https://github.com/alexdlaird/amazon-orders/issues/new?assignees=&labels=bug&projects=&template=bug-report.yml>`_
or a `pull request <https://github.com/alexdlaird/amazon-orders/compare>`_.
