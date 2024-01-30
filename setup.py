from setuptools import setup

__author__ = "Alex Laird"
__copyright__ = "Copyright 2024, Alex Laird"
__version__ = "1.0.8"

with open("README.md", "r") as f:
    long_description = f.read()

setup(
    name="amazon-orders",
    version=__version__,
    packages=["amazonorders",
              "amazonorders.entity"],
    python_requires=">=3.8",
    install_requires=[
        "click",
        "requests",
        "amazoncaptcha",
        "beautifulsoup4"
    ],
    entry_points="""
        [console_scripts]
        amazon-orders=amazonorders.cli:amazon_orders_cli
    """,
    include_package_data=True,
    description="A CLI and library for interacting with Amazon order history.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Alex Laird",
    author_email="contact@alexlaird.com",
    url="https://github.com/alexdlaird/amazon-orders-python",
    download_url="https://github.com/alexdlaird/amazon-orders-python/archive/{}.tar.gz".format(__version__),
    project_urls={
        "Changelog": "https://github.com/alexdlaird/amazon-orders-python/blob/main/CHANGELOG.md",
        "Sponsor": "https://github.com/sponsors/alexdlaird"
    },
    keywords=["python", "amazon", "library", "cli"],
    license="MIT",
    classifiers=[
        "Environment :: Console",
        "Environment :: Web Environment",
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: MacOS",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Unix",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ]
)
