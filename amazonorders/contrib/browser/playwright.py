__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import json
import logging
import os
import re
from abc import abstractmethod
from typing import Any, Dict, Optional, TYPE_CHECKING
from urllib.parse import urlparse

from bs4 import Tag
from requests import Response

from amazonorders.conf import AmazonOrdersConfig
from amazonorders.contrib.waf.base import _GOKU_PROPS_RE
from amazonorders.exception import AmazonOrdersError
from amazonorders.forms import AuthForm
from amazonorders.util import AmazonSessionResponse

if TYPE_CHECKING:
    from amazonorders.session import AmazonSession

logger = logging.getLogger(__name__)


class PlaywrightAuthForm(AuthForm):
    """
    Shared base for Playwright-based JavaScript challenge solvers. Subclasses implement
    :func:`select_form` to detect the challenge page and :func:`_is_challenge_url` to
    signal when navigation has completed.

    This base class handles the Playwright browser lifecycle, bidirectional cookie bridging
    between :mod:`requests` and the Playwright browser context, and re-fetching the final
    URL once the challenge resolves.

    Requires the ``[browser]`` extra: ``pip install amazon-orders[browser]``,
    then ``playwright install chromium``.
    """

    def __init__(self,
                 config: AmazonOrdersConfig) -> None:
        super().__init__(config, selector=None)
        #: Whether to launch the browser in headless mode. Defaults to ``True``.
        #: Set to ``False`` in subclasses that require user interaction.
        self.headless: bool = True

    def fill_form(self,
                  additional_attrs: Optional[Dict[str, Any]] = None) -> None:
        """JavaScript challenge pages have no ``<form>`` to populate; no-op override."""
        pass

    def submit(self,
               last_response: Response) -> AmazonSessionResponse:
        """
        Launch a headless browser, bridge the current session cookies into it,
        navigate to the challenge URL, wait for the challenge to resolve, harvest the
        resulting cookies back into the session, and re-fetch the final URL.

        :param last_response: The response that returned the JavaScript challenge page.
        :return: The :class:`~amazonorders.util.AmazonSessionResponse` from re-fetching
            the URL after the challenge resolves.
        :raises AmazonOrdersError: if the ``playwright`` package is not installed, if
            :func:`select_form` was not called first, or if the challenge does not resolve
            within the timeout.
        """
        if not self.amazon_session:
            raise AmazonOrdersError(
                "Call PlaywrightAuthForm.select_form() first."
            )  # pragma: no cover

        try:
            from playwright.sync_api import (  # type: ignore[import-not-found]
                sync_playwright,
                TimeoutError as PlaywrightTimeoutError,
            )
        except ImportError as e:
            raise AmazonOrdersError(
                f"{type(self).__name__} requires the [browser] extra. "
                "Install it with: `pip install amazon-orders[browser]`, then: `playwright install chromium`"
            ) from e

        debug = self.amazon_session.debug
        if debug:
            logger.setLevel(logging.DEBUG)

        message = "Info: A browser is handling a JavaScript authentication challenge."
        logger.info(message)
        self.amazon_session.io.echo(message)
        output_dir = self.config.output_dir if debug else None
        original_url = last_response.url

        browser_name = self.config.browser or "chromium"
        with sync_playwright() as pw:
            browser_launcher = getattr(pw, browser_name, None)
            if browser_launcher is None:
                raise AmazonOrdersError(
                    f"Unsupported browser: {browser_name!r}. "
                    f"Valid values: firefox, chromium."
                )
            browser = browser_launcher.launch(headless=self.headless)
            context = browser.new_context()

            self._inject_cookies(context, original_url)

            page = context.new_page()
            page.goto(original_url)
            logger.debug(f"Browser navigated to challenge URL: {page.url}")

            self._save_debug_snapshot(page, output_dir, "browser-challenge")
            self._on_challenge_page(page, context, output_dir)

            try:
                page.wait_for_url(
                    lambda url: not self._is_challenge_url(url, original_url),
                    timeout=30000
                )
            except PlaywrightTimeoutError as e:
                logger.debug(f"Browser timed out at URL: {page.url}")
                self._save_debug_snapshot(page, output_dir, "browser-timeout")
                browser.close()
                raise AmazonOrdersError(
                    "Browser timed out waiting for the JavaScript challenge to resolve."
                ) from e

            final_url = page.url
            logger.debug(f"Browser challenge resolved, final URL: {final_url}")
            self._save_debug_snapshot(page, output_dir, "browser-resolved")
            self._harvest_cookies(context)
            browser.close()

        response = self.amazon_session.get(final_url, persist_cookies=True)
        self.clear_form()
        return response

    def _on_challenge_page(self, page: Any, context: Any, output_dir: Optional[str]) -> None:
        """
        Hook called after navigating to the challenge page and saving the initial
        snapshot, but before waiting for the challenge URL to resolve. Override in
        subclasses to take additional action (e.g. solving an embedded CAPTCHA).

        :param page: The Playwright ``Page`` currently on the challenge URL.
        :param context: The Playwright ``BrowserContext``.
        :param output_dir: Directory for debug snapshots, or ``None`` when not in debug mode.
        """
        pass

    @abstractmethod
    def _is_challenge_url(self, url: str, original_url: str) -> bool:
        """
        Return ``True`` if ``url`` is still on the challenge page; ``False`` once
        the challenge has resolved and navigation may stop.

        :param url: The current browser URL.
        :param original_url: The URL of the page that first showed the challenge.
        :return: ``True`` while the challenge is active.
        """
        raise NotImplementedError  # pragma: no cover

    def _inject_cookies(self, context: Any, url: str) -> None:
        if not self.amazon_session:
            return  # pragma: no cover
        domain = urlparse(url).netloc
        playwright_cookies = []
        for cookie in self.amazon_session.session.cookies:
            playwright_cookies.append({
                "name": cookie.name,
                "value": cookie.value or "",
                "domain": cookie.domain or domain,
                "path": cookie.path or "/",
            })
        if playwright_cookies:
            context.add_cookies(playwright_cookies)

    def _harvest_cookies(self, context: Any) -> None:
        if not self.amazon_session:
            return  # pragma: no cover
        for pw_cookie in context.cookies():
            self.amazon_session.session.cookies.set(
                pw_cookie["name"],
                pw_cookie["value"],
                domain=pw_cookie.get("domain"),
                path=pw_cookie.get("path", "/"),
            )

    def _save_debug_snapshot(self, page: Any, output_dir: Optional[str], name: str) -> None:
        if not output_dir:
            return
        try:
            os.makedirs(output_dir, exist_ok=True)
            page.screenshot(path=os.path.join(output_dir, f"{name}.png"))
            with open(os.path.join(output_dir, f"{name}.html"), "w", encoding="utf-8") as f:
                f.write(page.content())
            logger.debug(f"Debug snapshot saved: {name} (url={page.url})")
        except Exception:
            logger.debug(f"Debug snapshot failed to save: {name}", exc_info=True)


class PlaywrightAcicForm(PlaywrightAuthForm):
    """
    Handles Amazon's ACIC (Amazon Challenge and Identity Component) JavaScript challenge
    by running it in a headless browser. If an embedded AWS WAF challenge is present on
    the ACIC page, it will be solved automatically using the first
    :class:`~amazonorders.contrib.waf.base.AwsWafForm` found in ``auth_forms_classes``.

    Detects the challenge via the ``#aa-challenge-page-captcha-container`` element and
    waits for navigation away from ``/ax/aaut/verify/ap/challenge``.

    Register via ``auth_forms_classes`` in :class:`~amazonorders.conf.AmazonOrdersConfig`:

    .. code-block:: yaml

        auth_forms_classes:
          - "amazonorders.contrib.browser.playwright.PlaywrightAcicForm"
    """

    def select_form(self,
                    amazon_session: "AmazonSession",
                    parsed: Tag) -> bool:
        """
        Detect an ACIC challenge page by the presence of
        ``#aa-challenge-page-captcha-container``.

        :param amazon_session: The ``AmazonSession`` on which to submit the form.
        :param parsed: The ``Tag`` for the page being inspected.
        :return: ``True`` if an ACIC challenge was detected, ``False`` otherwise.
        """
        self.amazon_session = amazon_session
        return bool(parsed.find(id="aa-challenge-page-captcha-container"))

    def _on_challenge_page(self, page: Any, context: Any, output_dir: Optional[str]) -> None:
        self._try_solve_embedded_waf(page, context, output_dir)

    def _try_solve_embedded_waf(self, page: Any, context: Any, output_dir: Optional[str]) -> bool:
        """
        If the ACIC challenge page contains an embedded AWS WAF challenge, solve it
        using the first :class:`~amazonorders.contrib.waf.base.AwsWafForm` found in
        ``amazon_session.auth_forms``, inject the resulting ``aws-waf-token`` cookie
        into the browser context, and reload the page.

        :param page: The Playwright ``Page`` on the ACIC challenge URL.
        :param context: The Playwright ``BrowserContext``.
        :param output_dir: Directory for debug snapshots, or ``None``.
        :return: ``True`` if a WAF token was obtained and injected, ``False`` otherwise.
        """
        try:
            from playwright.sync_api import TimeoutError as PlaywrightTimeoutError  # type: ignore[import-not-found]
        except ImportError:
            return False  # pragma: no cover

        try:
            page.wait_for_function("() => typeof window.gokuProps !== 'undefined'", timeout=8000)
        except PlaywrightTimeoutError:
            logger.debug("No window.gokuProps in ACIC page — no embedded WAF challenge to solve.")
            return False

        try:
            goku = page.evaluate("() => window.gokuProps")
            challenge_script = page.evaluate(
                "() => (Array.from(document.querySelectorAll('script[src]'))"
                ".find(s => s.src.includes('awswaf.com')) || {}).src || null"
            )
        except Exception:
            logger.debug("Failed to extract WAF props from ACIC page.", exc_info=True)
            return False

        if not goku or not challenge_script:
            logger.debug("Incomplete WAF props in ACIC page — goku=%r, script=%r.", goku, challenge_script)
            return False

        if not self.amazon_session:
            return False  # pragma: no cover

        from amazonorders.contrib.waf.base import AwsWafForm
        waf_form = next(
            (f for f in self.amazon_session.auth_forms if isinstance(f, AwsWafForm)),
            None,
        )
        if not waf_form:
            logger.debug("Embedded WAF challenge found but no AwsWafForm configured — skipping solve.")
            return False

        try:
            token = waf_form._solve_token(page.url, goku, challenge_script)
        except Exception:
            logger.debug("WAF solver raised an exception solving embedded ACIC CAPTCHA.", exc_info=True)
            return False

        message = f"Info: Solved embedded WAF challenge via {waf_form.PROVIDER_NAME}."
        logger.info(message)
        self.amazon_session.io.echo(message)

        domain = urlparse(page.url).netloc
        context.add_cookies([{
            "name": "aws-waf-token",
            "value": token,
            "domain": f".{domain}",
            "path": "/",
        }])
        page.reload(wait_until="load")
        logger.debug("Reloaded ACIC page after WAF token injection.")
        self._save_debug_snapshot(page, output_dir, "browser-waf-injected")
        return True

    def _is_challenge_url(self, url: str, original_url: str) -> bool:
        return "/ax/aaut/verify/ap/challenge" in url


class PlaywrightJSAuthForm(PlaywrightAuthForm):
    """
    Handles Amazon's JavaScript bot-detection challenge page by running it in a
    headless browser. This is a best-effort form; effectiveness
    depends on whether the challenge can be resolved by a real browser without a visual puzzle.

    Detects the challenge via :attr:`~amazonorders.constants.Constants.JS_ROBOT_TEXT_REGEX`
    and waits for navigation away from the original challenge URL path.

    Register via ``auth_forms_classes`` in :class:`~amazonorders.conf.AmazonOrdersConfig`:

    .. code-block:: yaml

        auth_forms_classes:
          - "amazonorders.contrib.browser.playwright.PlaywrightJSAuthForm"
    """

    def __init__(self,
                 config: AmazonOrdersConfig) -> None:
        super().__init__(config)
        #: The regex used to detect the JavaScript bot-detection page text.
        self.regex: str = config.constants.JS_ROBOT_TEXT_REGEX

    def select_form(self,
                    amazon_session: "AmazonSession",
                    parsed: Tag) -> bool:
        """
        Detect a JavaScript bot-detection page by matching
        :attr:`~amazonorders.constants.Constants.JS_ROBOT_TEXT_REGEX` against the page text.

        :param amazon_session: The ``AmazonSession`` on which to submit the form.
        :param parsed: The ``Tag`` for the page being inspected.
        :return: ``True`` if a JavaScript bot challenge was detected, ``False`` otherwise.
        """
        self.amazon_session = amazon_session
        return bool(re.search(self.regex, parsed.text))

    def _is_challenge_url(self, url: str, original_url: str) -> bool:
        return url.split("?")[0] == original_url.split("?")[0]


class PlaywrightManualWafForm(PlaywrightAuthForm):
    """
    Handles Amazon's AWS WAF JavaScript challenge by opening a **visible** browser
    window so the user can solve the CAPTCHA manually. Once the challenge
    resolves and the browser navigates away, cookies are harvested back into the
    session automatically.

    Because it opens a browser window it requires a display and a user at the
    keyboard, making it suitable for local/interactive use but not for headless
    servers or CI.

    Detects the challenge via the ``window.gokuProps`` blob and the
    ``challenge.js`` script tag (same signals as
    :class:`~amazonorders.contrib.waf.base.AwsWafForm`), and waits for navigation
    away from the original challenge URL path.

    Register via ``auth_forms_classes`` in :class:`~amazonorders.conf.AmazonOrdersConfig`:

    .. code-block:: yaml

        auth_forms_classes:
          - amazonorders.contrib.browser.playwright.PlaywrightManualWafForm
    """

    def __init__(self,
                 config: AmazonOrdersConfig) -> None:
        super().__init__(config)
        self.headless = False

    def select_form(self,
                    amazon_session: "AmazonSession",
                    parsed: Tag) -> bool:
        """
        Detect an AWS WAF challenge page by matching the ``window.gokuProps``
        blob and the ``challenge.js`` script tag.

        :param amazon_session: The ``AmazonSession`` on which to submit the form.
        :param parsed: The ``Tag`` for the page being inspected.
        :return: ``True`` if a WAF challenge was detected, ``False`` otherwise.
        """
        self.amazon_session = amazon_session

        match = _GOKU_PROPS_RE.search(str(parsed))
        if not match:
            return False
        try:
            json.loads(match.group(1))
        except (json.JSONDecodeError, ValueError):
            return False

        challenge_tag = parsed.select_one('script[src*="awswaf.com"]')
        return challenge_tag is not None and isinstance(challenge_tag.get("src"), str)

    def _on_challenge_page(self, page: Any, context: Any, output_dir: Optional[str]) -> None:
        message = (
            "Info: A browser window has opened — solve the CAPTCHA, then return here when done."
        )
        logger.info(message)
        if self.amazon_session:
            self.amazon_session.io.echo(message)

    def _is_challenge_url(self, url: str, original_url: str) -> bool:
        return url.split("?")[0] == original_url.split("?")[0]
