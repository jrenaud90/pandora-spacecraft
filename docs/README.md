<a href="https://github.com/pandoramission/pandora-spacecraft/actions/workflows/tests.yml"><img src="https://github.com/pandoramission/pandora-spacecraft/workflows/tests/badge.svg" alt="Test status"/></a><a href="https://github.com/pandoramission/pandora-spacecraft/actions/workflows/black.yml"><img src="https://github.com/pandoramission/pandora-spacecraft/workflows/black/badge.svg" alt="black status"/></a> <a href="https://github.com/pandoramission/pandora-spacecraft/actions/workflows/flake8.yml"><img src="https://github.com/pandoramission/pandora-spacecraft/workflows/flake8/badge.svg" alt="flake8 status"/></a> [![Generic badge](https://img.shields.io/badge/documentation-live-blue.svg)](https://pandoramission.github.io/pandora-spacecraft/)
[![PyPI - Version](https://img.shields.io/pypi/v/pandoraspacecraft)](https://pypi.org/project/pandoraspacecraft/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/pandoraspacecraft)](https://pypi.org/project/pandoraspacecraft/)

# Pandora Spacecraft

This package helps you quickly estimate Pandora's position and velocity at a particular time. Check the example usage to see how to use this package to calculate Pandora's orbital properties.

### Installation

To install you can use

```
pip install pandoraspacecraft --upgrade
```

You should update your package often, as we frequently we will add new TLEs. Check your version number using

```
import pandoraspacecraft as ps
ps.__version__
```
