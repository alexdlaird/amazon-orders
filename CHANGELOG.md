# Changelog

All notable changes to this project will be documented in this file.

This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://github.com/alexdlaird/amazon-orders/compare/1.1.1...HEAD)

## [1.1.2](https://github.com/alexdlaird/amazon-orders/compare/1.1.1...1.1.2) - TBD

### Added
- Build improvements.
- Documentation improvements.
- Test improvements (Amazon no longer provides the `condition` field in many cases).

### Fixed

- Raise `AmazonOrdersNotFoundError` when Order is not found.
- Prices with thousands separator now parse properly.

### Changed

- [AmazonOrder.debug](https://amazon-orders.readthedocs.io/en/1.1.2/api.html#amazonorders.orders.AmazonOrders.debug)
  defaults to the value
  of [AmazonSession.debug](https://amazon-orders.readthedocs.io/en/1.1.2/api.html#amazonorders.session.AmazonSession.debug)
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

- [AuthForm](https://amazon-orders.readthedocs.io/en/1.0.9/api.html#amazonorders.forms.AuthForm)'s now
  passes `captcha_img_url` to its `prompt()` fallback for Captcha, useful for
  overriding [IODefault](https://amazon-orders.readthedocs.io/en/1.0.9/api.html#amazonorders.session.IODefault).
- [MfaDeviceSelectForm](https://amazon-orders.readthedocs.io/en/1.0.9/api.html#amazonorders.forms.MfaDeviceSelectForm)
  now passes `mfa_device_select_choices` to `prompt()`, useful for
  overrides [IODefault](https://amazon-orders.readthedocs.io/en/1.0.9/api.html#amazonorders.session.IODefault).
- Documentation improvements.

## [1.0.8](https://github.com/alexdlaird/amazon-orders/compare/1.0.7...1.0.8) - 2024-01-30

### Added

- Stability improvements.

## [1.0.7](https://github.com/alexdlaird/amazon-orders/compare/1.0.6...1.0.7) - 2024-01-29

### Added

- [AuthForm](https://amazon-orders.readthedocs.io/en/1.0.7/api.html#amazonorders.forms.AuthForm) abstract class, and
  migrated all auth flow items to subclasses of this class.
- [Parsable.simple_parse()](https://amazon-orders.readthedocs.io/en/1.0.7/api.html#amazonorders.entities.parsable.Parsable.simple_parse),
  which can handle most basic fields when parised with CSS selectors.
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

- [Item.image_link](https://amazon-orders.readthedocs.io/en/1.0.5/api.html#amazonorders.entity.item.Item.image_link).
- [Item.quantity](https://amazon-orders.readthedocs.io/en/1.0.5/api.html#amazonorders.entity.item.Item.quantity).
- `version` command to CLI.
- Test improvements.

### Changed

- Migrated to using CSS selectors
  in [`AmazonSession`](https://amazon-orders.readthedocs.io/en/1.0.5/api.html#amazonorders.session.AmazonSession)
- Migrated to using CSS selectors
  in [`AmazonOrders`](https://amazon-orders.readthedocs.io/en/1.0.5/api.html#amazonorders.orders.AmazonOrders)

## [1.0.4](https://github.com/alexdlaird/amazon-orders/compare/1.0.3...1.0.4) - 2024-01-24

### Added

- A new OTP auth flow from Amazon that can occur after Captcha.
- Parameters `--max-auth-attempts` and `--output-dir` to CLI.
- `DEFAULT_OUTPUT_DIR`, which defaults to `os.getcwd()`, but allows users to change where output files are written.
- [`Troubleshooting`](https://amazon-orders.readthedocs.io/en/1.0.4/troubleshooting.html) section to the docs.
- Test improvements, including the ability to run dynamic tests using private order data from JSON files.

### Changed

- Improved string representations of entities,
  including [`Order`](https://amazon-orders.readthedocs.io/en/1.0.4/api.html#amazonorders.entity.order.Order), moved
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
  of [`Order`](https://amazon-orders.readthedocs.io/en/1.0.1/api.html#amazonorders.entity.order.Order), so they are not
  output on the CLI.
- `logout` command to CLI.
- Documentation improvements.
- Test improvements.

### Fixed

- Improvements to CLI, including error message cleanup on auth exceptions.
- [`Order.order_details_link`](https://amazon-orders.readthedocs.io/en/1.0.1/api.html#amazonorders.entity.order.Order.order_details_link)
  is now properly populated even on the details page.
- `.gitattributes` to HTML files are now ignore by Linguist.

## [1.0.0](https://github.com/alexdlaird/amazon-orders/releases/tag/1.0.0) - 2024-01-16

- First stable release of `amazon-orders`.
