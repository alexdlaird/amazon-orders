__author__ = "Alex Laird"
__copyright__ = "Copyright 2024, Alex Laird"
__version__ = "1.0.7"

### URLs for authentication
BASE_URL = "https://www.amazon.com"
SIGN_IN_URL = "{}/gp/sign-in.html".format(BASE_URL)
SIGN_IN_REDIRECT_URL = "{}/ap/signin".format(BASE_URL)
SIGN_OUT_URL = "{}/gp/sign-out.html".format(BASE_URL)

### URLs for Orders
ORDER_HISTORY_URL = "{}/your-orders/orders".format(BASE_URL)
ORDER_DETAILS_URL = "{}/gp/your-account/order-details".format(BASE_URL)

### Headers for authentication
BASE_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "max-age=0",
    "Content-Type": "application/x-www-form-urlencoded",
    "Origin": BASE_URL,
    "Referer": SIGN_IN_REDIRECT_URL,
    "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": "macOS",
    "Sec-Ch-Viewport-Width": "1393",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Viewport-Width": "1393",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

### CSS selectors for authentication
SIGN_IN_FORM_SELECTOR = "form[name='signIn']"
MFA_DEVICE_SELECT_FORM_SELECTOR = "form[id='auth-select-device-form']"
MFA_FORM_SELECTOR = "form[id='auth-mfa-form']"
CAPTCHA_1_FORM_SELECTOR = "form[class*='cvf-widget-form-captcha']"
CAPTCHA_2_FORM_SELECTOR = "form:has(input[id^='captchacharacters'])"
CAPTCHA_OTP_FORM_SELECTOR = "form[id='verification-code-form']"

### CSS selectors for Orders
ORDER_HISTORY_CARD_SELECTOR = "div[class*='order-card']:has(script)"
ORDER_DETAILS_DIV_SELECTOR = "div[id='orderDetails']"
NEXT_PAGE_LINK_SELECTOR = "ul[class*='a-pagination'] li[class*='a-last'] a"
