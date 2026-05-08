__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import json

from amazonorders.contrib.captcha.base import AwsWafForm
from amazonorders.exception import AmazonOrdersError


class TwoCaptchaWafForm(AwsWafForm):
    """
    Solves AWS WAF JavaScript challenges via `2Captcha <https://2captcha.com>`_'s
    ``amazon_waf`` solver method.

    Reads the API key from the ``TWOCAPTCHA_API_KEY`` environment variable.
    Requires the ``2captcha-python`` Python package:
    ``pip install amazon-orders[2captcha]``.
    """

    API_KEY_ENV_VAR = "TWOCAPTCHA_API_KEY"
    PROVIDER_NAME = "2Captcha"

    def _solve_token(self,
                     url: str) -> str:
        """
        Solve the AWS WAF challenge via 2Captcha's ``amazon_waf`` method and
        return the ``aws-waf-token`` cookie value (extracted from the
        ``existing_token`` field in 2Captcha's response).

        :param url: The URL of the WAF-challenged page.
        :return: The ``aws-waf-token`` cookie value.
        :raises AmazonOrdersError: if the ``2captcha-python`` package is not
            installed, or if 2Captcha's response is malformed or missing the
            expected ``existing_token`` field.
        """
        try:
            from twocaptcha import TwoCaptcha  # type: ignore[import-untyped]
        except ImportError as e:
            raise AmazonOrdersError(
                "TwoCaptchaWafForm requires the '2captcha-python' package. "
                "Install it with: pip install amazon-orders[2captcha]"
            ) from e

        assert self._goku is not None and self._challenge_script is not None

        solver = TwoCaptcha(self.api_key)
        try:
            result = solver.amazon_waf(
                sitekey=self._goku["key"],
                iv=self._goku["iv"],
                context=self._goku["context"],
                url=url,
                challenge_script=self._challenge_script,
            )
        except Exception as e:
            raise AmazonOrdersError(
                f"2Captcha failed to solve AWS WAF challenge: {e}"
            ) from e

        try:
            return json.loads(result["code"])["existing_token"]
        except (KeyError, TypeError, json.JSONDecodeError) as e:
            raise AmazonOrdersError(
                f"Unexpected 2Captcha response (missing 'existing_token'): {result!r}"
            ) from e
