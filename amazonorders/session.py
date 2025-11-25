__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import json
import logging
import os
import time
from typing import Any, List, Optional, Dict
from urllib.parse import urlencode, urlparse

import requests
import requests.adapters
from requests import Response, Session
from requests.utils import dict_from_cookiejar

from amazonorders.conf import AmazonOrdersConfig, config_file_lock, cookies_file_lock, debug_output_file_lock
from amazonorders.exception import AmazonOrdersAuthError, AmazonOrdersError, AmazonOrdersAuthRedirectError
from amazonorders.forms import (AuthForm, CaptchaForm, JSAuthBlocker, MfaDeviceSelectForm, MfaForm,
                                SignInForm, ClaimForm, IntentForm)
from amazonorders import util
from amazonorders.util import AmazonSessionResponse

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
    this class means session data is maintained between requests. Session data may also persisted after each request,
    so it can also be maintained between separate instantiations of the class or application.

    To get started, call the :func:`login` function.
    """

    def __init__(self,
                 username: Optional[str] = None,
                 password: Optional[str] = None,
                 debug: bool = False,
                 io: IODefault = IODefault(),
                 config: Optional[AmazonOrdersConfig] = None,
                 auth_forms: Optional[List] = None,
                 otp_secret_key: Optional[str] = None,
                 base_url: Optional[str] = None) -> None:
        # If base_url is provided, set it as environment variable BEFORE creating config
        if base_url:
            # Set the environment variable to mimic the old behavior exactly
            os.environ["AMAZON_BASE_URL"] = base_url
        
        if not config:
            config = AmazonOrdersConfig()
        if not auth_forms:
            auth_forms = [ClaimForm(config),
                          IntentForm(config),
                          SignInForm(config),
                          MfaDeviceSelectForm(config),
                          MfaForm(config),
                          CaptchaForm(config),
                          CaptchaForm(config,
                                      config.selectors.CAPTCHA_2_FORM_SELECTOR,
                                      config.selectors.CAPTCHA_2_ERROR_SELECTOR,
                                      "field-keywords"),
                          MfaForm(config,
                                  config.selectors.CAPTCHA_OTP_FORM_SELECTOR),
                          JSAuthBlocker(config,
                                        config.constants.JS_ROBOT_TEXT_REGEX)]

        #: An Amazon username. Environment variable ``AMAZON_USERNAME`` will override passed in or config value.
        self.username: Optional[str] = os.environ.get("AMAZON_USERNAME") or username or config.username
        #: An Amazon password. Environment variable ``AMAZON_PASSWORD`` will override passed in or config value.
        self.password: Optional[str] = os.environ.get("AMAZON_PASSWORD") or password or config.password
        #: The secret key Amazon provides when manually adding a 2FA authenticator app. Setting this will allow
        #: one-time password challenges to be auto-solved. Environment variable ``AMAZON_OTP_SECRET_KEY`` will override
        #: passed in or config value.
        self.otp_secret_key: Optional[str] = (os.environ.get("AMAZON_OTP_SECRET_KEY") or otp_secret_key or
                                              config.otp_secret_key)

        #: Setting logger to ``DEBUG`` will send output to ``stderr`` and write an HTML file for all requests made
        #: on the session.
        self.debug: bool = debug
        if self.debug:
            logger.setLevel(logging.DEBUG)
        #: The I/O handler for echoes and prompts.
        self.io: IODefault = io
        #: The config to use.
        self.config: AmazonOrdersConfig = config
        
        #: The list of form implementations to use with authentication. If a value is passed for this when
        #: instantiating an AmazonSession, ensure that list is populated with the default form implementations.
        self.auth_forms: List[AuthForm] = auth_forms

        #: The shared session to be used across all requests.
        self.session: Session = self._create_session()
        #: If :func:`login` has been executed and successfully logged in the session.
        self.is_authenticated: bool = False

        cookie_dir = os.path.dirname(self.config.cookie_jar_path)
        with config_file_lock:
            if not os.path.exists(cookie_dir):
                os.makedirs(cookie_dir)
        with cookies_file_lock:
            if os.path.exists(self.config.cookie_jar_path):
                with open(self.config.cookie_jar_path, "r", encoding="utf-8") as f:
                    data = json.loads(f.read())
                    cookies = requests.utils.cookiejar_from_dict(data)
                    self.session.cookies.update(cookies)

    def request(self,
                method: str,
                url: str,
                persist_cookies: bool = False,
                **kwargs: Any) -> AmazonSessionResponse:
        """
        Execute the request against Amazon with base headers, parsing and storing the response.

        :param method: The request method to execute.
        :param url: The URL to execute ``method`` on.
        :param persist_cookies: If ``True``, cookies from the response will be persisted to a file.
        :param kwargs: Remaining ``kwargs`` will be passed to :func:`requests.request`.
        :return: The response from the executed request.
        """
        if "headers" not in kwargs:
            kwargs["headers"] = {}
        kwargs["headers"].update(self.config.constants.BASE_HEADERS)

        url_to_log = url
        if self.debug:
            if "params" in kwargs:
                encoded_params = urlencode(kwargs["params"])
                if encoded_params not in url:
                    url_to_log += "?" + encoded_params
            logger.debug(f"{method} request: {url_to_log}")

        response = self.session.request(method, url, **kwargs)
        amazon_session_response = AmazonSessionResponse(response,
                                                        self.config.bs4_parser)

        if persist_cookies:
            cookies = dict_from_cookiejar(self.session.cookies)
            with cookies_file_lock:
                with open(self.config.cookie_jar_path, "w", encoding="utf-8") as f:
                    f.write(json.dumps(cookies))

        if self.debug:
            url_str = ""
            if url_to_log != amazon_session_response.response.url:
                url_str = f" - (redirected) {amazon_session_response.response.url}"
            logger.debug(f"Response: {amazon_session_response.response.status_code}{url_str}")

            page_name = self._get_page_from_url(self.config.output_dir, amazon_session_response.response.url)
            with open(os.path.join(self.config.output_dir, page_name), "w",
                      encoding="utf-8") as html_file:
                logger.debug(
                    f"Response written to file: {html_file.name}")
                html_file.write(amazon_session_response.response.text)

        return amazon_session_response

    def get(self,
            url: str,
            **kwargs: Any) -> AmazonSessionResponse:
        """
        Perform a ``GET`` request.

        :param url: The URL to request.
        :param kwargs: Remaining ``kwargs`` will be passed to :func:`AmazonSession.request`.
        :return: The response from the executed request.
        """
        return self.request("GET", url, **kwargs)

    def post(self,
             url: str,
             **kwargs: Any) -> AmazonSessionResponse:
        """
        Perform a ``POST`` request.

        :param url: The URL to request.
        :param kwargs: Remaining ``kwargs`` will be passed to :func:`AmazonSession.request`.
        :return: The response from the executed request.
        """
        return self.request("POST", url, **kwargs)

    def auth_cookies_stored(self) -> bool:
        cookies = dict_from_cookiejar(self.session.cookies)
        for cookie in self.config.constants.COOKIES_SET_WHEN_AUTHENTICATED:
            if cookie not in cookies:
                return False
        return True

    def login(self) -> None:
        """
        Execute an Amazon login process. This will include the sign-in page, and may also include OTP (if 2FA is
        enabled for your account), Captcha challenges, and any other forms in
        :attr:`~amazonorders.session.AmazonSession.auth_forms`.

        If successful, ``is_authenticated`` will be set to ``True``.

        If existing session data is already persisted, calling this function will still attempt to reauthenticate to
        refresh it.
        """
        self._provision_cookies()

        last_response = self.get(self.config.constants.SIGN_IN_URL,
                                 params=self.config.constants.SIGN_IN_QUERY_PARAMS)

        self.is_authenticated = False
        form_found = False
        attempts = 0
        while not self.is_authenticated and attempts < self.config.max_auth_attempts:
            # TODO: BeautifulSoup doesn't let us query for #nav-item-signout, maybe because it's dynamic on the page,
            #  but we should find a better way to do this
            if self.auth_cookies_stored() or \
                    ("Hello, sign in" not in last_response.response.text and
                     "nav-item-signout" in last_response.response.text):
                self.is_authenticated = True
                break

            if attempts > 0:
                logger.debug(f"Retrying auth flow, attempt {attempts} in "
                             f"{self.config.auth_reattempt_wait} seconds ...")
                time.sleep(self.config.auth_reattempt_wait)

                # If a form was found on the last attempt, then we already have a response to evaluate from that,
                # otherwise (and/or if we were redirected back to the home page) re-start the auth flow for this
                # attempt
                if not form_found or last_response.response.url.rstrip("/") == self.config.constants.BASE_URL:
                    last_response = self.get(self.config.constants.SIGN_IN_URL,
                                             params=self.config.constants.SIGN_IN_QUERY_PARAMS)

                form_found = False

            form_response = self._process_forms(last_response)

            if form_response:
                last_response = form_response
                form_found = True

            if not form_found:
                self._raise_auth_error(last_response.response)

            attempts += 1

        if attempts == self.config.max_auth_attempts:
            raise AmazonOrdersAuthError(
                "Authentication attempts exhausted. If authentication is correct, "
                "try increasing AmazonOrdersConfig.max_auth_attempts.")

    def logout(self) -> None:
        """
        Logout and close the existing Amazon session and clear cookies.
        """
        self.get(self.config.constants.SIGN_OUT_URL, persist_cookies=True)
        self.session.close()
        self.session = self._create_session()

        # Ensure authentication cookies are unset, since we can get inconsistent persistence behavior otherwise
        with cookies_file_lock:
            cookies = dict_from_cookiejar(self.session.cookies)
            for cookie in self.config.constants.COOKIES_SET_WHEN_AUTHENTICATED:
                cookies.pop(cookie, None)
            with open(self.config.cookie_jar_path, "w") as f:
                f.write(json.dumps(cookies))

        self.is_authenticated = False

    def build_response_error(self,
                             response: Response) -> str:
        """
        Build an error message from the given response.

        :param response: The response to check and build a response.
        :return: The error message.
        """
        error_msg = f"The page {response.url} returned {response.status_code}."
        if 500 <= response.status_code < 600:
            error_msg += (" Amazon had an issue on their end, or may be temporarily blocking your requests. "
                          "Wait a bit before trying again.")
        return error_msg

    def check_response(self,
                       amazon_session_response: AmazonSessionResponse,
                       meta: Optional[Dict[str, Any]] = None) -> None:
        """
        Check the response to ensure it appears to be returning a valid response, and that it is still authenticated.
        We detect if authentication has expired by checking for redirects to the login page. Raise an error if the
        response is not going to contain the requested data for parsing.

        :param amazon_session_response: The response to check.
        :param meta: Metadata to be added to any errors raised.
        """
        if not amazon_session_response.response.ok:
            raise AmazonOrdersError(self.build_response_error(amazon_session_response.response), meta=meta)
        if (amazon_session_response.response.url.startswith(self.config.constants.SIGN_IN_URL) or
                (amazon_session_response.parsed and
                 amazon_session_response.parsed.select_one(self.config.selectors.SIGN_IN_FORM_SELECTOR) is not None)):
            logger.debug("Amazon redirect to login, so persisted AmazonSession will be logged out.")
            self.logout()
            raise AmazonOrdersAuthRedirectError("Amazon redirected to login. Call AmazonSession.login() to "
                                                "reauthenticate first.", meta=meta)

    def _get_page_from_url(self,
                           output_dir: str,
                           url: str) -> str:
        page_name = os.path.splitext(os.path.basename(urlparse(url).path))[0]
        if not page_name:
            page_name = "index"

        with debug_output_file_lock:
            i = 0
            filename_frmt = "{page_name}_{index}.html"
            while os.path.isfile(os.path.join(output_dir, filename_frmt.format(page_name=page_name, index=i))):
                i += 1
        return filename_frmt.format(page_name=page_name, index=i)

    def _raise_auth_error(self,
                          response: Response) -> None:
        if response.ok:
            error_msg = (f"This is an unknown page, or its parsed contents don't match a "
                         f"known auth flow. {response.url}")
        else:
            error_msg = self.build_response_error(response)

        if not self.debug:
            error_msg += "\n--> To capture the page to a file, set AmazonSession.debug=True."

        raise AmazonOrdersAuthError(error_msg)

    def _create_session(self) -> Session:
        session = Session()
        adapter = requests.adapters.HTTPAdapter(pool_connections=self.config.connection_pool_size,
                                                pool_maxsize=self.config.connection_pool_size)
        session.mount('https://', adapter)
        return session

    def _process_forms(self, last_response):
        for form in self.auth_forms:
            if form.select_form(self, last_response.parsed):
                form.fill_form()
                return form.submit(last_response.response)

        return None

    def _provision_cookies(self):
        last_response = None
        attempts = 0
        # We have to retry for stability here, to ensure Amazon returns us the desktop version of the site; if we
        # don't implement this logic, Amazon will sometimes return a mobile version of teh site (regardless of
        # User-Agent headers)
        while last_response is None or \
                (last_response.parsed.select_one(self.config.selectors.BAD_INDEX_SELECTOR) is not None
                 and attempts < self.config.max_cookie_attempts):
            if attempts > 0:
                logger.debug(f"Retrying cookie provisioning, attempt {attempts} in "
                             f"{self.config.cookie_reattempt_wait} seconds ...")
                time.sleep(self.config.cookie_reattempt_wait)

            # To provision initial, unauthenticated cookies, fetch the Amazon home page
            last_response = self.get(self.config.constants.BASE_URL)
            # We process forms just in case Amazon presents a Captcha challenge on unauthenticated URLs
            self._process_forms(last_response)

            attempts += 1

        if attempts == self.config.max_cookie_attempts:
            raise AmazonOrdersAuthError("Amazon is not returning a parsable home page. Try waiting a while, "
                                        "increasing AmazonOrdersConfig.max_cookie_attempts, or using a different IP "
                                        "address, as this one may be flagged as a bot.")
