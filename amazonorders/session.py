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
    MFA_DEVICE_SELECT_FORM_NAME = "auth-select-device-form"
    MFA_FORM_NAME = "auth-mfa-form"
    CAPTCHA_FORM_CLASS_NAME = "cvf-widget-form"

    def __init__(self,
                 amazon_username,
                 amazon_password,
                 debug=False) -> None:
        self.amazon_username = amazon_username
        self.amazon_password = amazon_password
        self.debug = debug

        self.session = Session()
        self.last_request = None
        self.last_request_parsed = None

    def request(self, method, url, **kwargs):
        if "headers" not in kwargs:
            kwargs["headers"] = {}
        kwargs["headers"].update(self.BASE_HEADERS)

        logger.debug("{} request to {}".format(method, url))

        self.last_request = self.session.request(method, url, **kwargs)
        self.last_request_parsed = BeautifulSoup(self.last_request.text, "html.parser")

        logger.debug("Response: {} - {}".format(self.last_request.url, self.last_request.status_code))

        if self.debug:
            page_name = self._get_page_from_url(self.last_request.url)
            with open(page_name, "w") as html_file:
                html_file.write(self.last_request.text)

        return self.last_request

    def get(self, url, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self.request("POST", url, **kwargs)

    def login(self):
        # TODO: pull captcha method up to here, in loop, process before any/each page
        self.get("https://www.amazon.com/gp/sign-in.html")

        # TODO: loop this and identify a "logged in" cookie (or some state identifier) to prove when the auth flow is actually done

        self._sign_in()

        if self._is_form_found(self.MFA_DEVICE_SELECT_FORM_NAME):
            self._mfa_device_select()

        if self._is_form_found(self.MFA_FORM_NAME):
            self._mfa_submit()

    def close(self):
        self.session.close()

    def _sign_in(self):
        self._process_captcha()

        data = self._build_from_form(self.SIGN_IN_FORM_NAME,
                                     {"email": self.amazon_username,
                                      "password": self.amazon_password,
                                      "rememberMe": "true"})

        self.post(self._get_form_action(self.SIGN_IN_FORM_NAME),
                  data=data)

        self._handle_errors()

    def _mfa_device_select(self):
        self._process_captcha()

        form = self.last_request_parsed.find("form",
                                             {"id": self.MFA_DEVICE_SELECT_FORM_NAME})
        contexts = form.find_all("input",
                                 {"name": "otpDeviceContext"})
        i = 1
        for field in contexts:
            print(str(i) + ": " + field.attrs["value"].strip())
            i += 1
        otp_device = int(input("Where would you like your one-time passcode sent? "))

        data = self._build_from_form(self.MFA_DEVICE_SELECT_FORM_NAME,
                                     {"otpDeviceContext": contexts[otp_device - 1].attrs["value"]})

        self.post(self._get_form_action(self.SIGN_IN_FORM_NAME),
                  data=data)

        self._handle_errors()

    def _mfa_submit(self):
        self._process_captcha()

        otp = input("Enter the one-time passcode sent to your device: ")

        # TODO: figure out why Amazon isn't respect rememberDevice
        data = self._build_from_form(self.MFA_FORM_NAME, {"otpCode": otp, "rememberDevice": ""})

        self.post(self._get_form_action(self.MFA_FORM_NAME),
                  data=data)

        self._handle_errors()

    def _process_captcha(self):
        # TODO: clean this up
        if not self._is_form_found(self.CAPTCHA_FORM_CLASS_NAME, "class"):
            return

        captcha = self.last_request_parsed.find("form", {"class": self.CAPTCHA_FORM_CLASS_NAME})

        if self.debug:
            page_name = self._get_page_from_url(self.last_request.url)
            with open(page_name, "w") as html_file:
                html_file.write(str(self.last_request_parsed))

        img_src = captcha.find("img", {"alt": "captcha"}).attrs["src"]
        img = self.session.get(img_src)
        Image.open(BytesIO(img.content)).show()

        captch_response = input("Enter the Captcha seen on the opened image: ")

        data = self._build_from_form(self.CAPTCHA_FORM_CLASS_NAME,
                                     {"cvf_captcha_input": captch_response},
                                     attr_name="class")

        self.last_request = self.post(
            self._get_form_action(self.CAPTCHA_FORM_CLASS_NAME, attr_name="class",
                                  prefix="https://www.amazon.com/ap/cvf/"),
            data=data)

        self._handle_errors("cvf-widget-alert", "class")

    def _build_from_form(self, form_name, additional_attrs, attr_name="name"):
        data = {}
        form = self.last_request_parsed.find("form", {attr_name: form_name})
        for field in form.find_all("input"):
            try:
                data[field["name"]] = field["value"]
            except:
                pass
        data.update(additional_attrs)
        return data

    def _get_form_action(self, form_name, attr_name="name", prefix=None):
        form = self.last_request_parsed.find("form", {attr_name: form_name})
        action = form.attrs.get("action", self.last_request.url)
        if prefix and "/" not in action:
            action = prefix + action
        return action

    def _is_form_found(self, form_name, attr_name="id"):
        return self.last_request_parsed.find("form", {attr_name: form_name}) is not None

    def _get_page_from_url(self, url):
        page_name = url.rsplit('/', 1)[-1].split("?")[0]
        if not page_name.endswith(".html"):
            page_name += ".html"

    def _handle_errors(self, error_div="auth-error-message-box", attr_name="id"):
        error_div = self.last_request_parsed.find("div",
                                                  {attr_name: error_div})
        if error_div:
            print("An error occurred: " + error_div.text.strip())
            sys.exit(1)
