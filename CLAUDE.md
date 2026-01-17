# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`amazon-orders` is a Python library (and CLI) that provides an unofficial API for Amazon order history. It works by parsing HTML from Amazon's consumer-facing website using BeautifulSoup, with session management handled via requests.

## Development Commands

```bash
# Run unit tests with coverage
make test

# Run integration tests (requires Amazon credentials)
make test-integration

# Run linting and type checking
make check

# Build and install locally
make local

# Build documentation
make docs

# Run a single unit test
source venv/bin/activate
pytest -v tests/unit/test_orders.py::TestOrders::test_method_name

# Run tests without make (after activating venv)
coverage run -m pytest -v --ignore=tests/integration
```

## Architecture

### Core Components

- **`AmazonSession`** (`session.py`): Manages HTTP session, authentication, and cookie persistence. Handles the multi-step Amazon login flow including MFA and CAPTCHA.

- **`AmazonOrders`** (`orders.py`): Queries order history and individual order details. Supports concurrent fetching via thread pool.

- **`AmazonTransactions`** (`transactions.py`): Queries transaction history.

- **`AmazonOrdersConfig`** (`conf.py`): Central configuration with YAML persistence. Allows overriding entity classes, selectors, and constants.

### Entity Layer (`entity/`)

- **`Parsable`** (`parsable.py`): Base class for all entities. Provides `safe_parse()` and `safe_simple_parse()` methods for extracting data from BeautifulSoup Tags with error handling.

- **`Order`**, **`Item`**, **`Shipment`**, **`Recipient`**, **`Seller`**, **`Transaction`**: Data classes that parse themselves from HTML Tags.

### Authentication (`forms.py`)

Authentication uses a chain of `AuthForm` subclasses that handle different Amazon login screens:
- `SignInForm`, `ClaimForm`: Initial login
- `MfaForm`, `MfaDeviceSelectForm`: Two-factor authentication
- `CaptchaForm`: CAPTCHA solving (auto-attempts via `amazoncaptcha` library)
- `IntentForm`: Additional verification prompts

### HTML Parsing (`selectors.py`)

CSS selectors are centralized in the `Selectors` class. This design allows customization for different Amazon locales or HTML changes by subclassing and configuring via `selectors_class`.

### CLI (`cli.py`)

Built with Click. The `IOClick` class adapts session I/O for terminal interaction.

## Testing

- **Unit tests** (`tests/unit/`): Use `responses` library to mock HTTP requests. Test resources (HTML fixtures) are in `tests/resources/`.

- **Integration tests** (`tests/integration/`): Run against live Amazon. Require `AMAZON_USERNAME`, `AMAZON_PASSWORD`, and optionally `AMAZON_OTP_SECRET_KEY` environment variables.

- **Test base classes**: `UnitTestCase` and `IntegrationTestCase` in the tests directory provide setup for mocking and authentication.

## Key Patterns

- Entity fields use `safe_parse()` wrapper to gracefully handle missing/changed HTML structure
- Configuration classes (`Constants`, `Selectors`, entity classes) are loaded dynamically via string paths, enabling extension without modifying core code
- Session cookies are persisted to JSON for reuse across runs
