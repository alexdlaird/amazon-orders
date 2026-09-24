__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

from datetime import date

from amazonorders.conf import AmazonOrdersConfig
from amazonorders.exception import AmazonOrdersError
from amazonorders.localization import DeDE, EnUS, get_locale
from tests.unittestcase import UnitTestCase


class TestLocalization(UnitTestCase):
    def test_locale_by_domain(self):
        self.assertIsInstance(AmazonOrdersConfig(data={"domain": "amazon.com"}).constants.LOCALE, EnUS)
        self.assertIsInstance(AmazonOrdersConfig(data={"domain": "amazon.co.uk"}).constants.LOCALE, EnUS)
        self.assertIsInstance(AmazonOrdersConfig(data={"domain": "amazon.de"}).constants.LOCALE, DeDE)
        self.assertIsInstance(AmazonOrdersConfig(data={"domain": "https://www.amazon.de"}).constants.LOCALE, DeDE)

    def test_locale_config_override(self):
        config = AmazonOrdersConfig(data={"domain": "amazon.de", "locale": "en-US"})
        self.assertIsInstance(config.constants.LOCALE, EnUS)

        config = AmazonOrdersConfig(data={"domain": "amazon.com", "locale": "de-de"})
        self.assertIsInstance(config.constants.LOCALE, DeDE)

    def test_get_locale_unknown(self):
        with self.assertRaises(AmazonOrdersError):
            get_locale("xx-XX")

    def test_de_currency_symbol(self):
        self.assertEqual("€", AmazonOrdersConfig(data={"domain": "amazon.de"}).constants.CURRENCY_SYMBOL)

    def test_de_parse_date(self):
        locale = DeDE()

        self.assertEqual(date(2026, 9, 6), locale.parse_date("06. September 2026"))
        self.assertEqual(date(2026, 9, 6), locale.parse_date("6. Sept. 2026"))
        self.assertEqual(date(2026, 3, 1), locale.parse_date("1. März 2026"))
        self.assertEqual(date(2026, 3, 1), locale.parse_date("1. Mär. 2026"))
        self.assertEqual(date(2026, 5, 15), locale.parse_date("15. Mai 2026"))
        self.assertEqual(date(2026, 12, 24), locale.parse_date("24.12.2026"))
        self.assertEqual(date(2026, 9, 25),
                         locale.parse_date("Widerruf, Rückgabe oder Ersatz: Berechtigt bis zum 25. September 2026"))

    def test_de_months(self):
        locale = DeDE()

        self.assertEqual(9, locale.MONTHS["september"])
        self.assertEqual(9, locale.MONTHS["sept"])
        self.assertEqual(3, locale.MONTHS["mär"])
        self.assertEqual(set(range(1, 13)), set(locale.MONTHS.values()))
        self.assertEqual({}, dict(EnUS().MONTHS))
        with self.assertRaises(TypeError):
            locale.MONTHS["foo"] = 1  # type: ignore[index]

    def test_de_parse_date_never_guesses(self):
        locale = DeDE()

        with self.assertLogs("amazonorders.localization", level="WARNING"):
            self.assertIsNone(locale.parse_date("Zugestellt: 26. August"))
        with self.assertLogs("amazonorders.localization", level="WARNING"):
            self.assertIsNone(locale.parse_date("vom 1. August 2026 bis 3. August 2026"))
        with self.assertLogs("amazonorders.localization", level="WARNING"):
            self.assertIsNone(locale.parse_date("31. Februar 2026"))
        self.assertIsNone(locale.parse_date("Rückgabe oder Widerruf"))
        self.assertIsNone(locale.parse_date("August 2026"))
        self.assertIsNone(locale.parse_date(""))

    def test_de_parse_date_same_date_twice(self):
        self.assertEqual(date(2026, 9, 6), DeDE().parse_date("06. September 2026 (06.09.2026)"))

    def test_de_parse_currency(self):
        locale = DeDE()

        self.assertEqual(7.43, locale.parse_currency("7,43 €"))
        self.assertEqual(25.29, locale.parse_currency("25,29€"))
        self.assertEqual(-39.93, locale.parse_currency("-39,93 €"))
        self.assertEqual(-39.93, locale.parse_currency("−39,93 €"))
        self.assertEqual(1234.56, locale.parse_currency("1.234,56 €"))
        self.assertEqual(1234.56, locale.parse_currency("EUR 1.234,56"))
        self.assertEqual(1234, locale.parse_currency("1.234 €"))
        self.assertEqual(0.0, locale.parse_currency("0,00 €"))
        self.assertEqual(0.0, locale.parse_currency("Kostenlos"))

    def test_de_parse_currency_rejects_other_formats(self):
        locale = DeDE()

        with self.assertLogs("amazonorders.localization", level="WARNING"):
            self.assertIsNone(locale.parse_currency("1,234.56 €"))
        with self.assertLogs("amazonorders.localization", level="WARNING"):
            self.assertIsNone(locale.parse_currency("Summe 7,43 €"))

    def test_de_format_currency(self):
        constants = AmazonOrdersConfig(data={"domain": "amazon.de"}).constants

        self.assertEqual("7,43 €", constants.format_currency(7.43))
        self.assertEqual("1.234,50 €", constants.format_currency(1234.5))
        self.assertEqual("-1.234,56 €", constants.format_currency(-1234.56))
        self.assertEqual("0,00 €", constants.format_currency(-0.001))

    def test_en_us_unchanged(self):
        locale = EnUS()

        self.assertEqual(1234.56, locale.parse_currency("$1,234.56"))
        self.assertEqual(-1.99, locale.parse_currency("($1.99)"))
        self.assertEqual(0.0, locale.parse_currency("FREE"))
        self.assertEqual(date(2024, 8, 23), locale.parse_date("August 23, 2024"))
        self.assertEqual("-$1,234.56", locale.format_currency(-1234.56, "$"))
