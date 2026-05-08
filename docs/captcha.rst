=======================
Solving Captcha and WAF
=======================

Amazon may present an `AWS WAF <https://docs.aws.amazon.com/waf/latest/developerguide/waf-captcha-puzzle-examples.html>`_
JavaScript challenge during login. ``amazon-orders`` ships built-in support for solving these via third-party
solver services as opt-in optional installs. Once one is configured, ``amazon-orders login`` clears the challenge
automatically.

The supported providers are:

- `CapSolver <https://capsolver.com>`_
- `Anti-Captcha <https://anti-captcha.com>`_
- `2Captcha <https://2captcha.com>`_

Each provider follows the same setup: add its optional install, set its API key as an environment variable, and
register the form in your config.

CapSolver
---------

Add the ``[capsolver]`` optional install:

.. code-block:: shell

    pip install amazon-orders[capsolver]

Set your API key as an environment variable:

.. code-block:: shell

    export CAPSOLVER_API_KEY=your-capsolver-key

Register the form in your ``~/.config/amazonorders/config.yml``:

.. code-block:: yaml

    auth_forms_classes:
      - amazonorders.contrib.captcha.capsolver.CapSolverWafForm

Now ``amazon-orders login`` will clear any AWS WAF challenge it encounters during authentication.

Anti-Captcha
------------

Add the ``[anticaptcha]`` optional install:

.. code-block:: shell

    pip install amazon-orders[anticaptcha]

Set your API key as an environment variable:

.. code-block:: shell

    export ANTICAPTCHA_API_KEY=your-anticaptcha-key

Register the form in your ``~/.config/amazonorders/config.yml``:

.. code-block:: yaml

    auth_forms_classes:
      - amazonorders.contrib.captcha.anticaptcha.AntiCaptchaWafForm

2Captcha
--------

Add the ``[2captcha]`` optional install:

.. code-block:: shell

    pip install amazon-orders[2captcha]

Set your API key as an environment variable:

.. code-block:: shell

    export TWOCAPTCHA_API_KEY=your-2captcha-key

Register the form in your ``~/.config/amazonorders/config.yml``:

.. code-block:: yaml

    auth_forms_classes:
      - amazonorders.contrib.captcha.twocaptcha.TwoCaptchaWafForm

Writing Your Own
----------------

The ``auth_forms_classes`` config option accepts any
:class:`~amazonorders.forms.AuthForm` subclass, so you can integrate any provider you like. Subclass
:class:`~amazonorders.contrib.captcha.base.AwsWafForm` and implement ``_solve_token(url) -> str`` to call the
service of your choice and return the resulting ``aws-waf-token`` cookie value:

.. code-block:: python

    from amazonorders.contrib.captcha.base import AwsWafForm


    class MyCustomWafForm(AwsWafForm):
        API_KEY_ENV_VAR = "MY_PROVIDER_API_KEY"

        def _solve_token(self, url):
            ...

Once registered in ``auth_forms_classes``, your form participates in the same auth chain as the built-in providers.

If a supported optional install isn't working for you, please
`open an issue <https://github.com/alexdlaird/amazon-orders/issues/new?assignees=&labels=bug&projects=&template=bug-report.yml>`_
or a `pull request <https://github.com/alexdlaird/amazon-orders/compare>`_.

.. note::

   ``amazon-orders`` does not maintain or recommend any specific Captcha solver. You're responsible for evaluating
   the security, pricing, and reliability of any third-party service you choose, and for any costs associated with
   the API calls those services make on your behalf.
