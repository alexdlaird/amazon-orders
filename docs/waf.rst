======================
Solving WAF Challenges
======================

Amazon may present an AWS WAF (Web Application Firewall) JavaScript challenge during sign-in. An opt-in extra passes
it to a third-party solver service.

WAF solving is part of |amazon-auth|_, the authentication package
``amazon-orders`` is built on. This page covers getting started from ``amazon-orders``; :doc:`amazonauth:waf` in its
docs covers how the challenge works, combining a solver with :doc:`browser automation <browser>`, and writing your own
solver.

Getting Started
---------------

Install the extra for your provider, provide its API key (see :attr:`amazonauth.contrib.waf.base.AwsWafForm.api_key`),
and add its form to ``auth_forms_classes`` in the :class:`config <amazonorders.conf.AmazonOrdersConfig>`
(``~/.config/amazonorders/config.yml``):

.. list-table::
   :header-rows: 1

   * - Provider
     - Install
     - API key
     - Form
   * - `CapSolver <https://capsolver.com>`_
     - ``pip install amazon-orders[capsolver]``
     - ``CAPSOLVER_API_KEY``
     - ``amazonauth.contrib.waf.capsolver.CapSolverWafForm``
   * - `Anti-Captcha <https://anti-captcha.com>`_
     - ``pip install amazon-orders[anticaptcha]``
     - ``ANTICAPTCHA_API_KEY``
     - ``amazonauth.contrib.waf.anticaptcha.AntiCaptchaWafForm``
   * - `2Captcha <https://2captcha.com>`_
     - ``pip install amazon-orders[2captcha]``
     - ``TWOCAPTCHA_API_KEY``
     - ``amazonauth.contrib.waf.twocaptcha.TwoCaptchaWafForm``

For instance, for CapSolver:

.. code-block:: shell

    pip install amazon-orders[capsolver]

.. code-block:: yaml

    auth_forms_classes:
      - amazonauth.contrib.waf.capsolver.CapSolverWafForm

Now ``amazon-orders login`` passes any AWS WAF challenge it encounters during sign-in to CapSolver.
