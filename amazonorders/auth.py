import os
import sys
from io import BytesIO
from PIL import Image

from bs4 import BeautifulSoup
from requests import Session

__author__ = "Alex Laird"
__copyright__ = "Copyright 2023, Alex Laird"
__version__ = "0.0.2"

HEADERS = {
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

_session = None


def get_session():
    global _session, cookies

    if not _session:
        _session = Session()

    return _session


def close_session():
    global _session

    if _session:
        _session.close()

        _session = None


def _get_sign_in(session):
    r = session.get("https://www.amazon.com/gp/sign-in.html",
                    headers=HEADERS)
    print(r.url + " - " + str(r.status_code))
    html = r.text
    with open("signin.html", "w") as text_file:
        text_file.write(html)
    return r, BeautifulSoup(html, "html.parser")


def _post_sign_in(r, session, soup):
    r, soup = _process_captcha(r, session, soup)

    data = {}
    form = soup.find("form", {"name": "signIn"})
    for field in form.find_all("input"):
        try:
            data[field["name"]] = field["value"]
        except:
            pass
    data["email"] = os.environ["AMAZON_USERNAME"]
    data["password"] = os.environ["AMAZON_PASSWORD"]
    data["rememberMe"] = "true"

    print("Action: " + form.attrs["action"])
    r = session.post(form.attrs["action"],
                     headers=HEADERS,
                     cookies=r.cookies,
                     data=data)
    print(r.url + " - " + str(r.status_code))
    html = r.text
    with open("post-signin.html", "w") as text_file:
        text_file.write(html)
    soup = BeautifulSoup(html, "html.parser")

    error_div = soup.find("div", {"id": "auth-error-message-box"})
    if error_div:
        print("An error occurred: " + error_div.text)
        sys.exit(1)

    return r, soup


def _process_mfa_select(r, session, soup):
    r, soup = _process_captcha(r, session, soup)

    data = {}
    form = soup.find("form", {"id": "auth-select-device-form"})
    if form:
        print("OTP detected, select device:")
        for field in form.find_all("input"):
            try:
                data[field["name"]] = field["value"]
            except:
                pass
        contexts = soup.find_all("input", {"name": "otpDeviceContext"})
        i = 1
        for field in contexts:
            print(str(i) + ": " + field.attrs["value"])
            i += 1
        otpSelect = int(input("Which one? "))
        data["otpDeviceContext"] = contexts[otpSelect - 1].attrs["value"]

        action = form.attrs["action"]
        if not action:
            action = r.url
        print("Action: " + action)
        r = session.post(action,
                         headers=HEADERS,
                         cookies=r.cookies,
                         data=data)
        print(r.url + " - " + str(r.status_code))
        html = r.text
        with open("new-otp.html", "w") as text_file:
            text_file.write(html)
        soup = BeautifulSoup(html, "html.parser")

        error_div = soup.find("div", {"id": "auth-error-message-box"})
        if error_div:
            print("An error occurred: " + error_div.text)
            sys.exit(1)

    return r, soup


def _process_captcha(r, session, soup):
    captcha = soup.find("div", {"id": "cvf-page-content"})
    if captcha:
        with open("post-signin-captcha.html", "w") as text_file:
            text_file.write(str(soup))

        img_src = captcha.find("img", {"alt": "captcha"}).attrs["src"]
        img = session.get(img_src)
        Image.open(BytesIO(img.content)).show()

        form = captcha.find("form", {"class": "cvf-widget-form"})
        data = {}
        for field in form.find_all("input"):
            try:
                data[field["name"]] = field["value"]
            except:
                pass
        data["cvf_captcha_input"] = input("Enter the Captcha from the image opened: ")
        action = form.attrs["action"]
        if not action:
            action = r.url
        if "/" not in action:
            action = "https://www.amazon.com/ap/cvf/" + action
        print("Action: " + action)
        r = session.post(action,
                         headers=HEADERS,
                         cookies=r.cookies,
                         data=data)
        print(r.url + " - " + str(r.status_code))
        html = r.text
        with open("post-signin-post-captcha.html", "w") as text_file:
            text_file.write(html)
        soup = BeautifulSoup(html, "html.parser")

        error_div = soup.find("div", {"class": "cvf-widget-alert"})
        if error_div:
            print("An error occurred: " + error_div.text)
            sys.exit(1)

    return r, soup


def _process_otp(r, session, soup):
    r, soup = _process_captcha(r, session, soup)

    data = {}
    form = soup.find("form", {"id": "auth-mfa-form"})
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
        r = session.post(form.attrs["action"],
                         headers=HEADERS,
                         cookies=r.cookies,
                         data=data)
        print(r.url + " - " + str(r.status_code))
        html = r.text
        with open("post-signin-mfa.html", "w") as text_file:
            text_file.write(html)
        soup = BeautifulSoup(html, "html.parser")

        error_div = soup.find("div", {"id": "auth-error-message-box"})
        if error_div:
            print("An error occurred: " + error_div.text)
            sys.exit(1)

    return r, soup


def login():
    session = get_session()

    r, soup = _get_sign_in(session)

    r, soup = _post_sign_in(r, session, soup)

    r, soup = _process_mfa_select(r, session, soup)

    return _process_otp(r, session, soup)
