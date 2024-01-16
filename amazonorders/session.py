import logging
import os
from io import BytesIO

from PIL import Image
from bs4 import BeautifulSoup
from requests import Session

__author__ = "Alex Laird"
__copyright__ = "Copyright 2024, Alex Laird"
__version__ = "0.0.5"

from amazonorders.exception import AmazonOrdersAuthError

logger = logging.getLogger(__name__)

BASE_URL = "https://www.amazon.com"
BASE_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "max-age=0",
    "Content-Type": "application/x-www-form-urlencoded",
    "Origin": BASE_URL,
    "Referer": "{}/ap/signin".format(BASE_URL),
    "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": "macOS",
    "Sec-Ch-Viewport-Width": "1393",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Viewport-Width": "1393",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}
SIGN_IN_FORM_NAME = "signIn"
MFA_DEVICE_SELECT_FORM_ID = "auth-select-device-form"
MFA_FORM_ID = "auth-mfa-form"
CAPTCHA_1_DIV_ID = "cvf-page-content"
CAPTCHA_1_FORM_CLASS = "cvf-widget-form"
CAPTCHA_2_INPUT_ID = "captchacharacters"


class AmazonSession:
    def __init__(self,
                 username,
                 password,
                 debug=False,
                 max_auth_attempts=10) -> None:
        self.username = username
        self.password = password

        self.debug = debug
        if self.debug:
            logger.setLevel(logging.DEBUG)
        self.max_auth_attempts = max_auth_attempts

        self.session = Session()
        self.last_response = None
        self.last_response_parsed = None
        self.is_authenticated = False

    def request(self, method, url, **kwargs):
        if "headers" not in kwargs:
            kwargs["headers"] = {}
        kwargs["headers"].update(BASE_HEADERS)

        logger.debug("{} request to {}".format(method, url))

        self.last_response = self.session.request(method, url, **kwargs)
        self.last_response_parsed = BeautifulSoup(self.last_response.text,
                                                  "html.parser")

        logger.debug("Response: {} - {}".format(self.last_response.url,
                                                self.last_response.status_code))

        if self.debug:
            page_name = self._get_page_from_url(self.last_response.url)
            with open(page_name, "w", encoding="utf-8") as html_file:
                logger.debug("Response written to file: {}".format(html_file.name))
                html_file.write(self.last_response.text)

        return self.last_response

    def get(self, url, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self.request("POST", url, **kwargs)

    def login(self):
        self.get("{}/gp/sign-in.html".format(BASE_URL))

        attempts = 0
        while not self.is_authenticated and attempts < self.max_auth_attempts:
            if self._is_field_found(SIGN_IN_FORM_NAME):
                self._sign_in()
            elif self._is_field_found(CAPTCHA_1_FORM_CLASS, field_key="class"):
                self._captcha_1_submit()
            elif self.last_response_parsed.find("input",
                                                id=lambda value: value and value.startswith(CAPTCHA_2_INPUT_ID)):
                self._captcha_2_submit()
            elif self._is_field_found(MFA_DEVICE_SELECT_FORM_ID, field_key="id"):
                self._mfa_device_select()
            elif self._is_field_found(MFA_FORM_ID, field_key="id"):
                self._mfa_submit()
            else:
                raise AmazonOrdersAuthError(
                    "An error occurred, this is an unknown page: {}. To capture the page to a file, set the `debug` flag.".format(
                        self.last_response.url))

            if "Hello, sign in" not in self.last_response.text and "nav-item-signout" in self.last_response.text:
                self.is_authenticated = True
            else:
                attempts += 1

        if attempts == self.max_auth_attempts:
            raise AmazonOrdersAuthError(
                "Max authentication flow attempts reached.")

    def logout(self):
        self.get("{}/gp/sign-out.html".format(BASE_URL))

        self.close()

    def close(self):
        self.session.close()

    def _sign_in(self):
        form = self.last_response_parsed.find("form", {"name": SIGN_IN_FORM_NAME})
        data = self._build_from_form(form,
                                     additional_attrs={"email": self.username,
                                                       "password": self.password,
                                                       "rememberMe": "true"})

        self.request(form.attrs.get("method", "GET"),
                     self._get_form_action(form),
                     data=data)

        self._handle_errors(critical=True)

    def _mfa_device_select(self):
        form = self.last_response_parsed.find("form",
                                              {"id": MFA_DEVICE_SELECT_FORM_ID})
        contexts = form.find_all("input", {"name": "otpDeviceContext"})
        i = 1
        for field in contexts:
            print("{}: {}".format(i, field.attrs["value"].strip()))
            i += 1
        otp_device = int(
            input("Where would you like your one-time passcode sent? "))

        form = self.last_response_parsed.find("form", id=MFA_DEVICE_SELECT_FORM_ID)
        data = self._build_from_form(form,
                                     additional_attrs={"otpDeviceContext":
                                                           contexts[otp_device - 1].attrs[
                                                               "value"]})

        self.request(form.attrs.get("method", "GET"),
                     self._get_form_action(form),
                     data=data)

        self._handle_errors()

    def _mfa_submit(self):
        otp = input("Enter the one-time passcode sent to your device: ")

        # TODO: figure out why Amazon doesn't respect rememberDevice
        form = self.last_response_parsed.find("form", id=MFA_FORM_ID)
        data = self._build_from_form(form,
                                     additional_attrs={"otpCode": otp, "rememberDevice": ""})

        self.request(form.attrs.get("method", "GET"),
                     self._get_form_action(form),
                     data=data)

        self._handle_errors()

    def _captcha_1_submit(self):
        captcha = self.last_response_parsed.find("div", {"id": CAPTCHA_1_DIV_ID})

        img_src = captcha.find("img", {"alt": "captcha"}).attrs["src"]
        img_response = self.session.get(img_src)
        img = Image.open(BytesIO(img_response.content))
        img.show()

        captcha_response = input("Enter the Captcha seen on the opened image: ")

        form = self.last_response_parsed.find("form", {"class": CAPTCHA_1_FORM_CLASS})
        data = self._build_from_form(form,
                                     additional_attrs={"cvf_captcha_input": captcha_response})

        self.request(form.attrs.get("method", "GET"),
                     self._get_form_action(form,
                                           prefix="{}/ap/cvf/".format(BASE_URL)),
                     data=data)

        self._handle_errors("cvf-widget-alert", "class")

    def _captcha_2_submit(self):
        form = self.last_response_parsed.find("input",
                                              id=lambda value: value and value.startswith(
                                                  CAPTCHA_2_INPUT_ID)).find_parent("form")

        img_src = form.find("img").attrs["src"]
        img_response = self.session.get(img_src)
        img = Image.open(BytesIO(img_response.content))
        img.show()

        captcha_response = input("Enter the Captcha seen on the opened image: ")

        data = self._build_from_form(form,
                                     additional_attrs={"field-keywords": captcha_response})

        self.request(form.attrs.get("method", "GET"),
                     self._get_form_action(form,
                                           prefix=BASE_URL),
                     params=data)

        self._handle_errors("a-alert-info", "class")

    def _build_from_form(self, form, additional_attrs=None):
        data = {}
        for field in form.find_all("input"):
            try:
                data[field["name"]] = field["value"]
            except:
                pass
        if additional_attrs:
            data.update(additional_attrs)
        return data

    def _get_form_action(self, form, prefix=None):
        action = form.attrs.get("action")
        if not action:
            action = self.last_response.url
        if prefix and not action.startswith("http"):
            action = prefix + action
        return action

    def _is_field_found(self, field_value, field_type="form", field_key="name"):
        return self.last_response_parsed.find(field_type, {
            field_key: field_value}) is not None

    def _get_page_from_url(self, url):
        page_name = url.rsplit("/", 1)[-1].split("?")[0]
        page_name.strip(".html")
        i = 0
        while os.path.isfile("{}_{}".format(page_name, 0)):
            i += 1
        return "{}_{}.html".format(page_name, i)

    def _handle_errors(self, error_div="auth-error-message-box", attr_name="id",
                       critical=False):
        error_div = self.last_response_parsed.find("div",
                                                   {attr_name: error_div})
        if error_div:
            error_msg = "An error occurred: {}".format(error_div.text.strip())

            if critical:
                raise AmazonOrdersAuthError(error_msg)
            else:
                print(error_msg)
