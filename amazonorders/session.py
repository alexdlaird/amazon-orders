import logging
import sys
from io import BytesIO

from PIL import Image
from bs4 import BeautifulSoup
from requests import Session

__author__ = "Alex Laird"
__copyright__ = "Copyright 2023, Alex Laird"
__version__ = "0.0.2"

logger = logging.getLogger(__name__)


class AmazonSession:
    BASE_HEADERS = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "max-age=0",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://www.amazon.com",
        "Referer": "https://www.amazon.com/ap/signin",
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
    CAPTCHA_DIV_ID = "cvf-page-content"
    CAPTCHA_FORM_CLASS = "cvf-widget-form"

    def __init__(self,
                 username,
                 password,
                 debug=False,
                 max_auth_attempts=10) -> None:
        self.username = username
        self.password = password

        self.debug = debug
        self.max_auth_attempts = max_auth_attempts

        self.session = Session()
        self.last_response = None
        self.last_response_parsed = None
        self.is_authenticated = False

    def request(self, method, url, **kwargs):
        if "headers" not in kwargs:
            kwargs["headers"] = {}
        kwargs["headers"].update(self.BASE_HEADERS)

        logger.debug("{} request to {}".format(method, url))

        self.last_response = self.session.request(method, url, **kwargs)
        self.last_response_parsed = BeautifulSoup(self.last_response.text, "html.parser")

        logger.debug("Response: {} - {}".format(self.last_response.url, self.last_response.status_code))

        if self.debug:
            page_name = self._get_page_from_url(self.last_response.url)
            with open(page_name, "w") as html_file:
                html_file.write(self.last_response.text)

        return self.last_response

    def get(self, url, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self.request("POST", url, **kwargs)

    def login(self):
        self.get("https://www.amazon.com/gp/sign-in.html")

        attempts = 0
        while not self.is_authenticated and attempts < self.max_auth_attempts:
            if self._is_form_found(self.SIGN_IN_FORM_NAME, attr_name="name"):
                self._sign_in()
            elif self._is_form_found(self.CAPTCHA_FORM_CLASS, attr_name="class"):
                self._captcha_submit()
            elif self._is_form_found(self.MFA_DEVICE_SELECT_FORM_ID):
                self._mfa_device_select()
            elif self._is_form_found(self.MFA_FORM_ID):
                self._mfa_submit()
            else:
                print("An error occurred, this is an unknown page.")

                sys.exit(1)

            # TODO: implement an escape mechanism for a race condition here

            # TODO: figure out why BeautifulSoup isn't finding #nav-item-signout as an ID using `find()`
            if ("Your Account" in self.last_response.text and
                    "Sign Out" in self.last_response.text and
                    "nav-item-signout" in self.last_response.text):
                self.is_authenticated = True
            else:
                attempts += 1

        if attempts == self.max_auth_attempts:
            print("Max authentication flow attempts reached.")

            sys.exit(1)

    def close(self):
        self.session.close()

    def _sign_in(self):
        data = self._build_from_form(self.SIGN_IN_FORM_NAME,
                                     {"email": self.username,
                                      "password": self.password,
                                      "rememberMe": "true"},
                                     attr_name="name")

        self.post(self._get_form_action(self.SIGN_IN_FORM_NAME),
                  data=data)

        self._handle_errors(critical=True)

    def _mfa_device_select(self):
        form = self.last_response_parsed.find("form",
                                              {"id": self.MFA_DEVICE_SELECT_FORM_ID})
        contexts = form.find_all("input",
                                 {"name": "otpDeviceContext"})
        i = 1
        for field in contexts:
            print("{}: {}".format(i, field.attrs["value"].strip()))
            i += 1
        otp_device = int(input("Where would you like your one-time passcode sent? "))

        data = self._build_from_form(self.MFA_DEVICE_SELECT_FORM_ID,
                                     {"otpDeviceContext": contexts[otp_device - 1].attrs["value"]})

        self.post(self._get_form_action(self.SIGN_IN_FORM_NAME),
                  data=data)

        self._handle_errors()

    def _mfa_submit(self):
        otp = input("Enter the one-time passcode sent to your device: ")

        # TODO: figure out why Amazon isn't respect rememberDevice
        data = self._build_from_form(self.MFA_FORM_ID,
                                     {"otpCode": otp, "rememberDevice": ""})

        self.post(self._get_form_action(self.MFA_FORM_ID),
                  data=data)

        self._handle_errors()

    def _captcha_submit(self):
        captcha = self.last_response_parsed.find("div", {"id": self.CAPTCHA_DIV_ID})

        img_src = captcha.find("img", {"alt": "captcha"}).attrs["src"]
        img_response = self.session.get(img_src)
        img = Image.open(BytesIO(img_response.content))
        img.show()

        captcha_response = input("Enter the Captcha seen on the opened image: ")

        data = self._build_from_form(self.CAPTCHA_FORM_CLASS,
                                     {"cvf_captcha_input": captcha_response},
                                     attr_name="class")

        self.post(self._get_form_action(self.CAPTCHA_FORM_CLASS,
                                        attr_name="class",
                                        prefix="https://www.amazon.com/ap/cvf/"),
                  data=data)

        self._handle_errors("cvf-widget-alert", "class")

    def _build_from_form(self, form_name, additional_attrs, attr_name="id"):
        data = {}
        form = self.last_response_parsed.find("form", {attr_name: form_name})
        for field in form.find_all("input"):
            try:
                data[field["name"]] = field["value"]
            except:
                pass
        data.update(additional_attrs)
        return data

    def _get_form_action(self, form_name, attr_name="name", prefix=None):
        form = self.last_response_parsed.find("form", {attr_name: form_name})
        action = form.attrs.get("action", self.last_response.url)
        if prefix and "/" not in action:
            action = prefix + action
        return action

    def _is_form_found(self, form_name, attr_name="id"):
        return self.last_response_parsed.find("form", {attr_name: form_name}) is not None

    def _get_page_from_url(self, url):
        page_name = url.rsplit("/", 1)[-1].split("?")[0]
        if not page_name.endswith(".html"):
            page_name += ".html"
        return page_name

    def _handle_errors(self, error_div="auth-error-message-box", attr_name="id", critical=False):
        error_div = self.last_response_parsed.find("div",
                                                   {attr_name: error_div})
        if error_div:
            print("An error occurred: {}".format(error_div.text.strip()))

            if critical:
                sys.exit(1)
