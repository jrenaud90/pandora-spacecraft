# flake8: noqa
"""Tools to maintain package"""

import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from glob import glob
from pathlib import Path

import numpy as np
import pandas as pd
import spiceypy
from astropy.time import Time
from astropy.utils.data import cache_contents
from astropy.utils.data import clear_download_cache as _astropy_clear_download_cache
from astropy.utils.data import import_file_to_cache

from . import CACHEDIR, PACKAGEDIR, TLEDIR
from .utils import META_END, META_START, get_file_paths, truncate_directory_string


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


def update_cks(quaternions_csv_filename):
    df = pd.read_csv(quaternions_csv_filename)
    qt = Time(
        [
            datetime(1970, 1, 1, tzinfo=timezone.utc)
            + timedelta(seconds=t / 1000)
            - timedelta(seconds=37)
            for t in df.time.values
        ]
    )
    k = qt.jd > 2461052
    df, qt = df[k], qt[k]

    # Split at every 7 days since launch
    ph = qt.jd - ((qt.jd - 2461052) % 7)
    splits = np.where(np.diff(ph) == 7)[0] + 1

    with tempfile.TemporaryDirectory() as d:
        for a, b in zip(np.hstack([splits[:-1]]), splits[1:]):
            df1 = df[a:b]
            chunk_name = f"pandora_ck_{int(np.round(qt.jd[a] - 2461052)):05}"
            path = Path(d) / f"{chunk_name}.csv"
            df1.to_csv(path, index=False)
            convert_telemetry_to_cks(str(path))
            shutil.copy(
                cache_contents("pandoraspacecraft")[
                    f"https://github.com/pandoramission/pandoraspacecraft/src/pandoraspacecraft/data/kernels/Pandora/{chunk_name}.bc"
                ],
                PACKAGEDIR + f"/data/kernels/Pandora/{chunk_name}.bc",
            )


def update_spks(positions_csv_filename):
    df = pd.read_csv(positions_csv_filename)
    qt = Time(
        [
            datetime(1970, 1, 1, tzinfo=timezone.utc)
            + timedelta(seconds=t / 1000)
            - timedelta(seconds=37)
            for t in df.time.values
        ]
    )
    k = qt.jd > 2461052
    df, qt = df[k], qt[k]

    # Split at every 7 days since launch
    ph = qt.jd - ((qt.jd - 2461052) % 7)
    splits = np.where(np.diff(ph) == 7)[0] + 1

    with tempfile.TemporaryDirectory() as d:
        for a, b in zip(np.hstack([splits[:-1]]), splits[1:]):
            df1 = df[a:b]
            chunk_name = f"pandora_spk_{int(np.round(qt.jd[a] - 2461052)):05}"
            path = Path(d) / f"{chunk_name}.csv"
            df1.to_csv(path, index=False)
            convert_telemetry_to_spks(str(path))
            shutil.copy(
                cache_contents("pandoraspacecraft")[
                    f"https://github.com/pandoramission/pandoraspacecraft/src/pandoraspacecraft/data/kernels/Pandora/{chunk_name}.bsp"
                ],
                PACKAGEDIR + f"/data/kernels/Pandora/{chunk_name}.bsp",
            )


def make_test_data():
    """This makes the test data for the package.
    Note to run this you must have downloaded all the kernels.
    """

    meta_kernel = cache_contents(pkgname="pandoraspacecraft")[
        "https://github.com/pandoramission/pandoraspacecraft/src/pandoraspacecraft/data/Meta.txt"
    ]
    spiceypy.kclear()
    spiceypy.furnsh(meta_kernel)

    # Define time range for TESS Sector 4
    et_start = spiceypy.str2et("2026-2-20 20:09:56.999998")
    et_end = spiceypy.str2et("2026-02-25 11:33:59.999999")
    ets = np.linspace(et_start, et_end, 1000)

    bodies = [10, 399, 301, -167395]  # Sun, Earth, Moon, Pandora
    segid_template = "{} w.r.t. SSB"

    # Create output .bsp file
    out_kernel = f"{PACKAGEDIR}/data/kernels/testkernels/earth_sun_moon_pandora.bsp"
    if os.path.exists(out_kernel):
        os.remove(out_kernel)

    handle = spiceypy.spkopn(out_kernel, "Truncated ephemeris", 1000)

    # Write each segment
    for body in bodies:
        states = []
        for et in ets:
            state, _ = spiceypy.spkgeo(body, et, "J2000", 0)
            states.append(state)
        states = np.array(states)

        # Write segment using spkw08
        spiceypy.spkw08(
            handle=handle,
            body=body,
            center=0,
            inframe="J2000",
            first=ets[0],
            last=ets[-1],
            segid=segid_template.format(spiceypy.bodc2n(body)),
            step=(ets[-1] - ets[0]) / (len(ets) - 1),  # Interval between states
            n=len(ets),
            states=states,
            epoch1=ets[0],
            degree=2,
        )
    create_meta_test_kernel()


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


def create_meta_test_kernel():
    """Create a meta kernel out of the built in SPICE kernels
    This meta kernel is only for testing, but doesn't require internet access to be able to generate.
    """
    paths = [
        *glob(f"{PACKAGEDIR}/data/kernels/Pandora/*"),
    ]

    paths = [
        p
        for p in paths
        if (not p.endswith("bc"))
        & (not p.endswith("bsp"))
        & (not p.endswith("spk"))
        & (not p.endswith("ck"))
    ]
    paths = [*glob(f"{PACKAGEDIR}/data/kernels/testkernels/*"), *paths]

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
