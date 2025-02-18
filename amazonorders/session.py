__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import json
import logging
import os
from typing import Any, List, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup, Tag
from requests import Response, Session
from requests.utils import dict_from_cookiejar

from amazonorders.conf import AmazonOrdersConfig
from amazonorders.exception import AmazonOrdersAuthError
from amazonorders.forms import CaptchaForm, MfaDeviceSelectForm, MfaForm, SignInForm, AuthForm

logger = logging.getLogger(__name__)


class IODefault:
    """
    Handles input/output from the application. By default, this uses console commands, but
    this class exists so that it can be overridden when constructing an :class:`AmazonSession`
    if input/output should be handled another way.
    """

    def echo(self,
             msg: str,
             **kwargs: Any) -> None:
        """
        Echo a message to the console.

        :param msg: The data to send to output.
        :param kwargs: Unused by the default implementation.
        """
        print(msg)

    def prompt(self,
               msg: str,
               type: Optional[Any] = None,
               **kwargs: Any) -> Any:
        """
        Prompt to the console for user input.

        :param msg: The data to use as the input prompt.
        :param type: Unused by the default implementation.
        :param kwargs: Unused by the default implementation.
        :return: The user input result.
        """
        for choice in kwargs.get("choices", []):
            self.echo(choice, **kwargs)

        return input(f"--> {msg}: ")


class AmazonSession:
    """
    An interface for interacting with Amazon and authenticating an underlying :class:`requests.Session`. Utilizing
    this class means session data is maintained between requests. Session data is also persisted after each request,
    meaning it will also be maintained between separate instantiations of the class or application.

    To get started, call the :func:`login` function.
    """

    def __init__(self,
                 username: Optional[str],
                 password: Optional[str],
                 debug: bool = False,
                 io: IODefault = IODefault(),
                 config: Optional[AmazonOrdersConfig] = None,
                 auth_forms: Optional[List] = None) -> None:
        if not config:
            config = AmazonOrdersConfig()
        if not auth_forms:
            auth_forms = [SignInForm(config),
                          MfaDeviceSelectForm(config),
                          MfaForm(config),
                          CaptchaForm(config),
                          CaptchaForm(config,
                                      config.selectors.CAPTCHA_2_FORM_SELECTOR,
                                      config.selectors.CAPTCHA_2_ERROR_SELECTOR,
                                      "field-keywords"),
                          MfaForm(config,
                                  config.selectors.CAPTCHA_OTP_FORM_SELECTOR)]

        #: An Amazon username.
        self.username: Optional[str] = username
        #: An Amazon password.
        self.password: Optional[str] = password

        #: Set logger ``DEBUG``, send output to ``stderr``, and write an HTML file for requests made on the session.
        self.debug: bool = debug
        if self.debug:
            logger.setLevel(logging.DEBUG)
        #: The I/O handler for echoes and prompts.
        self.io: IODefault = io
        #: The AmazonOrdersConfig to use.
        self.config: AmazonOrdersConfig = config
        #: The list of form implementations to use with authentication. If a value is passed for this when
        #: instantiating an AmazonSession, ensure that list is populated with the default form implementations.
        self.auth_forms: List[AuthForm] = auth_forms

        #: The shared session to be used across all requests.
        self.session: Session = Session()
        #: The last response executed on the Session.
        self.last_response: Response = Response()
        #: A parsed representation of the last response executed on the Session.
        self.last_response_parsed: Tag = Tag(name="html")
        #: If :func:`login` has been executed and successfully logged in the session.
        self.is_authenticated: bool = False

        cookie_dir = os.path.dirname(self.config.cookie_jar_path)
        if not os.path.exists(cookie_dir):
            os.makedirs(cookie_dir)
        if os.path.exists(self.config.cookie_jar_path):
            with open(self.config.cookie_jar_path, "r", encoding="utf-8") as f:
                data = json.loads(f.read())
                cookies = requests.utils.cookiejar_from_dict(data)
                self.session.cookies.update(cookies)

    def request(self,
                method: str,
                url: str,
                **kwargs: Any) -> Response:
        """
        Execute the request against Amazon with base headers, parsing and storing the response
        and persisting response cookies.

        :param method: The request method to execute.
        :param url: The URL to execute ``method`` on.
        :param kwargs: Remaining ``kwargs`` will be passed to :func:`requests.request`.
        :return: The Response from the executed request.
        """
        if "headers" not in kwargs:
            kwargs["headers"] = {}
        kwargs["headers"].update(self.config.constants.BASE_HEADERS)

        logger.debug(f"{method} request to {url}")

        self.last_response = self.session.request(method, url, **kwargs)
        self.last_response_parsed = BeautifulSoup(self.last_response.text,
                                                  self.config.bs4_parser)

        cookies = dict_from_cookiejar(self.session.cookies)
        if os.path.exists(self.config.cookie_jar_path):
            os.remove(self.config.cookie_jar_path)
        with open(self.config.cookie_jar_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(cookies))

        logger.debug(f"Response: {self.last_response.url} - {self.last_response.status_code}")

        if self.debug:
            page_name = self._get_page_from_url(self.config.output_dir, self.last_response.url)
            with open(os.path.join(self.config.output_dir, page_name), "w",
                      encoding="utf-8") as html_file:
                logger.debug(
                    f"Response written to file: {html_file.name}")
                html_file.write(self.last_response.text)

        return self.last_response

    def get(self,
            url: str,
            **kwargs: Any) -> Response:
        """
        Perform a GET request.

        :param url: The URL to GET on.
        :param kwargs: Remaining ``kwargs`` will be passed to :func:`AmazonSession.request`.
        :return: The Response from the executed GET request.
        """
        return self.request("GET", url, **kwargs)

    def post(self,
             url: str,
             **kwargs: Any) -> Response:
        """
        Perform a POST request.

        :param url: The URL to POST on.
        :param kwargs: Remaining ``kwargs`` will be passed to :func:`AmazonSession.request`.
        :return: The Response from the executed POST request.
        """
        return self.request("POST", url, **kwargs)

    def auth_cookies_stored(self) -> bool:
        cookies = dict_from_cookiejar(self.session.cookies)
        return cookies.get("session-token") and cookies.get("x-main")

    def login(self) -> None:
        """
        Execute an Amazon login process. This will include the sign-in page, and may also include Captcha challenges
        and OTP pages (of 2FA authentication is enabled on your account).

        If successful, ``is_authenticated`` will be set to ``True``.

        Session cookies are persisted, and if existing session data is found during this auth flow, it will be
        skipped entirely and flagged as authenticated.
        """
        self.get(self.config.constants.SIGN_IN_URL)

        # If our local session data is stale, Amazon will redirect us to the signin page
        if (self.auth_cookies_stored() and
                self.last_response.url.split("?")[0] == self.config.constants.SIGN_IN_REDIRECT_URL):
            self.logout()
            self.get(self.config.constants.SIGN_IN_URL)

        attempts = 0
        while not self.is_authenticated and attempts < self.config.max_auth_attempts:
            # TODO: BeautifulSoup doesn't let us query for #nav-item-signout, maybe because it's dynamic on the page,
            #  but we should find a better way to do this
            if self.auth_cookies_stored() or \
                    ("Hello, sign in" not in self.last_response.text and
                     "nav-item-signout" in self.last_response.text):
                self.is_authenticated = True
                break

            form_found = False
            for form in self.auth_forms:
                if form.select_form(self, self.last_response_parsed):
                    form_found = True

                    form.fill_form()
                    form.submit()

                    break

            if not form_found:
                self._raise_auth_error()

            attempts += 1

        if attempts == self.config.max_auth_attempts:
            raise AmazonOrdersAuthError("Max authentication flow attempts reached.")

    def logout(self) -> None:
        """
        Logout and close the existing Amazon session and clear cookies.
        """
        self.get(self.config.constants.SIGN_OUT_URL)

        if os.path.exists(self.config.cookie_jar_path):
            os.remove(self.config.cookie_jar_path)

        self.session.close()
        self.session = Session()

        self.is_authenticated = False

    def _get_page_from_url(self,
                           output_dir: str,
                           url: str) -> str:
        page_name = os.path.splitext(os.path.basename(urlparse(url).path))[0]
        if not page_name:
            page_name = "index"

        i = 0
        filename_frmt = "{page_name}_{index}.html"
        while os.path.isfile(os.path.join(output_dir, filename_frmt.format(page_name=page_name, index=i))):
            i += 1
        return filename_frmt.format(page_name=page_name, index=i)

    def _raise_auth_error(self) -> None:
        debug_str = " To capture the page to a file, set the `debug` flag." if not self.debug else ""
        if self.last_response.ok:
            error_msg = (f"An error occurred, this is an unknown page, or its parsed contents don't match a "
                         f"known auth flow: {self.last_response.url}.{debug_str}")
        else:
            error_msg = "An error occurred, the page {url} returned {status_code}."
            if 500 <= self.last_response.status_code < 600:
                error_msg += (" Amazon had an issue on their end, or may be temporarily blocking your requests. "
                              "Wait a bit before trying again.")

            error_msg = error_msg.format(url=self.last_response.url,
                                         status_code=self.last_response.status_code) + debug_str

        raise AmazonOrdersAuthError(error_msg)
