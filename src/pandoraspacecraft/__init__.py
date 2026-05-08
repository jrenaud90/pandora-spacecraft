# Standard library
import os  # noqa

from astropy.config import get_cache_dir

PACKAGEDIR = os.path.abspath(os.path.dirname(__file__))
CACHEDIR = get_cache_dir("pandoraspacecraft") + "/download/url/"
TEST_MODE = False


def enable_test_mode():
    global TEST_MODE
    TEST_MODE = True


def disable_test_mode():
    global TEST_MODE
    TEST_MODE = False


def is_test_mode():
    return TEST_MODE


from importlib.metadata import PackageNotFoundError, version  # noqa


def get_version():
    try:
        return version("pandoraspacecraft")
    except PackageNotFoundError:
        return "unknown"


__version__ = get_version()

import logging  # noqa: E402
import os  # noqa
from glob import glob  # noqa

log = logging.getLogger("pandoraspacecraft")

PACKAGEDIR = os.path.abspath(os.path.dirname(__file__))
KERNELDIR = f"{PACKAGEDIR}/data/kernels/"
TLEDIR = f"{PACKAGEDIR}/data/tle/"
TLEDIR = f"{PACKAGEDIR}/data/tle/"

from .spacecraft import PandoraSpacecraft  # noqa
