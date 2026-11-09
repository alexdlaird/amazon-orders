__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import warnings

from amazonauth.region_data import REGION_SITES, RegionSite

__all__ = [
    "RegionSite",
    "REGION_SITES",
]

warnings.warn("amazonorders.region_data is deprecated and will be removed in 6.0. Use "
              "amazonauth.region_data instead.", DeprecationWarning, stacklevel=2)
