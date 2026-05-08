__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import json
import logging
import os
import re
from typing import Any, ClassVar, Dict, Optional, TYPE_CHECKING
from urllib.parse import urlparse

from bs4 import Tag
from requests import Response

from amazonorders.conf import AmazonOrdersConfig
from amazonorders.exception import AmazonOrdersError
from amazonorders.forms import AuthForm
from amazonorders.util import AmazonSessionResponse

if TYPE_CHECKING:
    from amazonorders.session import AmazonSession

logger = logging.getLogger(__name__)

_GOKU_PROPS_RE = re.compile(r"window\.gokuProps\s*=\s*(\{.*?\});", re.DOTALL)


class AwsWafForm(AuthForm):
    """
    Shared base for AWS WAF JavaScript challenge solvers. Subclasses implement
    :func:`_solve_token` to call a third-party solver and return the
    ``aws-waf-token`` cookie value.

    This base class handles detection (the ``window.gokuProps`` blob plus the
    ``challenge.js`` script tag), setting the ``aws-waf-token`` cookie on the
    session, and re-fetching the challenged URL.
    """

    #: Name of the environment variable from which to read this solver's API key.
    #: Subclasses must override.
    API_KEY_ENV_VAR: ClassVar[str] = ""

    #: Display name of the third-party provider, used in the user-visible message
    #: emitted on every successful solve. Subclasses must override.
    PROVIDER_NAME: ClassVar[str] = ""

    def __init__(self,
                 config: AmazonOrdersConfig) -> None:
        super().__init__(config, selector=None)
        api_key = os.environ.get(self.API_KEY_ENV_VAR, "")
        if not api_key:
            raise AmazonOrdersError(
                f"{type(self).__name__} requires the {self.API_KEY_ENV_VAR} "
                f"environment variable to be set."
            )
        #: The third-party solver API key, sourced from :attr:`API_KEY_ENV_VAR`.
        self.api_key: str = api_key
        self._goku: Optional[Dict[str, Any]] = None
        self._challenge_script: Optional[str] = None

    def select_form(self,
                    amazon_session: "AmazonSession",
                    parsed: Tag) -> bool:
        """
        Detect an AWS WAF challenge page by matching the ``window.gokuProps``
        blob and the ``challenge.js`` script tag. When both are present, this
        form will handle the page; otherwise the auth loop continues to the
        next form.

        :param amazon_session: The ``AmazonSession`` on which to submit the form.
        :param parsed: The ``Tag`` for the page being inspected.
        :return: ``True`` if a WAF challenge was detected, ``False`` otherwise.
        """
        self.amazon_session = amazon_session

        match = _GOKU_PROPS_RE.search(str(parsed))
        if not match:
            return False
        try:
            self._goku = json.loads(match.group(1))
        except json.JSONDecodeError:
            return False

        challenge_tag = parsed.select_one('script[src*="awswaf.com"]')
        if not challenge_tag:
            return False
        src = challenge_tag.get("src")
        if not isinstance(src, str):
            return False
        self._challenge_script = src
        return True

    def fill_form(self,
                  additional_attrs: Optional[Dict[str, Any]] = None) -> None:
        """AWS WAF challenge pages have no ``<form>`` to populate; no-op override."""
        pass

    def submit(self,
               last_response: Response) -> AmazonSessionResponse:
        """
        Hand the WAF challenge off to :func:`_solve_token`, set the resulting
        ``aws-waf-token`` cookie on the session, and re-fetch the challenged URL.

        :param last_response: The response that returned the WAF challenge page.
        :return: The :class:`~amazonorders.util.AmazonSessionResponse` from
            re-fetching the URL after the cookie is set.
        :raises AmazonOrdersError: if :func:`select_form` was not called first.
        """
        if not self.amazon_session or self._goku is None or self._challenge_script is None:
            raise AmazonOrdersError(
                "Call AwsWafForm.select_form() first."
            )  # pragma: no cover

        token = self._solve_token(last_response.url)

        # Always surface that a paid third-party service was used, regardless of debug mode.
        message = (
            f"Info: AWS WAF challenge solved via {self.PROVIDER_NAME}."
        )
        logger.info(message)
        self.amazon_session.io.echo(message)

        domain = urlparse(self.config.constants.BASE_URL).netloc
        self.amazon_session.session.cookies.set("aws-waf-token", token, domain=domain)

        return self.amazon_session.get(last_response.url)

    def _solve_token(self,
                     url: str) -> str:
        """
        Subclass hook. Call the third-party solver using :attr:`_goku` and
        :attr:`_challenge_script`, and return the resulting ``aws-waf-token``
        cookie value to be set on the session.

        :param url: The URL of the WAF-challenged page.
        :return: The ``aws-waf-token`` cookie value.
        :raises NotImplementedError: if a subclass does not override this method.
        """
        raise NotImplementedError
