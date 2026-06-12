__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

from typing import Any, Dict, List, Optional

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
                     url: str,
                     goku: Dict[str, Any],
                     challenge_script: str) -> str:
        """
        Solve the AWS WAF challenge via CapSolver's ``AntiAwsWafTaskProxyLess``
        task type and return the ``aws-waf-token`` cookie value.

        :param url: The URL of the WAF-challenged page.
        :param goku: The parsed ``window.gokuProps`` payload.
        :param challenge_script: The ``src`` of the AWS WAF ``challenge.js`` script tag.
        :return: The ``aws-waf-token`` cookie value.
        :raises AmazonOrdersError: if the ``capsolver`` package is not installed,
            or if CapSolver's response does not contain the expected
            ``cookie`` field.
        """
        try:
            import capsolver
        except ImportError as e:
            raise AmazonOrdersError(
                "CapSolverWafForm requires the 'capsolver' package. "
                "Install it with: `pip install amazon-orders[capsolver]`"
            ) from e

        capsolver.api_key = self.api_key

        try:
            solution = capsolver.solve({
                "type": "AntiAwsWafTaskProxyLess",
                "websiteURL": url,
                "awsKey": goku["key"],
                "awsIv": goku["iv"],
                "awsContext": goku["context"],
                "awsChallengeJS": challenge_script,
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

    def _solve_visual_captcha(self,
                              url: str,
                              image_data: List[str],
                              question: str) -> Optional[List[int]]:
        """
        Solve a visual grid Puzzle via CapSolver's ``AwsWafClassification`` task
        type and return the indices of the correct grid cells.

        :param url: The URL of the page containing the Puzzle.
        :param image_data: List of base64-encoded data URLs, one per grid tile.
        :param question: The object to identify (e.g. ``"the buckets"``).
        :return: A list of zero-based grid cell indices to select.
        :raises AmazonOrdersError: if the ``capsolver`` package is not installed,
            or if CapSolver's response does not contain the expected fields.
        """
        try:
            import capsolver
        except ImportError as e:
            raise AmazonOrdersError(
                "CapSolverWafForm requires the 'capsolver' package. "
                "Install it with: `pip install amazon-orders[capsolver]`"
            ) from e

        capsolver.api_key = self.api_key

        images_b64 = []
        for img in image_data:
            images_b64.append(img.split(",", 1)[1] if "," in img else img)

        question_id = f"aws:grid:{question.replace('the ', '').rstrip('s')}"

        try:
            solution = capsolver.solve({
                "type": "AwsWafClassification",
                "websiteURL": url,
                "images": images_b64,
                "question": question_id,
            })
        except Exception as e:
            raise AmazonOrdersError(
                f"CapSolver failed to solve Puzzle: {e}"
            ) from e

        try:
            return solution["objects"]
        except (KeyError, TypeError) as e:
            raise AmazonOrdersError(
                f"Unexpected CapSolver Puzzle response (missing 'objects'): {solution!r}"
            ) from e
