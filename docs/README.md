<a href="https://github.com/pandoramission/pandora-spacecraft/actions/workflows/tests.yml"><img src="https://github.com/pandoramission/pandora-spacecraft/workflows/tests/badge.svg" alt="Test status"/></a><a href="https://github.com/pandoramission/pandora-spacecraft/actions/workflows/black.yml"><img src="https://github.com/pandoramission/pandora-spacecraft/workflows/black/badge.svg" alt="black status"/></a> <a href="https://github.com/pandoramission/pandora-spacecraft/actions/workflows/flake8.yml"><img src="https://github.com/pandoramission/pandora-spacecraft/workflows/flake8/badge.svg" alt="flake8 status"/></a> [![Generic badge](https://img.shields.io/badge/documentation-live-blue.svg)](https://pandoramission.github.io/pandora-spacecraft/)
[![PyPI - Version](https://img.shields.io/pypi/v/pandoraspacecraft)](https://pypi.org/project/pandoraspacecraft/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/pandoraspacecraft)](https://pypi.org/project/pandoraspacecraft/)

# Pandora Spacecraft

This package helps you quickly estimate Pandora's position and velocity at a particular time. Check the example usage to see how to use this package to calculate Pandora's orbital properties.

### Installation

To install you can use

```shell
pip install pandoraspacecraft --upgrade
```

You should update your package often, as we frequently we will add new TLEs. Check your version number using

```python
import pandoraspacecraft as ps
ps.__version__
```

This package will download and store SPICE kernels into a directory in your home area when you use any of the objects. This means that if you install this package in multiple environments, the SPICE kernels will not be redownloaded and will be shared between multiple installs.

If you run into any problems with your installation, try clearing the cache and then restarting your session

```python
from pandoraspacecraft.utils import clear_cache
clear_cache()
```

To uninstall this package from your machine entirely you should uninstall it

```shell
pip uninstall pandoraspacecraft
```

And clear the cache of SPICE kernel files using

```python
from astropy.utils.data import clear_download_cache
clear_download_cache(pkgname='pandoraspacecraft')
```

or by deleting the `.pandoraspacecraft/cache/` directory in your home area.

### Test mode

This package now installs with a lightweight set of truncated kernels which can be used to test the functionality, but cover a very limited time range and set of bodies. These files are available in `src/data/kernels/testkernels`.

If you need to use this package as a depency and want to run tests, use

```python
import pandoraspacecraft as psc
psc.enable_test_mode()
```

This will set up a minimum number of kernels that are shipped with the package, and will not download anything from the internet. This ensures you can use, for example, GitHub actions without downloading anything.

The test kernel is only valid between the following dates:

- 2026-02-20 20:09:56.999998
- 2026-02-25 11:33:59.999999
