__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import warnings

from amazonauth.contrib.browser.playwright import (
    BODY_TEXT_LENGTH_JS,
    PlaywrightAcicForm,
    PlaywrightAuthForm,
    PlaywrightBrowserLauncher,
    PlaywrightBrowserLogin,
    PlaywrightJSAuthForm,
    PlaywrightManualWafForm,
    SIGN_IN_POLL_INTERVAL_MS,
    SIGN_IN_PREFILL_TIMEOUT_MS,
    SIGN_IN_SETTLE_MS,
)

__all__ = [
    "BODY_TEXT_LENGTH_JS",
    "SIGN_IN_POLL_INTERVAL_MS",
    "SIGN_IN_SETTLE_MS",
    "SIGN_IN_PREFILL_TIMEOUT_MS",
    "PlaywrightBrowserLauncher",
    "PlaywrightAuthForm",
    "PlaywrightAcicForm",
    "PlaywrightJSAuthForm",
    "PlaywrightManualWafForm",
    "PlaywrightBrowserLogin",
]

warnings.warn("amazonorders.contrib.browser.playwright is deprecated and will be removed in 6.0. Use "
              "amazonauth.contrib.browser.playwright instead.", DeprecationWarning, stacklevel=2)
