# Polish language package for amazon-orders

An unofficial language package that lets `amazon-orders` read Polish order pages on `amazon.pl`. It supports Polish dates, PLN formatting, cancellation, and order and refund totals. It does not translate the CLI or infer missing item quantities.

Install from this source directory with `python -m pip install .`, then add to your `amazon-orders` configuration:

```yaml
domain: amazon.pl
language_package: amazon_orders_pl_language
```

Use `--full-details` on the `orders` command to read detail-only fields such as refund totals. For a local check, run `python -m unittest discover -s tests` after installation. The included tests are synthetic and don't require an Amazon account.
