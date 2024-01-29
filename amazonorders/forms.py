from abc import ABC
from io import BytesIO
from typing import Optional, Dict, Any
from urllib.parse import urlparse

from PIL import Image
from amazoncaptcha import AmazonCaptcha
from bs4 import Tag

from amazonorders import constants
from amazonorders.exception import AmazonOrdersError, AmazonOrdersAuthError

__author__ = "Alex Laird"
__copyright__ = "Copyright 2024, Alex Laird"
__version__ = "1.0.7"


class AuthForm(ABC):
    """
    The base class of an authentication ``<form>`` that can be submitted.
    """

    def __init__(self,
                 selector: str,
                 error_selector: str = constants.DEFAULT_ERROR_TAG_SELECTOR,
                 critical: bool = False) -> None:
        #: The CSS selector for the ``<form>``.
        self.selector: str = selector
        #: The CSS selector for the error div when form submission fails.
        self.error_selector: str = error_selector
        #: If ``critical``, form submission failures will raise :class:`~amazonorders.exception.AmazonOrdersAuthError`.
        self.critical: bool = critical
        #: The :class:`~amazonorders.session.AmazonSession` on which to submit the form.
        self.amazon_session = None
        #: The selected ``<form>``.
        self.form: Optional[Tag] = None
        #: The ``<form>`` data that will be submitted.
        self.data: Optional[Dict[Any]] = None

    def select_form(self,
                    amazon_session,
                    parsed: Tag) -> bool:
        """
        Using the ``selector`` defined on this instance, select the ``<form>`` for the given :class:`~bs4.Tag`.

        :param amazon_session: The ``AmazonSession`` on which to submit the form.
        :param parsed: The ``Tag`` from which to select the ``<form>``.
        :return: Whether the ``<form>`` selection was successful.
        """
        self.amazon_session = amazon_session
        self.form = parsed.select_one(self.selector)

        return self.form is not None

    def fill_form(self,
                  additional_attrs: Optional[Dict[str, Any]] = None) -> None:
        """
        Populate the ``data`` field with values from the ``<form>``, including any additional attributes passed.

        :param additional_attrs: Additional attributes to add to the ``<form>`` data for submission.
        """
        if not self.form:
            raise AmazonOrdersError("Call AuthForm.select_form() first.")

        self.data = {}
        for field in self.form.select("input"):
            try:
                self.data[field["name"]] = field["value"]
            except:
                pass
        if additional_attrs:
            self.data.update(additional_attrs)

    def submit(self) -> None:
        """
        Submit the populated ``<form>``.
        """
        if not self.form:
            raise AmazonOrdersError("Call AuthForm.select_form() first.")
        elif not self.data:
            raise AmazonOrdersError("Call AuthForm.fill_form() first.")

        method = self.form.get("method", "GET").upper()
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
        captcha_response = AmazonCaptcha.fromlink(url).solve()
        if not captcha_response or captcha_response.lower() == "not solved":
            img_response = self.amazon_session.session.get(url)
            img = Image.open(BytesIO(img_response.content))
            img.show()

            self.amazon_session.io.echo("Info: The Captcha couldn't be auto-solved.")

            captcha_response = self.amazon_session.io.prompt("--> Enter the characters shown in the image")
            self.amazon_session.io.echo("")

        return captcha_response

    def _get_form_action(self) -> str:
        action = self.form.get("action")
        if not action:
            return self.amazon_session.last_response.url
        elif not action.startswith("http"):
            if action.startswith("/"):
                parsed_url = urlparse(self.amazon_session.last_response.url)
                return "{}://{}{}".format(parsed_url.scheme, parsed_url.netloc,
                                          action)
            else:
                return "{}/{}".format(
                    "/".join(self.amazon_session.last_response.url.split("/")[:-1]), action)
        else:
            return action

    def _handle_errors(self) -> None:
        error_tag = self.amazon_session.last_response_parsed.select_one(self.error_selector)
        if error_tag:
            error_msg = "An error occurred: {}\n".format(error_tag.text.strip())

            if self.critical:
                raise AmazonOrdersAuthError(error_msg)
            else:
                self.amazon_session.io.echo(error_msg, fg="red")


class SignInForm(AuthForm):
    def __init__(self,
                 selector: str = constants.SIGN_IN_FORM_SELECTOR,
                 solution_attr_key: str = "email") -> None:
        super().__init__(selector, critical=True)

        self.solution_attr_key = solution_attr_key

    def fill_form(self,
                  additional_attrs: Optional[Dict[str, Any]] = None) -> None:
        if not additional_attrs:
            additional_attrs = {}
        super().fill_form()

        additional_attrs.update({self.solution_attr_key: self.amazon_session.username,
                                 "password": self.amazon_session.password,
                                 "rememberMe": "true"})
        self.data.update(additional_attrs)


class MfaDeviceSelectForm(AuthForm):
    def __init__(self,
                 selector: str = constants.MFA_DEVICE_SELECT_FORM_SELECTOR,
                 solution_attr_key: str = "otpDeviceContext") -> None:
        super().__init__(selector)

        self.solution_attr_key = solution_attr_key

    def fill_form(self,
                  additional_attrs: Optional[Dict[str, Any]] = None) -> None:
        if not additional_attrs:
            additional_attrs = {}
        super().fill_form()

        contexts = self.form.select(constants.MFA_DEVICE_SELECT_INPUT_SELECTOR)
        i = 1
        for field in contexts:
            self.amazon_session.io.echo("{}: {}".format(i, field["value"].strip()))
            i += 1

        otp_device = int(
            self.amazon_session.io.prompt("--> Enter where you would like your one-time passcode sent",
                                          type=int)
        )
        self.amazon_session.io.echo("")

        additional_attrs.update({self.solution_attr_key: contexts[otp_device - 1]["value"]})
        self.data.update(additional_attrs)


class MfaForm(AuthForm):
    def __init__(self,
                 selector: str = constants.MFA_FORM_SELECTOR,
                 solution_attr_key: str = "otpCode") -> None:
        super().__init__(selector)

        self.solution_attr_key = solution_attr_key

    def fill_form(self,
                  additional_attrs: Optional[Dict[str, Any]] = None) -> None:
        if not additional_attrs:
            additional_attrs = {}
        super().fill_form()

        otp = self.amazon_session.io.prompt("--> Enter the one-time passcode sent to your device")
        self.amazon_session.io.echo("")

        additional_attrs.update({self.solution_attr_key: otp,
                                 "rememberDevice": ""})
        self.data.update(additional_attrs)


class CaptchaForm(AuthForm):
    def __init__(self,
                 selector: str = constants.CAPTCHA_1_FORM_SELECTOR,
                 error_selector: str = constants.CAPTCHA_1_ERROR_SELECTOR,
                 solution_attr_key: str = "cvf_captcha_input") -> None:
        super().__init__(selector, error_selector)

        self.solution_attr_key = solution_attr_key

    def fill_form(self,
                  additional_attrs: Optional[Dict[str, Any]] = None) -> None:
        if not additional_attrs:
            additional_attrs = {}
        super().fill_form(additional_attrs)

        # TODO: eliminate the use of find_parent() here
        img_url = self.form.find_parent().select_one("img")["src"]
        if not img_url.startswith("http"):
            img_url = "{}{}".format(constants.BASE_URL, img_url)
        solution = self._solve_captcha(img_url)

        additional_attrs.update({self.solution_attr_key: solution})
        self.data.update(additional_attrs)
