# Changelog

All notable changes to this project will be documented in this file.

This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://github.com/alexdlaird/amazon-orders/compare/3.2.14...HEAD)

## [3.2.14](https://github.com/alexdlaird/amazon-orders/compare/3.2.13...3.2.14) - 2025-03-08

### Added

- `Order.free_shipping` field.

### Fixed

- Duplicate currency symbol in CLI output for Order details.

## [3.2.13](https://github.com/alexdlaird/amazon-orders/compare/3.2.12...3.2.13) - 2025-03-02

### Fixed

- Broken parsing when `Transaction.order_number` is not selected from `<a>` tag.
- Parsing issue with `Transaction.seller` in pending Transactions.

## [3.2.12](https://github.com/alexdlaird/amazon-orders/compare/3.2.11...3.2.12) - 2025-02-24

### Fixed

- `Order.coupon_savings` and `Order.promotion_applied` may have multiple values, sum if so.

## [3.2.11](https://github.com/alexdlaird/amazon-orders/compare/3.2.10...3.2.11) - 2025-02-23

### Added

- `Order.coupon_savings` field, which is now parsed alongside other subtotals.

## [3.2.10](https://github.com/alexdlaird/amazon-orders/compare/3.2.9...3.2.10) - 2025-02-21

### Fixed

- When `full_details=True` is set and an Order's details page can't be parsed, the partial Order will still be returned (along with a warning that it's not fully populated).
- Broken parsing when Amazon renders a completely empty Transaction div.

## [3.2.9](https://github.com/alexdlaird/amazon-orders/compare/3.2.8...3.2.9) - 2025-02-19

### Added

- Further support for Amazon's new `data-component` tag on order ID and order date.

## [3.2.8](https://github.com/alexdlaird/amazon-orders/compare/3.2.7...3.2.8) - 2025-02-18

### Added

- Dependency and documentation improvements (including fixing links to BeautifulSoup entities).

## [3.2.7](https://github.com/alexdlaird/amazon-orders/compare/3.2.6...3.2.7) - 2025-02-17

### Added

- Fixes for parsing Amazon Fresh and Whole Foods Market orders, so they no longer need to be skipped (but their Items and Shipments will still be empty).

## [3.2.6](https://github.com/alexdlaird/amazon-orders/compare/3.2.5...3.2.6) - 2025-02-17

### Added

- Add generic integration tests for Transactions, now in weekly run.
- Other test improvements.

### Fixed

- Broken parsing when Transaction is pending.

## [3.2.5](https://github.com/alexdlaird/amazon-orders/compare/3.2.4...3.2.5) - 2025-02-12

### Fixed

- Parsing errors on gift cards totals and broken item links due to changes in Amazon.com DOM.

## [3.2.4](https://github.com/alexdlaird/amazon-orders/compare/3.2.3...3.2.4) - 2025-02-11

### Added

- `Order.promotion_applied` field, which is now parsed alongside other subtotals.

### Fixed

- Broken parsing of Whole Foods Market orders, these are now skipped.
- Parsing issue on `Order.order_number` and `Order.order_placed` due to changes in Amazon.com DOM.

## [3.2.3](https://github.com/alexdlaird/amazon-orders/compare/3.2.2...3.2.3) - 2025-02-06

### Added

- `bs4_parser` to the config file, which allows for overriding the parser used by BeautifulSoup, defaulting to the built-in `html.parser`.

## [3.2.2](https://github.com/alexdlaird/amazon-orders/compare/3.2.1...3.2.2) - 2025-01-28

### Added

- Stability improvements.

### Fixed

- Broken parsing of Amazon Fresh orders, these are now skipped.

## [3.2.1](https://github.com/alexdlaird/amazon-orders/compare/3.2.0...3.2.1) - 2024-11-08

### Fixed

- Issues with parsing Items and Shipments using the new `data-component`, selectors made more precise.
- Transactions use `util` selector methods, so consistent use of trying a list of selectors is maintained.

## [3.2.0](https://github.com/alexdlaird/amazon-orders/compare/3.1.0...3.2.0) - 2024-11-07

### Added

- Support for [Transactions](https://amazon-orders.readthedocs.io/api.html#amazonorders.entity.transaction.Transactions).
- Improvements for currency parsing.

### Changed

- Renamed `AmazonOrderError` to [`AmazonOrdersError`](https://amazon-orders.readthedocs.io/api.html#amazonorders.exception.AmazonOrdersEntityError).

## [3.1.0](https://github.com/alexdlaird/amazon-orders/compare/3.0.0...3.1.0) - 2024-11-04

### Added

- `python-dateutil` as a dependency is now used to parse dates, increasing the types of dates supported and eliminating manually splittings strings apart to find the date.
- `parse_date` to [`simple_parse`](https://amazon-orders.readthedocs.io/api.html#amazonorders.entity.parsable.Parsable.simple_parse).
- Cleanup for parsing payment method.
- Cleanup for parsing currency totals.
- Stability improvements.

### Changed

- Replaced `simple_parse`'s `link` arg with a more generic [`attr_name`](https://amazon-orders.readthedocs.io/api.html#amazonorders.entity.parsable.Parsable.simple_parse) (pass "href" or "src" as the value for the same behavior).
- `Order.payment_method_last_4` parses to an `int`, and now uses `safe_simple_parse`.

## [3.0.0](https://github.com/alexdlaird/amazon-orders/compare/2.0.3...3.0.0) - 2024-11-03

### Added

- Retry support to CLI when stale session fails to authenticate the first time.
- Improvements to exception messages on auth failures.
- Documentation improvements.

### Fixed

- Several parsing issues with the implementation of Amazon's new `data-component` tag.

### Removed

- `Order.order_shipped_date`, this cannot be consistently parsed from Amazon.
- `Order.refund_completed_date`, this cannot be consistently parsed from Amazon.

## [2.0.3](https://github.com/alexdlaird/amazon-orders/compare/2.0.2...2.0.3) - 2024-11-01

### Added

- Further support for Amazon's new `data-component` tag on order price, seller, and return eligibility, and fixing an issue with `Shipment` parsing.
- [`Parsable.to_date()`](https://amazon-orders.readthedocs.io/api.html#amazonorders.entity.parsable.Parsable.to_date) attempts multiple date formats.

### Fixed

- An issue with `Shipment`s parsing with Amazon's new `data-component`.

## [2.0.2](https://github.com/alexdlaird/amazon-orders/compare/2.0.1...2.0.2) - 2024-10-30

### Added

- `item_class` to the config file, which allows for overriding the `Item` class.
- Support for Amazon's new `data-component` tag on order subtotals.
- Build and stability improvements.

### Fixed

- The return value of `Order._parse_recipient()` is now optional, so parsing doesn't break digital goods without a shipping address.
- Redundant order ID logic to parse from the URI, simplified to consistently fetch from page.
- Support for order details selector on Amazon's legacy digital orders page.

## [2.0.1](https://github.com/alexdlaird/amazon-orders/compare/2.0.0...2.0.1) - 2024-10-27

### Added

Build and stability improvements.

## [2.0.0](https://github.com/alexdlaird/amazon-orders/compare/1.1.4...2.0.0) - 2024-10-26

### Added

- Support for Amazon's new `data-component` tags.
- `order_class` to the config file, which allows for overriding the `Order` class.
- `shipment_class` to the config file, which allows for overriding the `Shipment` class.
- Simplified integration tests to more quickly catch regressions.
- Bug fixes and stability improvements.

### Changed

- Removed global constants in `amazonorders.constants`. Now [`amazonorders.constants.Constants`](https://amazon-orders.readthedocs.io/api.html#amazonorders.constants.Constants) and [`amazonorders.selectors.Selectors`](https://amazon-orders.readthedocs.io/api.html#amazonorders.selectors.Selectors) classes are used, can be overridden with `constants_class` and `selectors_class` in the config file.

### Removed

- `session.AUTH_FORMS`. Pass [`auth_forms` when instantiating `AmazonSession`](https://amazon-orders.readthedocs.io/api.html#amazonorders.session.AmazonSession) instead.

## [1.1.4](https://github.com/alexdlaird/amazon-orders/compare/1.1.3...1.1.4) - 2024-06-07

### Added

- Improvements to helper functions for simple parsing support (`prefix_split`, parsing improvements, and more).
- Bug fixes and stability improvements.

## [1.1.3](https://github.com/alexdlaird/amazon-orders/compare/1.1.2...1.1.3) - 2024-06-05

### Added

- Config is now managed through a YAML file, with support for CLI overrides.
- Documentation improvements.

### Fixed

- Parsing issues due to change in Amazon.com DOM.
- Other minor bug fixes.

## [1.1.2](https://github.com/alexdlaird/amazon-orders/compare/1.1.1...1.1.2) - 2024-05-18

### Added

- Build improvements.
- Documentation improvements.
- Test improvements (Amazon no longer provides the `condition` field in many cases).

### Fixed

- Raise `AmazonOrdersNotFoundError` when Order is not found.
- Prices with thousands separator now parse properly.

### Changed

- [AmazonOrder.debug](https://amazon-orders.readthedocs.io/api.html#amazonorders.orders.AmazonOrders.debug)
  defaults to the value
  of [AmazonSession.debug](https://amazon-orders.readthedocs.io/api.html#amazonorders.session.AmazonSession.debug)
  if an override is not passed.

## [1.1.1](https://github.com/alexdlaird/amazon-orders/compare/1.0.16...1.1.1) - 2024-04-09

### Added

- Build improvements.
- Test improvements.

### Changed

- Renamed `kwarg` passed to `IODefault.prompt()` from `captcha_img_url` to `img_url`.
- Renamed `kwarg` passed to `IODefault.prompt()` from `mfa_device_select_choices` to `choices`.

## [1.0.16](https://github.com/alexdlaird/amazon-orders/compare/1.0.15...1.0.16) - 2024-03-24

### Added

- `constants.BASE_URL` will look for the environment variable `AMAZON_BASE_URL` before defaulting
  to "https://www.amazon.com".
- Build and stability improvements.

## [1.0.15](https://github.com/alexdlaird/amazon-orders/compare/1.0.14...1.0.15) - 2024-03-05

### Added

- Build and style improvements.
- Documentation improvements.
- `pytest` to streamline running unit and integration tests.

### Removed

- `conf.VERSION`, moved all version information to `amazonorders/__init__.py`. Get package version
  with `from amazonorders import __version__` instead.

## [1.0.14](https://github.com/alexdlaird/amazon-orders/compare/1.0.13...1.0.14) - 2024-02-26

### Added

- Build improvements.

### Changed

- Renamed `make check-style` to `make check`.

## [1.0.13](https://github.com/alexdlaird/amazon-orders/compare/1.0.12...1.0.13) - 2024-02-20

### Added

- `login` command to CLI.
- If `--username` or `--password` are not given and no stored session, CLI will prompt.
- Build improvements.

### Fixed

- Issue where `Parsable` objects could not be pickled due to BeautifulSoup `Tag` objects.

## [1.0.12](https://github.com/alexdlaird/amazon-orders/compare/1.0.11...1.0.12) - 2024-02-11

### Added

- Relative dependency pinning in `pyproject.toml`.
- Style and stability improvements (check `flake8` with `make check-style`).

### Removed

- `requirements.txt` files to streamline in to `pyproject.toml`.

## [1.0.11](https://github.com/alexdlaird/amazon-orders/compare/1.0.10...1.0.11) - 2024-02-09

### Changed

- `version` command now includes Python version and doesn't printer banner, for easy parsing.

## [1.0.10](https://github.com/alexdlaird/amazon-orders/compare/1.0.9...1.0.10) - 2024-02-08

### Added

- Migrated to `pyproject.toml`.

## [1.0.9](https://github.com/alexdlaird/amazon-orders/compare/1.0.8...1.0.9) - 2024-02-07

### Added

- [AuthForm](https://amazon-orders.readthedocs.io/api.html#amazonorders.forms.AuthForm)'s now
  passes `captcha_img_url` to its `prompt()` fallback for Captcha, useful for
  overriding [IODefault](https://amazon-orders.readthedocs.io/api.html#amazonorders.session.IODefault).
- [MfaDeviceSelectForm](https://amazon-orders.readthedocs.io/api.html#amazonorders.forms.MfaDeviceSelectForm)
  now passes `mfa_device_select_choices` to `prompt()`, useful for
  overrides [IODefault](https://amazon-orders.readthedocs.io/api.html#amazonorders.session.IODefault).
- Documentation improvements.

## [1.0.8](https://github.com/alexdlaird/amazon-orders/compare/1.0.7...1.0.8) - 2024-01-30

### Added

- Stability improvements.

## [1.0.7](https://github.com/alexdlaird/amazon-orders/compare/1.0.6...1.0.7) - 2024-01-29

### Added

- [AuthForm](https://amazon-orders.readthedocs.io/api.html#amazonorders.forms.AuthForm) abstract class, and
  migrated all auth flow items to subclasses of this class.
- [Parsable.simple_parse()](https://amazon-orders.readthedocs.io/api.html#amazonorders.entities.parsable.Parsable.simple_parse),
  which can handle most basic fields when parsed with CSS selectors.
- Stability improvements.
- Test improvements.

### Changed

- Moved all constant variables (URLs, CSS selectors, etc.) to `constants.py`.
- Migrated entities to use CSS selector constants.
- `constants.SIGN_IN_URL` is now the landing page for login, the old value has been moved
  to `constants.SIGN_IN_REDIRECT_URL`.

## [1.0.6](https://github.com/alexdlaird/amazon-orders/compare/1.0.5...1.0.6) - 2024-01-25

### Added

- Support for when local session data is stale (Amazon prompts us to login again).
- Documentation improvements.

### Fixed

- Regression in the Captcha flow introduced in `1.0.5`.

## [1.0.5](https://github.com/alexdlaird/amazon-orders/compare/1.0.4...1.0.5) - 2024-01-25

### Added

- [Item.image_link](https://amazon-orders.readthedocs.io/api.html#amazonorders.entity.item.Item.image_link).
- [Item.quantity](https://amazon-orders.readthedocs.io/api.html#amazonorders.entity.item.Item.quantity).
- `version` command to CLI.
- Test improvements.

### Changed

- Migrated to using CSS selectors
  in [`AmazonSession`](https://amazon-orders.readthedocs.io/api.html#amazonorders.session.AmazonSession)
- Migrated to using CSS selectors
  in [`AmazonOrders`](https://amazon-orders.readthedocs.io/api.html#amazonorders.orders.AmazonOrders)

## [1.0.4](https://github.com/alexdlaird/amazon-orders/compare/1.0.3...1.0.4) - 2024-01-24

### Added

- A new OTP auth flow from Amazon that can occur after Captcha.
- Parameters `--max-auth-attempts` and `--output-dir` to CLI.
- `DEFAULT_OUTPUT_DIR`, which defaults to `os.getcwd()`, but allows users to change where output files are written.
- [`Troubleshooting`](https://amazon-orders.readthedocs.io/troubleshooting.html) section to the docs.
- Test improvements, including the ability to run dynamic tests using private order data from JSON files.

### Changed

- Improved string representations of entities,
  including [`Order`](https://amazon-orders.readthedocs.io/api.html#amazonorders.entity.order.Order), moved
  string representation of all fields back to `cli.py` out of the `__str__` method.
- Moved `DEFAULT_COOKIE_JAR_PATH` to `conf.py`.

## [1.0.3](https://github.com/alexdlaird/amazon-orders/compare/1.0.2...1.0.3) - 2024-01-18

### Added

- CLI improvements.
- Documentation improvements.

## [1.0.2](https://github.com/alexdlaird/amazon-orders/compare/1.0.1...1.0.2) - 2024-01-18

### Added

- `IODefault` for I/O operations, which can be extended to use something other than `print()` and `input()`.
- Documentation improvements.
- Test improvements.

### Removed

- `Orders.print_output` variable, `cli.py` now handles output.

## [1.0.1](https://github.com/alexdlaird/amazon-orders/compare/1.0.0...1.0.1) - 2024-01-17

### Added

- Auth flow now also checks session cookies in addition to parsing the page for signs of login.
- All fields to string representation
  of [`Order`](https://amazon-orders.readthedocs.io/api.html#amazonorders.entity.order.Order), so they are not
  output on the CLI.
- `logout` command to CLI.
- Documentation improvements.
- Test improvements.

### Fixed

- Improvements to CLI, including error message cleanup on auth exceptions.
- [`Order.order_details_link`](https://amazon-orders.readthedocs.io/api.html#amazonorders.entity.order.Order.order_details_link)
  is now properly populated even on the details page.
- `.gitattributes` to HTML files are now ignore by Linguist.

## [1.0.0](https://github.com/alexdlaird/amazon-orders/releases/tag/1.0.0) - 2024-01-16

- First stable release of `amazon-orders`.
