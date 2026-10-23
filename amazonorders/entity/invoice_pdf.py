__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import warnings
from typing import Any

from amazonorders.entity.invoice import Invoice


def __getattr__(name: str) -> Any:
    """
    ``InvoicePdf`` is deprecated, use :class:`~amazonorders.entity.invoice.Invoice` instead. To be removed in 5.0.
    """
    if name == "InvoicePdf":
        warnings.warn("InvoicePdf is deprecated and will be removed in 5.0. Use Invoice instead.",
                      DeprecationWarning, stacklevel=2)
        return Invoice

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
