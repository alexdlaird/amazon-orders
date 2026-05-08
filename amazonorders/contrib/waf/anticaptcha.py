__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

from typing import Any, Dict

from amazonorders.contrib.waf.base import AwsWafForm
from amazonorders.exception import AmazonOrdersError


class AntiCaptchaWafForm(AwsWafForm):
    """
    Solves AWS WAF JavaScript challenges via `Anti-Captcha
    <https://anti-captcha.com>`_'s ``AmazonTaskProxyless`` task.

    Reads the API key from the ``ANTICAPTCHA_API_KEY`` environment variable.
    Requires the ``anticaptchaofficial`` Python package:
    ``pip install amazon-orders[anticaptcha]``.
    """

    API_KEY_ENV_VAR = "ANTICAPTCHA_API_KEY"
    PROVIDER_NAME = "Anti-Captcha"

    def _solve_token(self,
                     url: str,
                     goku: Dict[str, Any],
                     challenge_script: str) -> str:
        """
        Solve the AWS WAF challenge via Anti-Captcha's ``AmazonTaskProxyless``
        task type and return the ``aws-waf-token`` cookie value.

        :param url: The URL of the WAF-challenged page.
        :param goku: The parsed ``window.gokuProps`` payload.
        :param challenge_script: The ``src`` of the AWS WAF ``challenge.js`` script tag.
        :return: The ``aws-waf-token`` cookie value.
        :raises AmazonOrdersError: if the ``anticaptchaofficial`` package is
            not installed, or if Anti-Captcha returns no token.
        """
        try:
            from anticaptchaofficial.amazonproxyless import amazonProxyless  # type: ignore[import-untyped]
        except ImportError as e:
            raise AmazonOrdersError(
                "AntiCaptchaWafForm requires the 'anticaptchaofficial' package. "
                "Install it with: pip install amazon-orders[anticaptcha]"
            ) from e

        solver = amazonProxyless()
        solver.set_key(self.api_key)
        solver.set_website_url(url)
        solver.set_website_key(goku["key"])
        solver.set_iv(goku["iv"])
        solver.set_context(goku["context"])
        solver.set_challenge_script(challenge_script)

        try:
            token = solver.solve_and_return_solution()
        except Exception as e:
            raise AmazonOrdersError(
                f"Anti-Captcha failed to solve AWS WAF challenge: {e}"
            ) from e

        if not token:
            raise AmazonOrdersError(
                f"Anti-Captcha could not solve the AWS WAF challenge: "
                f"{getattr(solver, 'error_code', 'unknown error')}"
            )
        return token
