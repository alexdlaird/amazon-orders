Contributing
============

If you find issues, `report them on GitHub <https://github.com/alexdlaird/amazon-orders/issues>`_.

If you would like to contribute to the code, the process is pretty simple:

1. Familiarise yourself with this package and its dependencies.
2. Fork `the repository on GitHub <https://github.com/alexdlaird/amazon-orders>`_ and start implementing changes.
3. Write a test that plainly validates the changes made.
4. Build and test locally with ``make local``, ``make test``, and ``make test-integration``.
5. Ensure no linting errors were introduced by running ``make check``.
6. Submit a `pull requests <https://help.github.com/en/articles/creating-a-pull-request-from-a-fork>`_ to get the changes merged.

Support for languages other than English comes from separately published language packages, not from
this repository. The core package implements English, along with international date and currency
formats, and a language package can override any part of it through the config. Language packages are
built, published, and maintained by their own authors, including running a nightly integration test
against that version of Amazon. Pull requests that add a language here won't be accepted, but once your
package is published and its nightly run is passing, `request a link
<https://github.com/alexdlaird/amazon-orders/issues/new?template=new-language.yml>`_ and we'll add it to
the docs.

Also be sure to review the `Code of Conduct <https://github.com/alexdlaird/amazon-orders?tab=coc-ov-file#contributor-covenant-code-of-conduct>`_ before
submitting issues or pull requests.

Want to contribute financially? If you've found ``amazon-orders`` useful, `sponsorship <https://github.com/sponsors/alexdlaird>`_
would also be greatly appreciated!