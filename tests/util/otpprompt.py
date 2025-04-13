from typing import Any

import pyotp

from amazonorders.session import IODefault


class IODefaultWithOtpSecretKey(IODefault):
    """
    Attempt to auto-solve time-based OTP challenges using the OTP_SECRET_KEY environment variable.
    """

    def __init__(self, otp_secret_key) -> None:
        self.otp_secret_key = otp_secret_key

        print("--> IODefaultWithOtpSecretKey initialized, prompts will be solved using the "
              "time-based value in OTP_SECRET_KEY\n")

    def prompt(self,
               msg,
               **kwargs) -> Any:
        totp = pyotp.TOTP(self.otp_secret_key.replace(" ", ""))
        return totp.now()
