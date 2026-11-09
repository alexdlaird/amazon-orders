__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import warnings

from amazonauth.forms import (
    AcicAuthBlocker,
    AuthForm,
    CaptchaForm,
    ClaimForm,
    IntentForm,
    JSAuthBlocker,
    MfaDeviceSelectForm,
    MfaForm,
    PasskeyForm,
    SignInForm,
)

__all__ = [
    "AuthForm",
    "SignInForm",
    "ClaimForm",
    "PasskeyForm",
    "IntentForm",
    "MfaDeviceSelectForm",
    "MfaForm",
    "CaptchaForm",
    "AcicAuthBlocker",
    "JSAuthBlocker",
]

warnings.warn("amazonorders.forms is deprecated and will be removed in 6.0. Use "
              "amazonauth.forms instead.", DeprecationWarning, stacklevel=2)
