# flake8: noqa
import os
import shutil
import subprocess
import tempfile
import warnings
from functools import lru_cache
from glob import glob
from pathlib import Path

import numpy as np
import pandas as pd
from astropy.coordinates import SkyCoord
from astropy.utils.data import CacheMissingWarning, cache_contents
from astropy.utils.data import clear_download_cache as _astropy_clear_download_cache
from astropy.utils.data import download_file, import_file_to_cache, is_url_in_cache
from tqdm import tqdm
from datetime import datetime, timedelta, timezone
from astropy.time import Time
import astropy.units as u

from . import CACHEDIR, KERNELDIR, PACKAGEDIR, TLEDIR, log

META_START = """KPL/MK

pandoraspacecraft meta kernel
==============

The generic kernels listed below can be obtained from NAIF generic kernels:
    https://naif.jpl.nasa.gov/pub/naif/generic_kernels/

\\begindata

"""
META_END = """

\\begintext   
"""


PANDORADIRECTIONS = {
    "boresight": np.asarray([0, 0, 1]),
    "st1": np.asarray([0.6804, -0.7071, -0.1923]),
    "st2": np.asarray([0.6804, 0.7071, -0.1923]),
    "x": np.asarray([1, 0, 0]),
    "y": np.asarray([0, 1, 0]),
    "z": np.asarray([0, 0, 1]),
    "-x": np.asarray([-1, 0, 0]),
    "-y": np.asarray([0, -1, 0]),
    "-z": np.asarray([0, 0, -1]),
}


def clear_cache():
    _astropy_clear_download_cache(pkgname="pandoraspacecraft")
    [os.remove(path) for path in glob(f"{KERNELDIR}/Pandora/*.spk")]


def truncate_directory_string(directory_string):
    """Turns a directory string into a SPICE compliant list of directorys..."""
    lines = []
    line = ""
    words = directory_string.split("/")
    for word in words:
        if word == "":
            continue
        if len(line) < 50:
            line = f"{line}/{word}"
        else:
            line = f"{line}+"
            lines.append(line)
            line = f"/{word}"
    lines.append(line)
    return lines


def create_meta_test_kernel():
    """Create a meta kernel out of the built in SPICE kernels
    This meta kernel is only for testing, but doesn't require internet access to be able to generate.
    """
    paths = [
        *glob(f"{PACKAGEDIR}/data/kernels/testkernels/*"),
        *glob(f"{PACKAGEDIR}/data/kernels/Pandora/*"),
    ]

    if len(paths) == 0:
        raise ValueError(
            "Can not find any SPICE kernels. Check documentation on installation."
        )
    cache_dirs = np.unique([os.path.dirname(os.path.dirname(f)) for f in paths])
    if len(cache_dirs) != 1:
        raise ValueError(
            "You have provided multiple cache directories for SPICE kernels, try reinstalling."
        )

    path_values = truncate_directory_string(cache_dirs[0])
    path_symbols = ["cache"]
    kernels_to_load = ["$cache/" + path[len(cache_dirs[0]) + 1 :] for path in paths]

    def format_list(l, pad=10):
        if len(l) == 0:
            return ""
        if len(l) == 1:
            return f" '{l[0]}'"
        output = f" '{l[0]}'"
        for i in l[1:]:
            output += "\n" + "".join([" "] * pad) + "'" + i + "'"
        return output

    output = f"""{META_START}
    \n    PATH_VALUES = ({format_list(path_values, 20)}              )
    \n    PATH_SYMBOLS = ({format_list(path_symbols, 21)}              )
    \n    KERNELS_TO_LOAD = ({format_list(kernels_to_load, 24)}              )
    {META_END}
    """

    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as temp_file:
        temp_file.write(output)
        # Get the file name
        temp_file_name = temp_file.name

    import_file_to_cache(
        "https://github.com/pandoramission/pandoraspacecraft/src/pandoraspacecraft/data/TestMeta.txt",
        temp_file_name,
        pkgname="pandoraspacecraft",
    )
    return


def create_meta_kernel():
    """Create a meta kernel out of the cached SPICE kernels"""
    KERNELS = {
        # "naif0012.tls": "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/lsk/",
        "de440.bsp": "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/",
        # "pck00011.tpc": "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/",
    }

    paths = get_file_paths(KERNELS)
    cc = cache_contents(pkgname="pandoraspacecraft")
    paths = np.hstack(
        [
            paths,
            np.sort(
                [
                    value
                    for item, value in cc.items()
                    if (value not in paths)
                    and (
                        item.split("/")[-1].startswith("pandora")
                        & (item.endswith(".spk"))
                        | item.endswith(".bc")
                        | item.endswith(".bsp")
                    )
                ]
            ),
        ]
    )
    if len(paths) == 0:
        raise ValueError(
            "Can not find any SPICE kernels. Check documentation on installation."
        )
    cache_dirs = np.unique([os.path.dirname(os.path.dirname(f)) for f in paths])
    if len(cache_dirs) != 1:
        raise ValueError(
            "You have provided multiple cache directories for SPICE kernels, try reinstalling."
        )

    path_values = truncate_directory_string(cache_dirs[0])
    path_symbols = ["cache"]
    kernels_to_load = ["$cache/" + path[len(cache_dirs[0]) + 1 :] for path in paths]
    for dirname in glob(f"{KERNELDIR}/*"):
        if "testkernels" in dirname:
            continue
        for d in truncate_directory_string(dirname):
            path_values.append(d)
        path_symbols.append(dirname.split("/")[-1])
        for d in np.sort(glob(dirname + "/*")):
            kernels_to_load.append("$" + dirname.split("/")[-1] + d[len(dirname) :])

    def format_list(l, pad=10):
        if len(l) == 0:
            return ""
        if len(l) == 1:
            return f" '{l[0]}'"
        output = f" '{l[0]}'"
        for i in l[1:]:
            output += "\n" + "".join([" "] * pad) + "'" + i + "'"
        return output

    output = f"""{META_START}
    \n    PATH_VALUES = ({format_list(path_values, 20)}              )
    \n    PATH_SYMBOLS = ({format_list(path_symbols, 21)}              )
    \n    KERNELS_TO_LOAD = ({format_list(kernels_to_load, 24)}              )
    {META_END}
    """

    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as temp_file:
        temp_file.write(output)
        # Get the file name
        temp_file_name = temp_file.name

    import_file_to_cache(
        "https://github.com/pandoramission/pandoraspacecraft/src/pandoraspacecraft/data/Meta.txt",
        temp_file_name,
        pkgname="pandoraspacecraft",
    )
    return


def get_file_path(url):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", CacheMissingWarning)
        return download_file(
            url, cache=True, show_progress=False, pkgname="pandoraspacecraft"
        )


def get_file_paths(file_dictionary):
    """Ensure the file is downloaded and valid using Astropy's download_file."""
    file_paths = []
    file_names = list(file_dictionary.keys())
    progress_bar = None
    for idx, file_name in enumerate(file_names):
        log.debug(f"Finding {file_name}.")
        url = file_dictionary[file_name]
        if is_url_in_cache(url + file_name, pkgname="pandoraspacecraft"):
            file_paths.append(get_file_path(url + file_name))
            log.debug(f"Found {file_name} in cache.")
            continue
        if progress_bar is None:
            progress_bar = tqdm(
                range(0, len(file_names)),
                initial=idx,
                total=len(file_names),
                desc="Downloading SPICE Kernels",
            )
        file_paths.append(get_file_path(url + file_name))
        progress_bar.n = idx
        progress_bar.refresh()
        log.debug(f"Downloaded {file_name}.")
    return file_paths


def convert_tles_to_spk(run_all=True):
    Path(CACHEDIR).mkdir(parents=True, exist_ok=True)
    tle_paths = np.sort(glob(TLEDIR + "*.tle"))
    for f in tle_paths:
        p = Path(f)
        text = p.read_text()
        text = text.replace("1 99152U", "1 67395U")
        text = text.replace("2 99152", "2 67395")
        p.write_text(text)
    cc = cache_contents(pkgname="pandoraspacecraft")
    for tle_path in tle_paths:
        p = Path(tle_path)
        # read raw bytes
        b = p.read_bytes()

        # convert Windows CRLF -> Unix LF
        b = b.replace(b"\r\n", b"\n")

        # (optional) also handle any stray lone CRs
        b = b.replace(b"\r", b"\n")

        p.write_bytes(b)

        with open(tle_path, "rb") as file:
            sc_id = f"{file.read()}".split("\\n2 ")[1].split(" ")[0]
        tle_name = tle_path.split("/")[-1]

        if not run_all:
            if np.any([tle_name.split(".")[0] in item for item, value in cc.items()]):
                continue

        import_file_to_cache(
            url_key=f"https://github.com/pandoramission/pandoraspacecraft/src/pandoraspacecraft/data/tle/{tle_name}",
            filename=tle_path,
            pkgname="pandoraspacecraft",
        )

        KERNELS = {
            tle_name: f"https://github.com/pandoramission/pandoraspacecraft/src/pandoraspacecraft/data/tle/",
            "naif0012.tls": "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/lsk/",
            "geophysical.ker": "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/",
        }
        file_paths = get_file_paths(KERNELS)
        totle_string = f"""\\begindata
            
            INPUT_DATA_TYPE   = 'TL_ELEMENTS'
            OUTPUT_SPK_TYPE   = 10
            
            INPUT_DATA_FILE   = '{"/".join(file_paths[0].split("/")[-2:])}'
            OUTPUT_SPK_FILE   = 'pandora.bsp'
            
            LEAPSECONDS_FILE  = '{"/".join(file_paths[1].split("/")[-2:])}'
            PCK_FILE          = '{"/".join(file_paths[2].split("/")[-2:])}'
                    
            TLE_START_PAD = '2 days'
            TLE_STOP_PAD  = '{"2 days" if tle_path != tle_paths[-1] else "365 days"}'

            CENTER_ID         = 399
            REF_FRAME_NAME    = 'J2000'
            
            OBJECT_ID         = {sc_id}
            OBJECT_NAME       = 'PANDORA SPACECRAFT'
            
            PRODUCER_ID = 'PandoraDPC'
            
            \\begintext"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".tm", delete=False) as f:
            f.write(totle_string)
            setup_path = f.name

        subprocess.run(
            [
                "mkspk",
                "-setup",
                setup_path,
                "-output",
                f"{tle_name.split('.tle')[0]}.spk",
            ],
            cwd=CACHEDIR,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        Path(setup_path).unlink()

        # shutil.move(
        #     f"{CACHEDIR}/pandora.bsp",
        #     # f"{KERNELDIR}/Pandora/{tle_name.split('.tle')[0]}.spk",
        #     f"{CACHEDIR}/{tle_name.split('.tle')[0]}.spk",
        # )

        import_file_to_cache(
            f"https://github.com/pandoramission/pandoraspacecraft/src/pandoraspacecraft/data/kernels/Pandora/{tle_name.split('.tle')[0]}.spk",
            f"{CACHEDIR}/{tle_name.split('.tle')[0]}.spk",
            remove_original=True,
            pkgname="pandoraspacecraft",
            replace=False,
        )

        _astropy_clear_download_cache(
            f"https://github.com/pandoramission/pandoraspacecraft/src/pandoraspacecraft/data/tle/{tle_name}",
            "pandoraspacecraft",
        )

        if os.path.exists(setup_path):
            os.remove(setup_path)


def vec_to_radec(x, y, z):
    r = np.sqrt(x * x + y * y + z * z)
    ra = np.arctan2(y, x)  # [-pi, pi]
    ra = ra % (2 * np.pi)  # [0, 2pi)
    dec = np.arcsin(z / r)
    return np.degrees(ra), np.degrees(dec)


def vec_to_coord(x, y, z):
    ra, dec = vec_to_radec(x, y, z)
    return SkyCoord(ra, dec, unit="deg")


def radec_to_vec(ra, dec):
    ra, dec = u.Quantity(ra, "degree"), u.Quantity(dec, "degree")
    ca, sa = np.cos(ra.deg.value), np.sin(ra.deg.value)
    cd, sd = np.cos(dec.deg.value), np.sin(dec.deg.value)
    return np.array([cd * ca, cd * sa, sd], dtype=float)


def coord_to_vec(coord):
    return radec_to_vec(coord.ra, coord.dec)


def rotmat_from_xyzw(quats):
    x, y, z, w = quats.T
    return np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
        ]
    )


def get_pointing_vector_from_quats(quats, direction="boresight"):
    R = rotmat_from_xyzw(quats)
    pointing = np.dot(
        R.transpose([2, 0, 1]),
        PANDORADIRECTIONS[direction] if isinstance(direction, str) else direction,
    )
    pointing /= np.linalg.norm(pointing, axis=1)[:, None]
    return pointing


def radec_from_vec(v):
    x, y, z = v
    r = np.linalg.norm(v)
    ra = np.degrees(np.arctan2(y, x)) % 360.0
    dec = np.degrees(np.arcsin(z / r))
    return ra, dec


def quat_xyzw_to_radec(q, boresight=np.array([0.0, 0.0, 1.0])):
    R = rotmat_from_xyzw(q)
    v_inertial = R @ boresight
    return radec_from_vec(v_inertial)


def slerp(q0, q1, t, eps=1e-8):
    """
    SLERP between unit quaternions q0 and q1.
    q0, q1: shape (4,), scalar-last [x,y,z,w]
    t: float in [0,1]
    Returns unit quaternion, scalar-last.
    """

    def normalize(q):
        q = np.asarray(q, dtype=float)
        return q / np.linalg.norm(q)

    q0 = normalize(q0)
    q1 = normalize(q1)

    d = np.dot(q0, q1)

    # Same-rotation ambiguity fix (prevents 180° wrap issues)
    if d < 0.0:
        q1 = -q1
        d = -d

    # If very close, fall back to normalized lerp (avoids numeric issues)
    if d > 1.0 - eps:
        q = q0 + t * (q1 - q0)
        return normalize(q)

    theta = np.arccos(np.clip(d, -1.0, 1.0))
    sin_theta = np.sin(theta)

    w0 = np.sin((1.0 - t) * theta) / sin_theta
    w1 = np.sin(t * theta) / sin_theta
    return w0 * q0 + w1 * q1


def interp_quat(times, quats, t):
    times = np.asarray(times, dtype=float)
    quats = np.asarray(quats, dtype=float)

    i = np.searchsorted(times, t) - 1
    i = np.clip(i, 0, len(times) - 2)

    t0, t1 = times[i], times[i + 1]
    u = (t - t0) / (t1 - t0)
    return slerp(quats[i], quats[i + 1], u)


def angle_between(a, b):
    a = np.asarray(a)
    b = np.asarray(b)
    norm = (
        np.linalg.norm(np.atleast_1d(a), axis=1)[:, None]
        * np.linalg.norm(np.atleast_1d(b), axis=1)[:, None]
    )
    cos_theta = np.asarray(
        [
            np.dot(np.atleast_1d(a1), np.atleast_1d(b1)) / norm1
            for a1, b1, norm1 in zip(a, b, norm)
        ]
    )[:, 0]
    # numerical safety
    cos_theta = np.clip(cos_theta, -1.0, 1.0)
    if a.ndim == 0:
        return np.arccos(cos_theta[0])
    return np.arccos(cos_theta)  # radians


def convert_telemetry_to_cks(fname):
    """Converts input bus quaternions to CK file"""
    Path(CACHEDIR).mkdir(parents=True, exist_ok=True)
    qdf = pd.read_csv(fname)
    outname = fname.split("/")[-1].split(".")[0]

    qt = Time(
        [
            datetime(1970, 1, 1, tzinfo=timezone.utc)
            + timedelta(seconds=t / 1000)
            - timedelta(seconds=37)
            for t in qdf.time.values
        ]
    )
    quats = qdf[["q1", "q2", "q3", "q4"]].values
    k = np.isclose(np.linalg.norm(quats, axis=1), 1, atol=1e-4)
    k = k & np.roll(k, 1) & np.roll(k, -1)
    qt, quats = qt[k], quats[k]
    quats /= np.linalg.norm(quats, axis=1, keepdims=True)

    spice_quats = np.asarray([quats[:, 3], quats[:, 0], quats[:, 1], quats[:, 2]]).T
    pd.DataFrame(np.hstack([qt.isot[:, None], spice_quats])).to_csv(
        f"{CACHEDIR}/input_quats.csv", sep=" ", header=False, index=False
    )
    import_file_to_cache(
        url_key=f"https://github.com/pandoramission/pandoraspacecraft/src/pandoraspacecraft/data/ck/input_quats.csv",
        filename=f"{CACHEDIR}/input_quats.csv",
        remove_original=True,
        pkgname="pandoraspacecraft",
        replace=False,
    )

    import_file_to_cache(
        url_key="https://github.com/pandoramission/pandoraspacecraft/src/pandoraspacecraft/data/kernels/Pandora/pandora_sclkscet.0005.tsc",
        filename=f"{PACKAGEDIR}/data/kernels/Pandora/pandora_sclkscet.0005.tsc",
        pkgname="pandoraspacecraft",
    )

    KERNELS = {
        "input_quats.csv": "https://github.com/pandoramission/pandoraspacecraft/src/pandoraspacecraft/data/ck/",
        "naif0012.tls": "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/lsk/",
        "pandora_sclkscet.0005.tsc": "https://github.com/pandoramission/pandoraspacecraft/src/pandoraspacecraft/data/kernels/Pandora/",
    }
    file_paths = get_file_paths(KERNELS)

    tock_string = f"""\\begindata
    
    INPUT_DATA_TYPE          = 'SPICE QUATERNIONS'
    INPUT_TIME_TYPE          = 'UTC'
    
    CK_TYPE                  = 3
    
    INSTRUMENT_ID            = -167395000
    REFERENCE_FRAME_NAME     = 'J2000'
    ANGULAR_RATE_PRESENT     = 'NO'
    
    CK_SEGMENT_ID            = 'SPACECRAFT ATTITUDE'
    PRODUCER_ID              = 'Christina Hedges'
    
    LSK_FILE_NAME            = '{"/".join(file_paths[1].split("/")[-2:])}'
    SCLK_FILE_NAME           = '{"/".join(file_paths[2].split("/")[-2:])}'
    
    \\begintext"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".tm", delete=False) as f:
        f.write(tock_string)
        setup_path = f.name

    subprocess.run(
        [
            "msopck",
            setup_path,
            f"{'/'.join(file_paths[0].split('/')[-2:])}",
            f"{outname}.bc",
        ],
        cwd=CACHEDIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    Path(setup_path).unlink()
    import_file_to_cache(
        f"https://github.com/pandoramission/pandoraspacecraft/src/pandoraspacecraft/data/kernels/Pandora/{outname}.bc",
        f"{CACHEDIR}/{outname}.bc",
        remove_original=True,
        pkgname="pandoraspacecraft",
        replace=False,
    )

    _astropy_clear_download_cache(
        f"https://github.com/pandoramission/pandoraspacecraft/src/pandoraspacecraft/data/ck/input_quats.csv",
        "pandoraspacecraft",
    )

    if os.path.exists(setup_path):
        os.remove(setup_path)


def convert_telemetry_to_spks(fname):
    """Converts input bus position and velocity to SPK file"""
    Path(CACHEDIR).mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(fname)
    outname = fname.split("/")[-1].split(".")[0]

    qt = Time(
        [
            datetime(1970, 1, 1, tzinfo=timezone.utc)
            + timedelta(seconds=t / 1000)
            - timedelta(seconds=37)
            for t in df.time.values
        ]
    )
    positions = df[["p1", "p2", "p3"]].values
    velocities = df[["v1", "v2", "v3"]].values

    norm = np.linalg.norm(positions, axis=1)
    resid = np.abs(norm - np.median(norm))
    k = resid < 4 * np.median(resid)
    k = k & np.roll(k, 1) & np.roll(k, -1)
    qt, positions, velocities = qt[k], positions[k], velocities[k]

    norm = np.linalg.norm(velocities, axis=1)
    resid = np.abs(norm - np.median(norm))
    k = resid < 4 * np.median(resid)
    k = k & np.roll(k, 1) & np.roll(k, -1)
    qt, positions, velocities = qt[k], positions[k], velocities[k]

    norm = np.gradient(np.linalg.norm(positions, axis=1), qt.jd)
    resid = np.abs(norm - np.median(norm))
    k = resid < 4 * np.median(resid)
    k = k & np.roll(k, 1) & np.roll(k, -1)
    qt, positions, velocities = qt[k], positions[k], velocities[k]

    norm = np.gradient(np.linalg.norm(velocities, axis=1), qt.jd)
    resid = np.abs(norm - np.median(norm))
    k = resid < 4 * np.median(resid)
    k = k & np.roll(k, 1) & np.roll(k, -1)
    qt, positions, velocities = qt[k], positions[k], velocities[k]

    pd.DataFrame(np.hstack([qt.isot[:, None], positions, velocities])).to_csv(
        f"{CACHEDIR}input_telemetry.csv", header=False, index=False
    )
    import_file_to_cache(
        url_key=f"https://github.com/pandoramission/pandoraspacecraft/src/pandoraspacecraft/data/ck/input_telemetry.csv",
        filename=f"{CACHEDIR}input_telemetry.csv",
        remove_original=True,
        pkgname="pandoraspacecraft",
        replace=False,
    )

    KERNELS = {
        "input_telemetry.csv": "https://github.com/pandoramission/pandoraspacecraft/src/pandoraspacecraft/data/ck/",
        "naif0012.tls": "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/lsk/",
    }
    file_paths = get_file_paths(KERNELS)

    tospk_string = f"""\\begindata

INPUT_DATA_TYPE    = 'STATES'
OUTPUT_SPK_TYPE    = 13
POLYNOM_DEGREE = 3

OBJECT_ID          = -167395
CENTER_ID          = 399
REF_FRAME_NAME     = 'J2000'
PRODUCER_ID        = 'Christina Hedges'

DATA_ORDER         = 'EPOCH X Y Z VX VY VZ'
DATA_DELIMITER     = ','
LINES_PER_RECORD   = 1
INPUT_DATA_UNITS   = ( 'DISTANCES=km' )

IGNORE_FIRST_LINE  = 0
LEAPSECONDS_FILE   = '{"/".join(file_paths[1].split("/")[-2:])}'

\\begintext"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".tm", delete=False) as f:
        f.write(tospk_string)
        setup_path = f.name

    subprocess.run(
        [
            "mkspk",
            "-setup",
            setup_path,
            "-input",
            f"{'/'.join(file_paths[0].split('/')[-2:])}",
            "-output",
            f"{outname}.bsp",
        ],
        cwd=CACHEDIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    Path(setup_path).unlink()

    import_file_to_cache(
        f"https://github.com/pandoramission/pandoraspacecraft/src/pandoraspacecraft/data/kernels/Pandora/{outname}.bsp",
        f"{CACHEDIR}{outname}.bsp",
        remove_original=True,
        pkgname="pandoraspacecraft",
        replace=False,
    )

    _astropy_clear_download_cache(
        f"https://github.com/pandoramission/pandoraspacecraft/src/pandoraspacecraft/data/ck/input_telemetry.csv",
        "pandoraspacecraft",
    )

    if os.path.exists(setup_path):
        os.remove(setup_path)
