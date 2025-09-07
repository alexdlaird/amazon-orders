__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import re
from abc import ABC
from typing import Any, Dict, Optional, TYPE_CHECKING
from urllib.parse import urlparse

import pyotp
from bs4 import Tag
from requests import Response

from amazonorders import util
from amazonorders.conf import AmazonOrdersConfig
from amazonorders.exception import AmazonOrdersAuthError, AmazonOrdersError
from amazonorders.util import AmazonSessionResponse

if TYPE_CHECKING:
    from amazonorders.session import AmazonSession


class AuthForm(ABC):
    """
    The base class of an authentication ``<form>`` that can be submitted.
    """

    def __init__(self,
                 config: AmazonOrdersConfig,
                 selector: Optional[str],
                 error_selector: Optional[str] = None,
                 critical: bool = False) -> None:
        #: The config to use.
        self.config: AmazonOrdersConfig = config
        #: The CSS selector for the ``<form>``.
        self.selector: Optional[str] = selector
        #: The CSS selector for the error div when form submission fails.
        self.error_selector: str = error_selector or config.selectors.DEFAULT_ERROR_TAG_SELECTOR
        #: If ``True``, form submission failures will raise :class:`~amazonorders.exception.AmazonOrdersAuthError`.
        self.critical: bool = critical
        #: The :class:`~amazonorders.session.AmazonSession` on which to submit the form.
        self.amazon_session: Optional["AmazonSession"] = None
        #: The selected ``<form>``.
        self.form: Optional[Tag] = None
        #: The ``<form>`` data that will be submitted.
        self.data: Optional[Dict[str, Any]] = None

    def select_form(self,
                    amazon_session: "AmazonSession",
                    parsed: Tag) -> bool:
        """
        Using the ``selector`` defined on this instance, select the ``<form>`` for the given :class:`~bs4.Tag`.

        :param amazon_session: The ``AmazonSession`` on which to submit the form.
        :param parsed: The ``Tag`` from which to select the ``<form>``.
        :return: Whether the ``<form>`` selection was successful.
        """
        if not self.selector:
            raise AmazonOrdersError("Must set a selector first.")  # pragma: no cover

        self.amazon_session = amazon_session
        self.form = util.select_one(parsed, self.selector)

        return self.form is not None

    def fill_form(self,
                  additional_attrs: Optional[Dict[str, Any]] = None) -> None:
        """
        Populate the ``data`` field with values from the ``<form>``, including any additional attributes passed.

        :param additional_attrs: Additional attributes to add to the ``<form>`` data for submission.
        """
        if not self.form:
            raise AmazonOrdersError(
                "Call AuthForm.select_form() first."
            )  # pragma: no cover

        self.data = {}
        for field in self.form.select("input"):
            try:
                self.data[str(field["name"])] = field["value"]
            except Exception:
                pass
        if additional_attrs:
            self.data.update(additional_attrs)

    def submit(self, last_response: Response) -> AmazonSessionResponse:
        """
        Submit the populated ``<form>``.

        :param last_response: The response of the request that fetched the form.
        :return: The response from the executed request.
        """
        if not self.amazon_session or not self.form or not self.data:
            raise AmazonOrdersError(
                "Call AuthForm.select_form() first."
            )  # pragma: no cover

        method = str(self.form.get("method", "GET")).upper()
        url = self._get_form_action(last_response)
        request_data = {"params" if method == "GET" else "data": self.data}
        form_response = self.amazon_session.request(method,
                                                    url,
                                                    persist_cookies=True,
                                                    **request_data)

        self._handle_errors(form_response)

        self.clear_form()

        return form_response

    def clear_form(self) -> None:
        """
        Clear the populated ``<form>`` so this class can be reused.
        """
        self.amazon_session = None
        self.form = None
        self.data = None

    def _get_form_action(self, last_response: Response) -> str:
        if not self.amazon_session or not self.form:
            raise AmazonOrdersError(
                "Call AuthForm.select_form() first."
            )  # pragma: no cover

        action = self.form.get("action")
        if not action:
            return last_response.url

        action = str(action)
        if not action.startswith("http"):
            if action.startswith("/"):
                parsed_url = urlparse(last_response.url)
                return f"{parsed_url.scheme}://{parsed_url.netloc}{action}"
            else:
                return "{url}/{path}".format(url="/".join(last_response.url.split("/")[:-1]),
                                             path=action)
        else:
            return action

    def _handle_errors(self, form_response: AmazonSessionResponse) -> None:
        if not self.amazon_session:
            raise AmazonOrdersError(
                "Call AuthForm.select_form() first."
            )  # pragma: no cover

        error_tag = util.select_one(form_response.parsed, self.error_selector)
        if error_tag:
            error_msg = f"Error from Amazon: {util.cleanup_html_text(error_tag.text)}"

            if self.critical:
                raise AmazonOrdersAuthError(error_msg)
            else:
                self.amazon_session.io.echo(error_msg, fg="red")


class SignInForm(AuthForm):
    def __init__(self,
                 config: AmazonOrdersConfig,
                 selector: Optional[str] = None,
                 solution_attr_key: str = "email") -> None:
        if not selector:
            selector = config.selectors.SIGN_IN_FORM_SELECTOR

        super().__init__(config, selector, critical=True)

        self.solution_attr_key = solution_attr_key

    def fill_form(self,
                  additional_attrs: Optional[Dict[str, Any]] = None) -> None:
        if not self.amazon_session:
            raise AmazonOrdersError(
                "Call AuthForm.select_form() first."
            )  # pragma: no cover

        if not additional_attrs:
            additional_attrs = {}
        super().fill_form()
        if not self.data:
            raise AmazonOrdersError(
                "SignInForm data did not populate, but it's required. "
                "Check if Amazon changed their login flow."
            )  # pragma: no cover

        additional_attrs.update({self.solution_attr_key: self.amazon_session.username,
                                 "password": self.amazon_session.password,
                                 "rememberMe": "true"})
        self.data.update(additional_attrs)


class ClaimForm(AuthForm):
    def __init__(self,
                 config: AmazonOrdersConfig,
                 selector: Optional[str] = None,
                 solution_attr_key: str = "email") -> None:
        if not selector:
            selector = config.selectors.CLAIM_FORM_SELECTOR

        super().__init__(config, selector, critical=True)

        self.solution_attr_key = solution_attr_key

    def fill_form(self,
                  additional_attrs: Optional[Dict[str, Any]] = None) -> None:
        if not self.amazon_session:
            raise AmazonOrdersError(
                "Call AuthForm.select_form() first."
            )  # pragma: no cover

        if not additional_attrs:
            additional_attrs = {}
        super().fill_form()
        if not self.data:
            raise AmazonOrdersError(
                "ClaimForm data did not populate, but it's required. "
                "Check if Amazon changed their login flow."
            )  # pragma: no cover

        additional_attrs.update({self.solution_attr_key: self.amazon_session.username,
                                 "password": self.amazon_session.password,
                                 "rememberMe": "true"})
        self.data.update(additional_attrs)


class IntentForm(AuthForm):
    def __init__(self,
                 config: AmazonOrdersConfig,
                 selector: Optional[str] = None,
                 error_selector: Optional[str] = None) -> None:
        if not selector:
            selector = config.selectors.INTENT_FORM_SELECTOR
        if not error_selector:
            error_selector = config.selectors.INTENT_MESSAGE_SELECTOR

        super().__init__(config, selector, error_selector, critical=True)

    def submit(self, last_response: Response) -> AmazonSessionResponse:
        """
        When we encounter this form, we can't submit it, so we display its contents as the
        error message, since within the context of this library, it is a termination event
        for the auth flow.

        :param last_response: The response of the request that fetched the form.
        :return: The response from the executed request.
        """
        response = AmazonSessionResponse(last_response, self.config.bs4_parser)

        self._handle_errors(response)

        return response


class MfaDeviceSelectForm(AuthForm):
    """
    This will first echo the ``<form>`` device choices, then it will pass the list of choices
    to :func:`~amazonorders.session.IODefault.prompt` as ``choices``. The value passed to
    :func:`~amazonorders.session.IODefault.prompt` will be a ``list`` of  the ``value`` from
    each of ``input`` tag.
    """

    def __init__(self,
                 config: AmazonOrdersConfig,
                 selector: Optional[str] = None,
                 solution_attr_key: str = "otpDeviceContext") -> None:
        if not selector:
            selector = config.selectors.MFA_DEVICE_SELECT_FORM_SELECTOR

        super().__init__(config, selector)

        self.solution_attr_key = solution_attr_key

    def fill_form(self,
                  additional_attrs: Optional[Dict[str, Any]] = None) -> None:
        if not self.amazon_session or not self.form:
            raise AmazonOrdersError(
                "Call AuthForm.select_form() first."
            )  # pragma: no cover

        if not additional_attrs:
            additional_attrs = {}
        super().fill_form()
        if not self.data:
            raise AmazonOrdersError(
                "MfaDeviceSelectForm data did not populate, but it's required. "
                "Check if Amazon changed their MFA flow."
            )  # pragma: no cover

        contexts = util.select(self.form, self.config.selectors.MFA_DEVICE_SELECT_INPUT_SELECTOR)
        i = 0
        choices = []
        for field in contexts:
            choices.append(f"{i}: {str(field[self.config.selectors.MFA_DEVICE_SELECT_INPUT_SELECTOR_VALUE]).strip()}")
            i += 1

        otp_device = int(
            self.amazon_session.io.prompt("Choose where you would like your one-time passcode sent",
                                          type=int,
                                          choices=choices)
        )
        self.amazon_session.io.echo("")

        additional_attrs.update({self.solution_attr_key: contexts[otp_device - 1]["value"]})
        self.data.update(additional_attrs)


class MfaForm(AuthForm):
    def __init__(self,
                 config: AmazonOrdersConfig,
                 selector: Optional[str] = None,
                 solution_attr_key: str = "otpCode") -> None:
        if not selector:
            selector = config.selectors.MFA_FORM_SELECTOR

        super().__init__(config, selector, critical=True)

        self.solution_attr_key = solution_attr_key

    def fill_form(self,
                  additional_attrs: Optional[Dict[str, Any]] = None) -> None:
        if not self.amazon_session:
            raise AmazonOrdersError(
                "Call AuthForm.select_form() first."
            )  # pragma: no cover

        if not additional_attrs:
            additional_attrs = {}
        super().fill_form()
        if not self.data:
            raise AmazonOrdersError(
                "MfaForm data did not populate, but it's required. "
                "Check if Amazon changed their MFA flow."
            )  # pragma: no cover

        if self.amazon_session.otp_secret_key:
            otp = pyotp.TOTP(self.amazon_session.otp_secret_key.replace(" ", "")).now()
        else:
            otp = self.amazon_session.io.prompt("Enter the one-time passcode from your preferred 2FA method")
            self.amazon_session.io.echo("")

        additional_attrs.update({self.solution_attr_key: otp,
                                 "rememberDevice": ""})
        self.data.update(additional_attrs)

        if "deviceId" not in self.data:
            self.data["deviceId"] = ""


class LegacyCaptchaForm(AuthForm):
    """
    This implementation exists only to support legacy Captcha forms that now contain the field keywords
    pre-populated within the form (ie. there is no image Captch challenge anymore). Amazon's WAF and other
    JavaScript-based Captcha are not solvable by this library.
    """

    def __init__(self,
                 config: AmazonOrdersConfig,
                 selector: Optional[str] = None,
                 solution_attr_key: str = "field-keywords") -> None:
        if not selector:
            selector = config.selectors.CAPTCHA_FORM_SELECTOR

        super().__init__(config, selector)

        self.solution_attr_key = solution_attr_key

    def fill_form(self,
                  additional_attrs: Optional[Dict[str, Any]] = None) -> None:
        if not self.form:
            raise AmazonOrdersError(
                "Call AuthForm.select_form() first."
            )  # pragma: no cover

        if not additional_attrs:
            additional_attrs = {}
        super().fill_form(additional_attrs)
        if not self.data:
            raise AmazonOrdersError(
                "LegacyCaptchaForm data did not populate, but it's required. "
                "Check if Amazon changed their Captcha flow, and see "
                "https://amazon-orders.readthedocs.io/troubleshooting.html#captcha-blocking-login"
            )  # pragma: no cover

        # TODO: eliminate the use of find_parent() here
        form_parent = self.form.find_parent()
        if not form_parent:
            raise AmazonOrdersError(
                "LegacyCaptchaForm parent not found, but it's required. "
                "Check if Amazon changed their Captcha flow, and see "
                "https://amazon-orders.readthedocs.io/troubleshooting.html#captcha-blocking-login."
            )  # pragma: no cover

        solution_tag = form_parent.select_one(f"input[name='{self.solution_attr_key}']")

        if solution_tag:
            solution = str(solution_tag["value"])
        else:
            raise AmazonOrdersError(
                "A JavaScript-based Captcha has been found. This library cannot solve these challenges. See "
                "https://amazon-orders.readthedocs.io/troubleshooting.html#captcha-blocking-login for more details."
            )  # pragma: no cover

        additional_attrs.update({self.solution_attr_key: solution})
        self.data.update(additional_attrs)


class JSAuthBlocker(AuthForm):
    def __init__(self,
                 config: AmazonOrdersConfig,
                 regex: str) -> None:
        self.regex = regex

        super().__init__(config, None)

    def select_form(self,
                    amazon_session: "AmazonSession",
                    parsed: Tag) -> bool:
        if not self.regex:
            raise AmazonOrdersError("Must set a regex first.")  # pragma: no cover

        if re.search(self.regex, parsed.text):
            raise AmazonOrdersAuthError(
                "A JavaScript-based authentication challenge page has been found. This library cannot solve these "
                "challenges. See "
                "https://amazon-orders.readthedocs.io/troubleshooting.html#captcha-blocking-login for more details.")

        return False
