__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import warnings

from amazonauth.contrib.waf.capsolver import (
    CapSolverWafForm,
)

__all__ = [
    "CapSolverWafForm",
]

warnings.warn("amazonorders.contrib.waf.capsolver is deprecated and will be removed in 6.0. Use "
              "amazonauth.contrib.waf.capsolver instead.", DeprecationWarning, stacklevel=2)
