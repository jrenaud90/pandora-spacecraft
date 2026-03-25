<a href="https://github.com/pandoramission/pandora-spacecraft/actions/workflows/pytest.yml"><img src="https://github.com/pandoramission/pandora-spacecraft/workflows/pytest/badge.svg" alt="Test status"/></a><a href="https://github.com/pandoramission/pandora-spacecraft/actions/workflows/black.yml"><img src="https://github.com/pandoramission/pandora-spacecraft/workflows/black/badge.svg" alt="black status"/></a> <a href="https://github.com/pandoramission/pandora-spacecraft/actions/workflows/flake8.yml"><img src="https://github.com/pandoramission/pandora-spacecraft/workflows/flake8/badge.svg" alt="flake8 status"/></a> [![Generic badge](https://img.shields.io/badge/documentation-live-blue.svg)](https://pandoramission.github.io/pandora-spacecraft/)
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

## Maintainers

If you have to maintain this package you can use the `maintainence` module to update the CK and SPK files using telemetry, and update the test kernel if needed. You will need the quaternions from telemetry in their raw, unformated form as a CSV file, which look like this:

|    |        time |        q1 |         q2 |        q3 |       q4 |
|---:|------------:|----------:|-----------:|----------:|---------:|
|  0 | 1.76651e+12 |  0.435525 | -1.0177    | -0.95454  | 0.865711 |
|  1 | 1.7668e+12  | -1.02916  |  0.940569  |  0.157958 | 0.674988 |
|  2 | 1.76815e+12 | -0.203154 |  0.0986252 | -0.298318 | 0.927197 |
|  3 | 1.76815e+12 | -0.313266 |  0.126517  | -0.32174  | 0.883077 |
|  4 | 1.76815e+12 | -0.463277 |  0.159831  | -0.345662 | 0.798644 |

and the positions and velocities over time which look like this:

|    |        time |      p1 |      p2 |       p3 |      v1 |        v2 |      v3 |
|---:|------------:|--------:|--------:|---------:|--------:|----------:|--------:|
|  0 | 1.76815e+12 | 6544.48 | 1698.28 | -1759.2  | 2.08593 | -0.556566 | 7.23922 |
|  1 | 1.76815e+12 | 6556.82 | 1694.9  | -1715.72 | 2.03993 | -0.568475 | 7.25141 |
|  2 | 1.76815e+12 | 6576.84 | 1689.11 | -1643.1  | 1.9631  | -0.588273 | 7.27112 |
|  3 | 1.76815e+12 | 6596.09 | 1683.13 | -1570.3  | 1.88616 | -0.608106 | 7.2901  |
|  4 | 1.76815e+12 | 6614.57 | 1676.95 | -1497.31 | 1.80899 | -0.627867 | 7.30822 |

From a terminal or a notebook run the following to update CK and SPK. First build a CK and SPK from your full set of telemetry

```python
from pandoraspacecraft.maintenance import convert_telemetry_to_cks, convert_telemetry_to_spks
convert_telemetry_to_cks(quaternions_csv_filename)
convert_telemetry_to_spks(position_csv_filename)
```

You can then restart your session and run the following to update the test data, if necessary. You would only do this if you changed the code base significantly or if you wanted to change the period of validity for the test data.

```python
from pandoraspacecraft.maintenance import make_test_data
make_test_data()
```

When you have finished your updates you should make sure to push them to the `pandoraspacecraft` repo. Inside the `utils.py` module update `nweeks = X` to the number of weeks of CK and SPK files you have now made.

These files are not included with the distribution of the package to pip and are instead downloaded and cached whenever you run the package. This ensures that the files are shared between multiple installs across different environments.

### TLEs

TLEs are not used by this package but are maintained and pushed to GitHub.
