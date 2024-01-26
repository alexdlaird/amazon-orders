from abc import ABC
from io import BytesIO
from typing import Optional, Dict, Any
from urllib.parse import urlparse

from PIL import Image
from amazoncaptcha import AmazonCaptcha
from bs4 import Tag

from amazonorders.constants import SIGN_IN_FORM_SELECTOR, DEFAULT_ERROR_SELECTOR, MFA_DEVICE_SELECT_FORM_SELECTOR, \
    MFA_FORM_SELECTOR, BASE_URL, CAPTCHA_1_FORM_SELECTOR, CAPTCHA_1_ERROR_SELECTOR
from amazonorders.exception import AmazonOrdersError, AmazonOrdersAuthError

__author__ = "Alex Laird"
__copyright__ = "Copyright 2024, Alex Laird"
__version__ = "1.0.7"


class AuthForm(ABC):
    def __init__(self,
                 selector: str,
                 error_selector: str = DEFAULT_ERROR_SELECTOR,
                 critical: bool = False) -> None:
        self.selector = selector
        self.error_selector = error_selector
        self.critical = critical
        self.amazon_session = None
        self.form = None
        self.data = None

    def select_form(self,
                    amazon_session,
                    parsed: Tag) -> bool:
        self.amazon_session = amazon_session
        self.form = parsed.select_one(self.selector)

        return self.form is not None

    def fill_form(self,
                  additional_attrs: Optional[Dict[str, Any]] = None) -> None:
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

    def clear_form(self):
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
    def __init__(self) -> None:
        super().__init__(SIGN_IN_FORM_SELECTOR, critical=True)

    def fill_form(self,
                  additional_attrs: Optional[Dict[str, Any]] = None) -> None:
        if not additional_attrs:
            additional_attrs = {}
        super().fill_form()

        additional_attrs.update({"email": self.amazon_session.username,
                                 "password": self.amazon_session.password,
                                 "rememberMe": "true"})
        self.data.update(additional_attrs)


class MfaDeviceSelectForm(AuthForm):
    def __init__(self) -> None:
        super().__init__(MFA_DEVICE_SELECT_FORM_SELECTOR)

    def fill_form(self,
                  additional_attrs: Optional[Dict[str, Any]] = None) -> None:
        if not additional_attrs:
            additional_attrs = {}
        super().fill_form()

        contexts = self.form.select("input[name='otpDeviceContext']")
        i = 1
        for field in contexts:
            self.amazon_session.io.echo("{}: {}".format(i, field["value"].strip()))
            i += 1

        otp_device = int(
            self.amazon_session.io.prompt("--> Enter where you would like your one-time passcode sent",
                                          type=int)
        )
        self.amazon_session.io.echo("")

        additional_attrs.update({"otpDeviceContext": contexts[otp_device - 1]["value"]})
        self.data.update(additional_attrs)


class MfaForm(AuthForm):
    def __init__(self,
                 selector: str = MFA_FORM_SELECTOR) -> None:
        super().__init__(selector)

    def fill_form(self,
                  additional_attrs: Optional[Dict[str, Any]] = None) -> None:
        if not additional_attrs:
            additional_attrs = {}
        super().fill_form()

        otp = self.amazon_session.io.prompt("--> Enter the one-time passcode sent to your device")
        self.amazon_session.io.echo("")

        additional_attrs.update({"otpCode": otp,
                                 "rememberDevice": ""})
        self.data.update(additional_attrs)


class CaptchaForm(AuthForm):
    def __init__(self,
                 selector: str = CAPTCHA_1_FORM_SELECTOR,
                 error_selector: str = CAPTCHA_1_ERROR_SELECTOR,
                 solution_attr_key: str = "cvf_captcha_input") -> None:
        super().__init__(selector, error_selector)

        self.solution_attr_key = solution_attr_key

    def fill_form(self,
                  additional_attrs: Optional[Dict[str, Any]] = None) -> None:
        if not additional_attrs:
            additional_attrs = {}
        super().fill_form(additional_attrs)

        img_url = self.form.find_parent().select_one("img")["src"]
        if not img_url.startswith("http"):
            img_url = "{}{}".format(BASE_URL, img_url)
        solution = self._solve_captcha(img_url)

        additional_attrs.update({self.solution_attr_key: solution})
        self.data.update(additional_attrs)