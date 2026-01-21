# Amazon Australia (amazon.com.au) Support

This document explains how to configure `amazon-orders` to work with Amazon Australia and other international Amazon sites.

## Quick Start for Amazon Australia

### Method 1: Direct Base URL Parameter (Recommended)

The simplest and most flexible way to use `amazon-orders` with Amazon Australia:

```python
from amazonorders.session import AmazonSession
from amazonorders.orders import AmazonOrders

# Create session with direct base_url parameter
amazon_session = AmazonSession(
    username="your_email@example.com",
    password="your_password",
    debug=True,  # Enable for troubleshooting
    base_url="https://www.amazon.com.au"  # Direct parameter - no environment variables needed
)

amazon_session.login()
amazon_orders = AmazonOrders(amazon_session)
orders = amazon_orders.get_order_history(year=2024)
print(f"Found {len(orders)} orders")
```

### Method 2: Environment Variables (Alternative)

You can also use environment variables if you prefer:

```python
import os
from amazonorders.session import AmazonSession
from amazonorders.orders import AmazonOrders

# Set environment variable before creating session
os.environ["AMAZON_BASE_URL"] = "https://www.amazon.com.au"

amazon_session = AmazonSession(
    username="your_email@example.com",
    password="your_password",
    debug=True
)

amazon_session.login()
amazon_orders = AmazonOrders(amazon_session)
orders = amazon_orders.get_order_history(year=2024)
```

## Supported International Sites

The library automatically detects and configures appropriate settings for:

| Amazon Site | Base URL | Currency | Language |
|-------------|----------|----------|----------|
| Australia | `https://www.amazon.com.au` | A$ | en-AU |
| United Kingdom | `https://www.amazon.co.uk` | £ | en-GB |
| Canada | `https://www.amazon.ca` | C$ | en-CA |
| United States | `https://www.amazon.com` | $ | en-US |

## Configuration Options

### Base URL Parameter

Pass the `base_url` parameter directly to the `AmazonSession` constructor:

```python
amazon_session = AmazonSession(
    username="your_email",
    password="your_password",
    base_url="https://www.amazon.com.au"  # Any Amazon site URL
)
```

### Environment Variables (Alternative)

You can also use environment variables:

- `AMAZON_BASE_URL`: The Amazon site URL (e.g., `https://www.amazon.com.au`)
- `AMAZON_CURRENCY_SYMBOL`: Override currency symbol (e.g., `AUD` instead of `A$`)

### What's Automatically Configured

When you specify a base URL (via parameter or environment variable), the library automatically adjusts:

1. **Headers**: Appropriate `Accept-Language` and other region-specific headers
2. **Currency**: Correct currency symbol for price formatting
3. **URLs**: All internal URLs (sign-in, orders, etc.) use the correct base
4. **Authentication**: Region-specific authentication parameters

## Troubleshooting Amazon Australia

### Enable Debug Mode

Always enable debug mode when troubleshooting authentication issues:

```python
amazon_session = AmazonSession(
    username="your_email",
    password="your_password",
    debug=True,  # This saves HTML pages to help diagnose issues
    config=config
)
```

Debug mode saves HTML pages to the `output/` directory, allowing you to see:

- Captcha challenges
- MFA (Multi-Factor Authentication) prompts
- Error messages from Amazon

### Common Issues and Solutions

#### 1. Authentication Failures

**Problem**: Login fails with Amazon Australia
**Solutions**:

- Ensure you're using credentials for an Australian Amazon account
- Check for captcha challenges in debug HTML files
- Verify MFA is not required (or handle MFA prompts)
- Try logging in manually through a browser first

#### 2. Different Page Structure

**Problem**: Parsing fails due to different HTML structure
**Solutions**:

- Australian Amazon might have different CSS selectors
- Check the saved HTML files in debug mode
- You may need to customize the selectors (see Advanced Configuration)

#### 3. Rate Limiting

**Problem**: Too many requests error
**Solutions**:

- Australian Amazon might have stricter rate limits
- Add delays between requests
- Use fewer concurrent connections

### Advanced Configuration

#### Custom Headers

If you need to customize headers further:

```python
from amazonorders.constants_au import AustralianConstants

class MyAustralianConstants(AustralianConstants):
    @property
    def base_headers(self):
        headers = super().base_headers
        headers.update({
            "X-Custom-Header": "my-value"
        })
        return headers

config = AmazonOrdersConfig(data={
    "constants_class": "my_module.MyAustralianConstants"
})
```

#### Custom Currency Formatting

```python
class MyAustralianConstants(AustralianConstants):
    @property
    def currency_symbol(self):
        return "AUD "  # Space after currency code
    
    def format_currency(self, amount):
        # Custom formatting: AUD 123.45
        formatted_amt = f"{self.currency_symbol}{abs(amount):,.2f}"
        return f"-{formatted_amt}" if amount < 0 else formatted_amt
```

## Testing Your Configuration

Use the provided test script to verify your configuration:

```bash
python test_au_config.py
```

This will test:
- Environment variable detection
- Australian constants class
- Backward compatibility
- Multiple international sites
- Currency and language detection

## Example: Complete Australian Setup

```python
#!/usr/bin/env python3
import logging
from amazonorders.session import AmazonSession
from amazonorders.orders import AmazonOrders

# Enable logging to see what's happening
logging.basicConfig(level=logging.INFO)

def main():
    # Create session with Australian base URL
    amazon_session = AmazonSession(
        username=input("Enter your Amazon Australia email: "),
        password=input("Enter your password: "),
        debug=True,
        base_url="https://www.amazon.com.au"  # Direct parameter - no environment variables needed
    )
    
    # Verify configuration
    print(f"Base URL: {amazon_session.config.constants.BASE_URL}")
    print(f"Currency: {amazon_session.config.constants.CURRENCY_SYMBOL}")
    print(f"Language: {amazon_session.config.constants.BASE_HEADERS['Accept-Language']}")
    
    try:
        # Login
        print("Logging in...")
        amazon_session.login()
        
        # Get orders
        print("Fetching orders...")
        amazon_orders = AmazonOrders(amazon_session)
        orders = amazon_orders.get_order_history(year=2024)
        
        print(f"Found {len(orders)} orders")
        for order in orders[:5]:  # Show first 5
            print(f"Order {order.order_number}: {order.total}")
            
    except Exception as e:
        print(f"Error: {e}")
        print("Check the 'output' directory for HTML files to debug the issue")

if __name__ == "__main__":
    main()
```

### Multi-Region Example

You can easily switch between different Amazon sites:

```python
from amazonorders.session import AmazonSession
from amazonorders.orders import AmazonOrders

# Function to get orders from any Amazon site
def get_orders_from_site(base_url, username, password, year=2024):
    session = AmazonSession(
        username=username,
        password=password,
        base_url=base_url,
        debug=True
    )
    
    print(f"Connecting to {base_url}...")
    print(f"Currency: {session.config.constants.CURRENCY_SYMBOL}")
    
    session.login()
    orders = AmazonOrders(session).get_order_history(year=year)
    return orders

# Example usage
sites = [
    "https://www.amazon.com.au",  # Australia
    "https://www.amazon.co.uk",   # UK
    "https://www.amazon.com",     # US
]

for site in sites:
    try:
        orders = get_orders_from_site(site, "your_email", "your_password")
        print(f"{site}: Found {len(orders)} orders")
    except Exception as e:
        print(f"{site}: Error - {e}")
```

## Migration from Previous Versions

If you were previously using custom code for Amazon Australia:

### From Environment Variables to Parameters (Recommended)

**Old approach:**

```python
import os
os.environ["AMAZON_BASE_URL"] = "https://www.amazon.com.au"
amazon_session = AmazonSession(username="...", password="...")
```

**New approach:**

```python
amazon_session = AmazonSession(
    username="...", 
    password="...", 
    base_url="https://www.amazon.com.au"
)
```

### From Custom Code

If you were previously using custom constants or URL modifications:

1. Remove any custom URL or header modifications
2. Use the `base_url` parameter instead: `base_url="https://www.amazon.com.au"`
3. Test with debug mode enabled
4. Update any hardcoded currency symbols

### Backward Compatibility

Both approaches work identically:

- **Parameter approach**: `base_url="https://www.amazon.com.au"` (recommended)
- **Environment variable approach**: `AMAZON_BASE_URL=https://www.amazon.com.au` (still supported)

The new automatic detection should handle most use cases without additional configuration.