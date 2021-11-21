""" Setup the package.

    Install this module in development mode to get the tests to work:
      pip install --editable .[dev]
"""

import os
from setuptools import setup, find_packages

# ---------------------------------------------------------------------

# NOTE: We break the requirements out into separate files so that we can load them early
# into a Docker image, where they can be cached, instead of having to re-install them every time.

def parse_requirements( fname ):
    """Parse a requirements file."""
    lines = []
    fname = os.path.join( os.path.split(__file__)[0], fname )
    with open( fname, "r", encoding="utf-8" ) as fp:
        for line in fp:
            line = line.strip()
            if line == "" or line.startswith("#"):
                continue
            lines.append( line )
    return lines

# ---------------------------------------------------------------------

setup(
    name = "vasl_templates",
    version = "1.9", # nb: also update constants.py
    description = "Create HTML snippets for use in VASL.",
    license = "AGPLv3",
    url = "https://github.com/pacman-ghost/vasl-templates",
    packages = find_packages(),
    install_requires = parse_requirements( "requirements.txt" ),
    extras_require = {
        "gui": [
            # NOTE: PyQt5 requirements: https://doc.qt.io/qt-5/linux.html
            #   Linux: mesa-libGL-devel ; @"C Development Tools and Libraries"
            # NOTE: You may need to disable VMware 3D acceleration, if QWebEngineView is crashing.
            "PyQT5==5.15.4",
            "PyQtWebEngine==5.15.4",
        ],
        "dev": parse_requirements( "requirements-dev.txt" ),
    },
    include_package_data = True,
    data_files = [
        ( "vasl-templates", ["LICENSE.txt"] ),
    ],
    entry_points = {
        "console_scripts": "vasl-templates = vasl_templates.main:main",
    }
)
