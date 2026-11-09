__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import warnings

from amazonauth.contrib.waf.base import (
    AwsWafForm,
)

__all__ = [
    "AwsWafForm",
]

warnings.warn("amazonorders.contrib.waf.base is deprecated and will be removed in 6.0. Use "
              "amazonauth.contrib.waf.base instead.", DeprecationWarning, stacklevel=2)
