""" Setup the package.

    Install this module in development mode to get the tests to work:
    pip install --editable .[dev]
"""

from setuptools import setup, find_packages

setup(
    name = "vasl_templates",
    version = "0.1",
    packages = find_packages(),
    install_requires = [
        # Python 3.6.5
        "flask==1.0.2",
        # NOTE: PyQt5 requirements: https://doc.qt.io/qt-5/linux.html
        #   Linux: mesa-libGL-devel ; @"C Development Tools and Libraries"
        # nb: WebEngine seems to be broken in 5.10.1 :-/
        "PyQT5==5.10.0",
        "pyyaml==3.13",
        "click==6.7",
    ],
    extras_require = {
        "dev": [
            "pytest==3.6.0",
            "tabulate==0.8.2",
            "selenium==3.12.0",
            "lxml==4.2.4",
            "pylint==1.9.2",
            "pytest-pylint==0.9.0",
            "cx-Freeze==5.1.1",
        ],
    },
    include_package_data = True,
    entry_points = {
        "console_scripts": "vasl-templates = vasl_templates.main:main",
    }
)
