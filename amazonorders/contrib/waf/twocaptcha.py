__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import warnings

from amazonauth.contrib.waf.twocaptcha import (
    TwoCaptchaWafForm,
)

__all__ = [
    "TwoCaptchaWafForm",
]

warnings.warn("amazonorders.contrib.waf.twocaptcha is deprecated and will be removed in 6.0. Use "
              "amazonauth.contrib.waf.twocaptcha instead.", DeprecationWarning, stacklevel=2)
