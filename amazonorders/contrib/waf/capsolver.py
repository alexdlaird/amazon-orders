__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

from amazonorders.contrib.waf.base import AwsWafForm
from amazonorders.exception import AmazonOrdersError


class CapSolverWafForm(AwsWafForm):
    """
    Solves AWS WAF JavaScript challenges via `CapSolver
    <https://capsolver.com>`_'s ``AntiAwsWafTaskProxyLess`` task.

    Reads the API key from the ``CAPSOLVER_API_KEY`` environment variable.
    Requires the ``capsolver`` Python package: ``pip install amazon-orders[capsolver]``.
    """

    API_KEY_ENV_VAR = "CAPSOLVER_API_KEY"
    PROVIDER_NAME = "CapSolver"

    def _solve_token(self,
                     url: str) -> str:
        """
        Solve the AWS WAF challenge via CapSolver's ``AntiAwsWafTaskProxyLess``
        task type and return the ``aws-waf-token`` cookie value.

        :param url: The URL of the WAF-challenged page.
        :return: The ``aws-waf-token`` cookie value.
        :raises AmazonOrdersError: if the ``capsolver`` package is not installed,
            or if CapSolver's response does not contain the expected
            ``cookie`` field.
        """
        try:
            import capsolver  # type: ignore[import-untyped]
        except ImportError as e:
            raise AmazonOrdersError(
                "CapSolverWafForm requires the 'capsolver' package. "
                "Install it with: pip install amazon-orders[capsolver]"
            ) from e

        capsolver.api_key = self.api_key

        assert self._goku is not None and self._challenge_script is not None
        try:
            solution = capsolver.solve({
                "type": "AntiAwsWafTaskProxyLess",
                "websiteURL": url,
                "awsKey": self._goku["key"],
                "awsIv": self._goku["iv"],
                "awsContext": self._goku["context"],
                "awsChallengeJS": self._challenge_script,
            })
        except Exception as e:
            raise AmazonOrdersError(
                f"CapSolver failed to solve AWS WAF challenge: {e}"
            ) from e

        try:
            return solution["cookie"]
        except (KeyError, TypeError) as e:
            raise AmazonOrdersError(
                f"Unexpected CapSolver response (missing 'cookie'): {solution!r}"
            ) from e
