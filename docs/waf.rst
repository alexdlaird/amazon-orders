======================
Solving WAF Challenges
======================

Amazon may present an AWS WAF (Web Application Firewall) JavaScript challenge during sign-in. A third-party solver
service, through an opt-in extra, clears it automatically.

WAF solving is part of `amazon-auth <https://amazon-auth.readthedocs.io>`_, the authentication package
``amazon-orders`` is built on. This page covers getting started from ``amazon-orders``; :doc:`amazonauth:waf` in its
docs covers how the challenge works, combining a solver with :doc:`browser automation <browser>`, and writing your own
solver.

Getting Started
---------------

Install the extra for your provider, set its API key as an environment variable, and add its form to
``auth_forms_classes`` in the :class:`config <amazonorders.conf.AmazonOrdersConfig>`
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
    export CAPSOLVER_API_KEY=your-capsolver-key

.. code-block:: yaml

    auth_forms_classes:
      - amazonauth.contrib.waf.capsolver.CapSolverWafForm

Now ``amazon-orders login`` clears any AWS WAF challenge it encounters during sign-in.
