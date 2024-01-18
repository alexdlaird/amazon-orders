# Changelog
All notable changes to this project will be documented in this file.

This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://github.com/alexdlaird/amazon-orders-python/compare/1.0.3...HEAD)

## [1.0.3](https://github.com/alexdlaird/pyngrok/compare/1.0.2...1.0.3) - 2024-01-18
### Added
- CLI improvements.
- Documentation improvements.

## [1.0.2](https://github.com/alexdlaird/pyngrok/compare/1.0.1...1.0.2) - 2024-01-18
### Added
- `IODefault` for I/O operations, which can be extended to use something other than `print()` and `input()`.
- Documentation improvements.
- Test improvements.

### Removed
`Orders.print_output` variable, `cli.py` now handles output. 

## [1.0.1](https://github.com/alexdlaird/pyngrok/compare/1.0.0...1.0.1) - 2024-01-17
### Added
- Auth flow now also checks session cookies in addition to parsing the page for signs of login.
- All fields to string representation of [`Order`](https://amazon-orders.readthedocs.io/en/1.0.1/api.html#amazonorders.entity.order.Order), so they are not output on the CLI.
- `logout` command to CLI.
- Documentation improvements.
- Test improvements.

### Fixed
- Improvements to CLI, including error message cleanup on auth exceptions.
- [`Order.order_details_link`](https://amazon-orders.readthedocs.io/en/1.0.1/api.html#amazonorders.entity.order.Order.order_details_link) is now properly populated even on the details page.
- `.gitattributes` to HTML files are now ignore by Linguist.

## [1.0.0](https://github.com/alexdlaird/amazon-orders-python/releases/tag/1.0.0) - 2024-01-16
- First stable release of `amazon-orders`.
