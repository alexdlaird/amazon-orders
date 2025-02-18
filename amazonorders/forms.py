__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

from abc import ABC
from io import BytesIO
from typing import Any, Dict, Optional, TYPE_CHECKING
from urllib.parse import urlparse

from PIL import Image
from amazoncaptcha import AmazonCaptcha
from bs4 import Tag

from amazonorders import util
from amazonorders.conf import AmazonOrdersConfig
from amazonorders.exception import AmazonOrdersAuthError, AmazonOrdersError

if TYPE_CHECKING:
    from amazonorders.session import AmazonSession


class AuthForm(ABC):
    """
    The base class of an authentication ``<form>`` that can be submitted.

    The base implementation will attempt to auto-solve Captcha. If this fails, it will
    use the default image view to show the Captcha prompt, and it will also pass the
    image URL to :func:`~amazonorders.session.IODefault.prompt` as ``img_url``.
    """

    def __init__(self,
                 config: AmazonOrdersConfig,
                 selector: Optional[str],
                 error_selector: Optional[str] = None,
                 critical: bool = False) -> None:
        #: The AmazonOrdersConfig to use.
        self.config: AmazonOrdersConfig = config
        #: The CSS selector for the ``<form>``.
        self.selector: Optional[str] = selector
        #: The CSS selector for the error div when form submission fails.
        self.error_selector: str = error_selector or config.selectors.DEFAULT_ERROR_TAG_SELECTOR
        #: If ``critical``, form submission failures will raise :class:`~amazonorders.exception.AmazonOrdersAuthError`.
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

    def submit(self) -> None:
        """
        Submit the populated ``<form>``.
        """
        if not self.amazon_session or not self.form or not self.data:
            raise AmazonOrdersError(
                "Call AuthForm.select_form() first."
            )  # pragma: no cover

        method = str(self.form.get("method", "GET")).upper()
        action = self._get_form_action()
        request_data = {"params" if method == "GET" else "data": self.data}
        self.amazon_session.request(method,
                                    action,
                                    **request_data)

        self._handle_errors()

        self.clear_form()

    def clear_form(self) -> None:
        """
        Clear the populated ``<form>`` so this class can be reused.
        """
        self.amazon_session = None
        self.form = None
        self.data = None

    def _solve_captcha(self,
                       url: str) -> str:
        if not self.amazon_session:
            raise AmazonOrdersError(
                "Call AuthForm.select_form() first."
            )  # pragma: no cover

        captcha_response = AmazonCaptcha.fromlink(url).solve()
        if not captcha_response or captcha_response.lower() == "not solved":
            img_response = self.amazon_session.session.get(url)
            img = Image.open(BytesIO(img_response.content))
            img.show()

            self.amazon_session.io.echo("Info: The Captcha couldn't be auto-solved.")

            captcha_response = self.amazon_session.io.prompt("Enter the characters shown in the image",
                                                             img_url=url)
            self.amazon_session.io.echo("")

        return captcha_response

    def _get_form_action(self) -> str:
        if not self.amazon_session or not self.form:
            raise AmazonOrdersError(
                "Call AuthForm.select_form() first."
            )  # pragma: no cover

        action = self.form.get("action")
        if not action:
            return self.amazon_session.last_response.url

        action = str(action)
        if not action.startswith("http"):
            if action.startswith("/"):
                parsed_url = urlparse(self.amazon_session.last_response.url)
                return f"{parsed_url.scheme}://{parsed_url.netloc}{action}"
            else:
                return "{url}/{path}".format(url="/".join(self.amazon_session.last_response.url.split("/")[:-1]),
                                             path=action)
        else:
            return action

    def _handle_errors(self) -> None:
        if not self.amazon_session:
            raise AmazonOrdersError(
                "Call AuthForm.select_form() first."
            )  # pragma: no cover

        error_tag = util.select_one(self.amazon_session.last_response_parsed, self.error_selector)
        if error_tag:
            error_msg = f"An error occurred: {error_tag.text.strip().rstrip('.')}.\n"

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

        super().__init__(config, selector)

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

        otp = self.amazon_session.io.prompt("Enter the one-time passcode sent to your device")
        self.amazon_session.io.echo("")

        additional_attrs.update({self.solution_attr_key: otp,
                                 "rememberDevice": ""})
        self.data.update(additional_attrs)


class CaptchaForm(AuthForm):
    def __init__(self,
                 config: AmazonOrdersConfig,
                 selector: Optional[str] = None,
                 error_selector: Optional[str] = None,
                 solution_attr_key: str = "cvf_captcha_input") -> None:
        if not selector:
            selector = config.selectors.CAPTCHA_1_FORM_SELECTOR
        elif not error_selector:
            error_selector = config.selectors.CAPTCHA_1_ERROR_SELECTOR

        super().__init__(config, selector, error_selector)

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
                "CaptchaForm data did not populate, but it's required. "
                "Check if Amazon changed their Captcha flow."
            )  # pragma: no cover

        # TODO: eliminate the use of find_parent() here
        form_parent = self.form.find_parent()
        if not form_parent:
            raise AmazonOrdersError(
                "CaptchaForm parent not found, but it's required. "
                "Check if Amazon changed their Captcha flow."
            )  # pragma: no cover

        img_tag = form_parent.select_one("img")
        if not img_tag:
            raise AmazonOrdersError(
                "CaptchaForm <img> tag not found, but it's required. "
                "Check if Amazon changed their Captcha flow."
            )  # pragma: no cover

        img_url = str(img_tag["src"])

        if not img_url.startswith("http"):
            img_url = f"{self.config.constants.BASE_URL}{img_url}"
        solution = self._solve_captcha(img_url)

        additional_attrs.update({self.solution_attr_key: solution})
        self.data.update(additional_attrs)
