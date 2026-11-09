__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import warnings

from amazonauth.contrib.waf.anticaptcha import (
    AntiCaptchaWafForm,
)

__all__ = [
    "AntiCaptchaWafForm",
]

warnings.warn("amazonorders.contrib.waf.anticaptcha is deprecated and will be removed in 6.0. Use "
              "amazonauth.contrib.waf.anticaptcha instead.", DeprecationWarning, stacklevel=2)
