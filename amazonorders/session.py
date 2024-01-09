import os
import sys
from io import BytesIO

from PIL import Image
from bs4 import BeautifulSoup
from requests import Session

__author__ = "Alex Laird"
__copyright__ = "Copyright 2023, Alex Laird"
__version__ = "0.0.2"


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

    def __init__(self) -> None:
        self.session = Session()
        self.last_request = None
        self.last_request_parsed = None

    def request(self, method, url, **kwargs):
        if "headers" not in kwargs:
            kwargs["headers"] = {}
        kwargs["headers"].update(self.BASE_HEADERS)

        return self.session.request(method, url, **kwargs)

    def get(self, url, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self.request("POST", url, **kwargs)

    def login(self):
        self._get_sign_in()

        self._post_sign_in()

        self._process_mfa_select()

        self._process_otp()

    def close(self):
        self.session.close()

    def _get_sign_in(self):
        self.last_request = self.session.get(
            "https://www.amazon.com/gp/sign-in.html",
            headers=self.BASE_HEADERS)
        print(self.last_request.url + " - " + str(self.last_request.status_code))
        html = self.last_request.text
        with open("signin.html", "w") as text_file:
            text_file.write(html)
        self.last_request_parsed = BeautifulSoup(html, "html.parser")

    def _post_sign_in(self):
        self._process_captcha()

        form = self.last_request_parsed.find("form", {"name": "signIn"})
        data = {}
        for field in form.find_all("input"):
            try:
                data[field["name"]] = field["value"]
            except:
                pass
        data["email"] = os.environ["AMAZON_USERNAME"]
        data["password"] = os.environ["AMAZON_PASSWORD"]
        data["rememberMe"] = "true"

        print("Action: " + form.attrs["action"])
        self.last_request = self.session.post(form.attrs["action"],
                                              headers=self.BASE_HEADERS,
                                              cookies=self.last_request.cookies,
                                              data=data)
        print(self.last_request.url + " - " + str(self.last_request.status_code))
        html = self.last_request.text
        with open("post-signin.html", "w") as text_file:
            text_file.write(html)
        self.last_request_parsed = BeautifulSoup(html, "html.parser")

        error_div = self.last_request_parsed.find("div",
                                                  {"id": "auth-error-message-box"})
        if error_div:
            print("An error occurred: " + error_div.text)
            sys.exit(1)

    def _process_mfa_select(self):
        self._process_captcha()

        form = self.last_request_parsed.find("form",
                                             {"id": "auth-select-device-form"})
        data = {}
        if form:
            print("OTP detected, select device:")
            for field in form.find_all("input"):
                try:
                    data[field["name"]] = field["value"]
                except:
                    pass
            contexts = self.last_request_parsed.find_all("input",
                                                         {"name": "otpDeviceContext"})
            i = 1
            for field in contexts:
                print(str(i) + ": " + field.attrs["value"])
                i += 1
            otpSelect = int(input("Which one? "))
            data["otpDeviceContext"] = contexts[otpSelect - 1].attrs["value"]

            action = form.attrs["action"]
            if not action:
                action = self.last_request.url
            print("Action: " + action)
            self.last_request = self.session.post(action,
                                                  headers=self.BASE_HEADERS,
                                                  cookies=self.last_request.cookies,
                                                  data=data)
            print(self.last_request.url + " - " + str(self.last_request.status_code))
            html = self.last_request.text
            with open("new-otp.html", "w") as text_file:
                text_file.write(html)
            self.last_request_parsed = BeautifulSoup(html, "html.parser")

            error_div = self.last_request_parsed.find("div", {
                "id": "auth-error-message-box"})
            if error_div:
                print("An error occurred: " + error_div.text)
                sys.exit(1)

    def _process_captcha(self):
        captcha = self.last_request_parsed.find("div", {"id": "cvf-page-content"})
        if captcha:
            with open("post-signin-captcha.html", "w") as text_file:
                text_file.write(str(self.last_request_parsed))

            img_src = captcha.find("img", {"alt": "captcha"}).attrs["src"]
            img = self.session.get(img_src)
            Image.open(BytesIO(img.content)).show()

            form = captcha.find("form", {"class": "cvf-widget-form"})
            data = {}
            for field in form.find_all("input"):
                try:
                    data[field["name"]] = field["value"]
                except:
                    pass
            data["cvf_captcha_input"] = input(
                "Enter the Captcha from the image opened: ")
            action = form.attrs["action"]
            if not action:
                action = self.last_request.url
            if "/" not in action:
                action = "https://www.amazon.com/ap/cvf/" + action
            print("Action: " + action)
            self.last_request = self.session.post(action,
                                                  headers=self.BASE_HEADERS,
                                                  cookies=self.last_request.cookies,
                                                  data=data)
            print(self.last_request.url + " - " + str(self.last_request.status_code))
            html = self.last_request.text
            with open("post-signin-post-captcha.html", "w") as text_file:
                text_file.write(html)
            self.last_request_parsed = BeautifulSoup(html, "html.parser")

            error_div = self.last_request_parsed.find("div",
                                                      {"class": "cvf-widget-alert"})
            if error_div:
                print("An error occurred: " + error_div.text)
                sys.exit(1)

    def _process_otp(self):
        self._process_captcha()

        form = self.last_request_parsed.find("form", {"id": "auth-mfa-form"})
        data = {}
        if form:
            print("OTP detected, answer prompt")
            for field in form.find_all("input"):
                try:
                    data[field["name"]] = field["value"]
                except:
                    pass
            otp = input("OTP code: ")
            data["otpCode"] = otp
            data["rememberDevice"] = ""

            print("Action: " + form.attrs["action"])
            self.last_request = self.session.post(form.attrs["action"],
                                                  headers=self.BASE_HEADERS,
                                                  cookies=self.last_request.cookies,
                                                  data=data)
            print(self.last_request.url + " - " + str(self.last_request.status_code))
            html = self.last_request.text
            with open("post-signin-mfa.html", "w") as text_file:
                text_file.write(html)
            self.last_request_parsed = BeautifulSoup(html, "html.parser")

            error_div = self.last_request_parsed.find("div", {
                "id": "auth-error-message-box"})
            if error_div:
                print("An error occurred: " + error_div.text)
                sys.exit(1)
