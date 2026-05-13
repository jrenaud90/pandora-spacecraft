# flake8: noqa
"""Tools to maintain package"""

import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from glob import glob
from pathlib import Path

import astropy.units as u
import numpy as np
import pandas as pd
import spiceypy
from astropy.time import Time
from astropy.utils.data import cache_contents
from astropy.utils.data import clear_download_cache as _astropy_clear_download_cache
from astropy.utils.data import import_file_to_cache
from tqdm import tqdm

from . import CACHEDIR, KERNELDIR, PACKAGEDIR, TLEDIR
from .utils import (
    META_END,
    META_START,
    find_merged_gaps,
    get_file_paths,
    truncate_directory_string,
)


def _cache_rel(path, parts=2):
    """Return a cache-relative path token using POSIX separators."""
    return "/".join(Path(path).parts[-parts:])


def _naif_tool(name):
    """Resolve NAIF utility executable on any OS and fail with a clear error."""
    tool = shutil.which(name) or shutil.which(f"{name}.exe")
    if tool is None:
        raise FileNotFoundError(
            f"Could not find NAIF utility '{name}' on PATH. Install NAIF Toolkit utilities and ensure they are on PATH."
        )
    return tool


def convert_telemetry_to_cks(fname):
    """Converts input bus quaternions to CK file"""
    CACHEDIR.mkdir(parents=True, exist_ok=True)
    qdf = pd.read_csv(fname)

    qt = Time(
        [
            datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=t / 1000)
            # - timedelta(seconds=37)
            for t in qdf.time.values
        ],
        scale="utc",
    )
    quats = qdf[["q1", "q2", "q3", "q4"]].values
    k = np.isclose(np.linalg.norm(quats, axis=1), 1, atol=1e-4)
    k = k & np.roll(k, 1) & np.roll(k, -1)
    qt, quats = qt[k], quats[k]
    quats /= np.linalg.norm(quats, axis=1, keepdims=True)

    spice_quats = np.asarray([quats[:, 3], quats[:, 0], quats[:, 1], quats[:, 2]]).T
    input_quats_path = CACHEDIR / "input_quats.csv"
    pd.DataFrame(np.hstack([qt.isot[:, None], spice_quats])).to_csv(
        input_quats_path, sep=" ", header=False, index=False
    )
    import_file_to_cache(
        url_key=f"https://github.com/pandoramission/pandoraspacecraft/src/pandoraspacecraft/data/ck/input_quats.csv",
        filename=str(input_quats_path),
        remove_original=True,
        pkgname="pandoraspacecraft",
        replace=False,
    )

    import_file_to_cache(
        url_key="https://github.com/pandoramission/pandoraspacecraft/src/pandoraspacecraft/data/kernels/Pandora/pandora_sclkscet.0005.tsc",
        filename=str(PACKAGEDIR / "data" / "kernels" / "Pandora" / "pandora_sclkscet.0005.tsc"),
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
    MAXIMUM_VALID_INTERVAL.  = 60.0
    
    CK_SEGMENT_ID            = 'SPACECRAFT ATTITUDE'
    PRODUCER_ID              = 'Christina Hedges'
    
    LSK_FILE_NAME            = '{_cache_rel(file_paths[1])}'
    SCLK_FILE_NAME           = '{_cache_rel(file_paths[2])}'
    
    \\begintext"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".tm", delete=False) as f:
        f.write(tock_string)
        setup_path = f.name

    subprocess.run(
        [
            _naif_tool("msopck"),
            setup_path,
            _cache_rel(file_paths[0]),
            f"pandora.bc",
        ],
        cwd=CACHEDIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    Path(setup_path).unlink()
    import_file_to_cache(
        f"https://github.com/pandoramission/pandoraspacecraft/src/pandoraspacecraft/data/kernels/Pandora/pandora.bc",
        str(CACHEDIR / "pandora.bc"),
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
    CACHEDIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(fname)

    qt = Time(
        [
            datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=t / 1000)
            # - timedelta(seconds=37)
            for t in df.time.values
        ],
        scale="utc",
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

    KERNELS = {
        "naif0012.tls": "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/lsk/",
        "pck00011.tpc": "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/",
        "gm_de440.tpc": "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/",
    }
    file_paths = get_file_paths(KERNELS)

    tospk_string13 = f"""\\begindata

    INPUT_DATA_TYPE    = 'STATES'
    OUTPUT_SPK_TYPE    = 13
    POLYNOM_DEGREE     = 3

    OBJECT_ID          = -167395
    CENTER_ID          = 399
    REF_FRAME_NAME     = 'J2000'
    PRODUCER_ID        = 'Christina Hedges'

    DATA_ORDER         = 'EPOCH X Y Z VX VY VZ'
    DATA_DELIMITER     = ','
    LINES_PER_RECORD   = 1
    INPUT_DATA_UNITS   = ( 'DISTANCES=km' )

    IGNORE_FIRST_LINE  = 0
    LEAPSECONDS_FILE   = '{_cache_rel(file_paths[0])}'

    APPEND_TO_OUTPUT  = 'YES'

    \\begintext"""

    tospk_string5 = f"""\\begindata

    INPUT_DATA_TYPE    = 'STATES'
    OUTPUT_SPK_TYPE    = 5

    OBJECT_ID          = -167395
    CENTER_ID          = 399
    REF_FRAME_NAME     = 'J2000'
    PRODUCER_ID        = 'Christina Hedges'

    DATA_ORDER         = 'EPOCH X Y Z VX VY VZ'
    DATA_DELIMITER     = ','
    LINES_PER_RECORD   = 1
    INPUT_DATA_UNITS   = ( 'DISTANCES=km' )

    IGNORE_FIRST_LINE  = 0
    LEAPSECONDS_FILE   = '{_cache_rel(file_paths[0])}'
    PCK_FILE           = '{_cache_rel(file_paths[2])}'

    APPEND_TO_OUTPUT  = 'YES'

    \\begintext"""

    dt = np.diff(qt.jd) * u.day.to(u.second)
    mdt = np.median(dt)
    left, right = np.asarray(
        find_merged_gaps((qt.jd - qt.jd[0]) * u.day.to(u.second), mdt * 3, mdt * 10)
    ).T
    a = np.hstack([np.asarray([left, right]).T.ravel()])

    if (CACHEDIR / "pandora.bsp").is_file():
        (CACHEDIR / "pandora.bsp").unlink()
    if (CACHEDIR / "input_telemetry.csv").is_file():
        (CACHEDIR / "input_telemetry.csv").unlink()

    for spktype_order in [13, 5]:
        # we append 13 first because we want to prioritize interpolated times over propagated
        for tdx, l, r in tqdm(zip(np.arange(0, len(a)), a[:-1], a[1:]), total=len(a)):
            if (tdx % 2) == 1:
                spktype = 5
                buffer = 40
                l1 = np.max([l - buffer, 0])
                r1 = np.min([r + buffer, len(df)])
            else:
                spktype = 13
                l1 = l
                r1 = r
            if spktype != spktype_order:
                continue
            df1 = pd.DataFrame(
                np.hstack(
                    [
                        qt.isot[l1 : r1 + 1][:, None],
                        positions[l1 : r1 + 1],
                        velocities[l1 : r1 + 1],
                    ]
                )
            )
            df1.to_csv(CACHEDIR / "input_telemetry.csv", header=False, index=False)
            with tempfile.NamedTemporaryFile(mode="w", suffix=".tm", delete=False) as f:
                f.write([tospk_string13 if spktype == 13 else tospk_string5][0])
                setup_path = f.name

            subprocess.run(
                [
                    _naif_tool("mkspk"),
                    "-setup",
                    setup_path,
                    "-input",
                    "input_telemetry.csv",
                    "-output",
                    "pandora.bsp",
                ],
                cwd=CACHEDIR,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            Path(setup_path).unlink()

        if (CACHEDIR / "input_telemetry.csv").is_file():
            (CACHEDIR / "input_telemetry.csv").unlink()

    import_file_to_cache(
        f"https://github.com/pandoramission/pandoraspacecraft/src/pandoraspacecraft/data/kernels/Pandora/pandora.bsp",
        str(CACHEDIR / "pandora.bsp"),
        remove_original=True,
        pkgname="pandoraspacecraft",
        replace=False,
    )


#     df = pd.read_csv(fname)
#     outname = "pandora"

#     qt = Time(
#         [
#             datetime(1970, 1, 1, tzinfo=timezone.utc)
#             + timedelta(seconds=t / 1000)
#             - timedelta(seconds=37)
#             for t in df.time.values
#         ]
#     )
#     positions = df[["p1", "p2", "p3"]].values
#     velocities = df[["v1", "v2", "v3"]].values

#     norm = np.linalg.norm(positions, axis=1)
#     resid = np.abs(norm - np.median(norm))
#     k = resid < 4 * np.median(resid)
#     k = k & np.roll(k, 1) & np.roll(k, -1)
#     qt, positions, velocities = qt[k], positions[k], velocities[k]

#     norm = np.linalg.norm(velocities, axis=1)
#     resid = np.abs(norm - np.median(norm))
#     k = resid < 4 * np.median(resid)
#     k = k & np.roll(k, 1) & np.roll(k, -1)
#     qt, positions, velocities = qt[k], positions[k], velocities[k]

#     norm = np.gradient(np.linalg.norm(positions, axis=1), qt.jd)
#     resid = np.abs(norm - np.median(norm))
#     k = resid < 4 * np.median(resid)
#     k = k & np.roll(k, 1) & np.roll(k, -1)
#     qt, positions, velocities = qt[k], positions[k], velocities[k]

#     norm = np.gradient(np.linalg.norm(velocities, axis=1), qt.jd)
#     resid = np.abs(norm - np.median(norm))
#     k = resid < 4 * np.median(resid)
#     k = k & np.roll(k, 1) & np.roll(k, -1)
#     qt, positions, velocities = qt[k], positions[k], velocities[k]

#     pd.DataFrame(np.hstack([qt.isot[:, None], positions, velocities])).to_csv(
#         f"{CACHEDIR}input_telemetry.csv", header=False, index=False
#     )
#     import_file_to_cache(
#         url_key=f"https://github.com/pandoramission/pandoraspacecraft/src/pandoraspacecraft/data/ck/input_telemetry.csv",
#         filename=f"{CACHEDIR}input_telemetry.csv",
#         remove_original=True,
#         pkgname="pandoraspacecraft",
#         replace=False,
#     )

#     KERNELS = {
#         "input_telemetry.csv": "https://github.com/pandoramission/pandoraspacecraft/src/pandoraspacecraft/data/ck/",
#         "naif0012.tls": "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/lsk/",
#         "pck00011.tpc": "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/",
#         "gm_de440.tpc": "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/",
#     }
#     file_paths = get_file_paths(KERNELS)

#     tospk_string = f"""\\begindata

# INPUT_DATA_TYPE    = 'STATES'
# OUTPUT_SPK_TYPE    = 9
# POLYNOM_DEGREE = 3

# OBJECT_ID          = -167395
# CENTER_ID          = 399
# REF_FRAME_NAME     = 'J2000'
# PRODUCER_ID        = 'Christina Hedges'

# DATA_ORDER         = 'EPOCH X Y Z VX VY VZ'
# DATA_DELIMITER     = ','
# LINES_PER_RECORD   = 1
# INPUT_DATA_UNITS   = ( 'DISTANCES=km' )

# IGNORE_FIRST_LINE  = 0
# LEAPSECONDS_FILE   = '{"/".join(file_paths[1].split("/")[-2:])}'

# \\begintext"""

#     tospk_string = f"""\\begindata

# INPUT_DATA_TYPE    = 'STATES'
# OUTPUT_SPK_TYPE    = 5

# OBJECT_ID          = -167395
# CENTER_ID          = 399
# REF_FRAME_NAME     = 'J2000'
# PRODUCER_ID        = 'Christina Hedges'

# DATA_ORDER         = 'EPOCH X Y Z VX VY VZ'
# DATA_DELIMITER     = ','
# LINES_PER_RECORD   = 1
# INPUT_DATA_UNITS   = ( 'DISTANCES=km' )

# IGNORE_FIRST_LINE  = 0
# LEAPSECONDS_FILE   = '{"/".join(file_paths[1].split("/")[-2:])}'
# PCK_FILE           = '{"/".join(file_paths[3].split("/")[-2:])}'

# \\begintext"""

#     with tempfile.NamedTemporaryFile(mode="w", suffix=".tm", delete=False) as f:
#         f.write(tospk_string)
#         setup_path = f.name
#     print(tospk_string)
#     subprocess.run(
#         [
#             "mkspk",
#             "-setup",
#             setup_path,
#             "-input",
#             f"{'/'.join(file_paths[0].split('/')[-2:])}",
#             "-output",
#             f"{outname}.bsp",
#         ],
#         cwd=CACHEDIR,
#         # stdout=subprocess.DEVNULL,
#         # stderr=subprocess.DEVNULL,
#     )

#     Path(setup_path).unlink()

#     import_file_to_cache(
#         f"https://github.com/pandoramission/pandoraspacecraft/src/pandoraspacecraft/data/kernels/Pandora/{outname}.bsp",
#         f"{CACHEDIR}{outname}.bsp",
#         remove_original=True,
#         pkgname="pandoraspacecraft",
#         replace=False,
#     )

#     _astropy_clear_download_cache(
#         f"https://github.com/pandoramission/pandoraspacecraft/src/pandoraspacecraft/data/ck/input_telemetry.csv",
#         "pandoraspacecraft",
#     )

#     if os.path.exists(setup_path):
#         os.remove(setup_path)


# def update_cks(quaternions_csv_filename):
#     df = pd.read_csv(quaternions_csv_filename)
#     qt = Time(
#         [
#             datetime(1970, 1, 1, tzinfo=timezone.utc)
#             + timedelta(seconds=t / 1000)
#             - timedelta(seconds=37)
#             for t in df.time.values
#         ]
#     )
#     k = qt.jd > 2461052
#     df, qt = df[k], qt[k]

#     # Split at every 7 days since launch
#     ph = qt.jd - ((qt.jd - 2461052) % 7)
#     splits = np.where(np.diff(ph) == 7)[0] + 1

#     with tempfile.TemporaryDirectory() as d:
#         for a, b in zip(np.hstack([splits[:-1]]), splits[1:]):
#             buffer = 10000
#             a = np.min([0, a - buffer])
#             b = np.min([b + buffer, len(df)])
#             df1 = df[a:b]
#             chunk_name = f"pandora_ck_{int(np.round(qt.jd[a] - 2461052)):05}"
#             path = Path(d) / f"{chunk_name}.csv"
#             df1.to_csv(path, index=False)
#             convert_telemetry_to_cks(str(path))
#             shutil.copy(
#                 cache_contents("pandoraspacecraft")[
#                     f"https://github.com/pandoramission/pandoraspacecraft/src/pandoraspacecraft/data/kernels/Pandora/{chunk_name}.bc"
#                 ],
#                 PACKAGEDIR + f"/data/kernels/Pandora/{chunk_name}.bc",
#             )


# def update_spks(positions_csv_filename):
#     df = pd.read_csv(positions_csv_filename)
#     qt = Time(
#         [
#             datetime(1970, 1, 1, tzinfo=timezone.utc)
#             + timedelta(seconds=t / 1000)
#             - timedelta(seconds=37)
#             for t in df.time.values
#         ]
#     )
#     k = qt.jd > 2461052
#     df, qt = df[k], qt[k]

#     # Split at every 7 days since launch
#     ph = qt.jd - ((qt.jd - 2461052) % 7)
#     splits = np.where(np.diff(ph) == 7)[0] + 1

#     with tempfile.TemporaryDirectory() as d:
#         for a, b in zip(np.hstack([splits[:-1]]), splits[1:]):
#             df1 = df[a:b]
#             chunk_name = f"pandora_spk_{int(np.round(qt.jd[a] - 2461052)):05}"
#             path = Path(d) / f"{chunk_name}.csv"
#             df1.to_csv(path, index=False)
#             convert_telemetry_to_spks(str(path))
#             shutil.copy(
#                 cache_contents("pandoraspacecraft")[
#                     f"https://github.com/pandoramission/pandoraspacecraft/src/pandoraspacecraft/data/kernels/Pandora/{chunk_name}.bsp"
#                 ],
#                 PACKAGEDIR + f"/data/kernels/Pandora/{chunk_name}.bsp",
#             )


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
    out_kernel = PACKAGEDIR / "data" / "kernels" / "testkernels" / "earth_sun_moon_pandora.bsp"
    if os.path.exists(out_kernel):
        os.remove(out_kernel)

    handle = spiceypy.spkopn(str(out_kernel), "Truncated ephemeris", 1000)

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


def convert_tles_to_spk():
    CACHEDIR.mkdir(parents=True, exist_ok=True)
    tle_paths = np.sort(glob(str(TLEDIR / "*.tle")))
    for f in tle_paths:
        p = Path(f)
        text = p.read_text()
        text = text.replace("1 99152U", "1 67395U")
        text = text.replace("2 99152", "2 67395")
        p.write_text(text)
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
        tle_name = Path(tle_path).name

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

INPUT_DATA_FILE   = '{_cache_rel(file_paths[0])}'
OUTPUT_SPK_FILE   = 'pandora.bsp'

LEAPSECONDS_FILE  = '{_cache_rel(file_paths[1])}'
PCK_FILE          = '{_cache_rel(file_paths[2])}'
        
TLE_START_PAD = '2 days'
TLE_STOP_PAD  = '{"2 days" if tle_path != tle_paths[-1] else "365 days"}'

CENTER_ID         = 399
REF_FRAME_NAME    = 'J2000'

OBJECT_ID         = {sc_id}
OBJECT_NAME       = 'PANDORA SPACECRAFT'

PRODUCER_ID = 'PandoraDPC'

APPEND_TO_OUTPUT  = 'YES'

\\begintext"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".tm", delete=False) as f:
            f.write(totle_string)
            setup_path = f.name

        subprocess.run(
            [
                _naif_tool("mkspk"),
                "-setup",
                setup_path,
                "-output",
                "pandora_tle.bsp",
            ],
            cwd=CACHEDIR,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        Path(setup_path).unlink()

        _astropy_clear_download_cache(
            f"https://github.com/pandoramission/pandoraspacecraft/src/pandoraspacecraft/data/tle/{tle_name}",
            "pandoraspacecraft",
        )

        if os.path.exists(setup_path):
            os.remove(setup_path)

    shutil.move(
        CACHEDIR / "pandora_tle.bsp",
        KERNELDIR / "Pandora" / "pandora_tle.bsp",
    )

    # import_file_to_cache(
    #     f"https://github.com/pandoramission/pandoraspacecraft/src/pandoraspacecraft/data/kernels/Pandora/{tle_name.split('.tle')[0]}.spk",
    #     f"{CACHEDIR}/{tle_name.split('.tle')[0]}.spk",
    #     remove_original=True,
    #     pkgname="pandoraspacecraft",
    #     replace=False,
    # )


def create_meta_test_kernel():
    """Create a meta kernel out of the built in SPICE kernels
    This meta kernel is only for testing, but doesn't require internet access to be able to generate.
    """
    paths = [
        *glob(str(PACKAGEDIR / "data" / "kernels" / "Pandora" / "*")),
    ]

    paths = [
        p
        for p in paths
        if (not p.endswith("bc"))
        & (not p.endswith("bsp"))
        & (not p.endswith("spk"))
        & (not p.endswith("ck"))
    ]
    paths = [*glob(str(PACKAGEDIR / "data" / "kernels" / "testkernels" / "*")), *paths]

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


def split_spk():
    """Splits the existing SPK file into many day long files, puts them in the package directory for upload to github."""
    # convert_telemetry_to_spks(fname, outname="pandora")
    file_paths = ["", ""]
    file_paths[0] = cache_contents("pandoraspacecraft")[
        "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/lsk/naif0012.tls"
    ]
    file_paths[1] = cache_contents("pandoraspacecraft")[
        "https://github.com/pandoramission/pandoraspacecraft/src/pandoraspacecraft/data/kernels/Pandora/pandora.bsp"
    ]
    r = subprocess.run(
        [
            _naif_tool("brief"),
            "-utc",
            _cache_rel(file_paths[0]),
            _cache_rel(file_paths[1]),
        ],
        capture_output=True,
        text=True,
        check=True,
        cwd=CACHEDIR,
    ).stdout
    start_time, end_time = np.asarray(r.split("\n")[-3].strip().split("  "))[[0, -1]]
    start_time = Time.strptime(start_time, format_string="%Y-%b-%d %H:%M:%S.%f")
    end_time = Time.strptime(end_time, format_string="%Y-%b-%d %H:%M:%S.%f")
    # whole days only!
    times = Time(
        np.arange(np.ceil(start_time.jd), np.floor(end_time.jd), 1), format="jd"
    )

    for t1, t2 in tqdm(zip(times[:-1], times[1:]), total=len(times) - 1):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".tm") as f:

            def get_split_string():
                return f"""LEAPSECONDS_KERNEL = {_cache_rel(file_paths[0])}
SPK_KERNEL         = pandora_{t1.strftime("%Y%j")}.bsp
BEGIN_TIME         = {t1.strftime("%Y %b %d %H:%M:%S UTC").upper()}
END_TIME           = {t2.strftime("%Y %b %d %H:%M:%S UTC").upper()}
SOURCE_SPK_KERNEL  = {_cache_rel(file_paths[1])}
"""

            f.write(get_split_string())
            f.flush()
            setup_path = f.name
            subprocess.run(
                [_naif_tool("spkmerge"), setup_path],
                text=True,
                cwd=CACHEDIR,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            shutil.move(
                CACHEDIR / f"pandora_{t1.strftime('%Y%j')}.bsp",
                PACKAGEDIR / "data" / "kernels" / "Pandora" / f"pandora_{t1.strftime('%Y%j')}.bsp",
            )

    return


def split_ck():
    """Splits the existing SPK file into many day long files, puts them in the package directory for upload to github."""
    # convert_telemetry_to_spks(fname, outname="pandora")
    file_paths = ["", "", ""]
    file_paths[0] = cache_contents("pandoraspacecraft")[
        "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/lsk/naif0012.tls"
    ]
    file_paths[1] = cache_contents("pandoraspacecraft")[
        "https://github.com/pandoramission/pandoraspacecraft/src/pandoraspacecraft/data/kernels/Pandora/pandora_sclkscet.0005.tsc"
    ]
    file_paths[2] = cache_contents("pandoraspacecraft")[
        "https://github.com/pandoramission/pandoraspacecraft/src/pandoraspacecraft/data/kernels/Pandora/pandora.bc"
    ]
    r = subprocess.run(
        [
            _naif_tool("ckbrief"),
            _cache_rel(file_paths[2]),
            _cache_rel(file_paths[0]),
            _cache_rel(file_paths[1]),
        ],
        capture_output=True,
        text=True,
        check=True,
        cwd=CACHEDIR,
    ).stdout
    start_time, end_time = (
        " ".join(np.asarray(r.split("\n")[-3].strip().split(" "))[:2]),
        " ".join(np.asarray(r.split("\n")[-3].strip().split(" "))[2:4]),
    )

    start_time = Time.strptime(start_time, format_string="%Y-%b-%d %H:%M:%S.%f")
    end_time = Time.strptime(end_time, format_string="%Y-%b-%d %H:%M:%S.%f")
    # whole days only!
    times = Time(
        np.arange(np.ceil(start_time.jd), np.floor(end_time.jd), 1), format="jd"
    )

    for t1, t2 in tqdm(zip(times[:-1], times[1:]), total=len(times) - 1):
        subprocess.run(
            [
                _naif_tool("ckslicer"),
                "-lsk",
                _cache_rel(file_paths[0]),
                "-sclk",
                _cache_rel(file_paths[1]),
                "-inputck",
                _cache_rel(file_paths[2]),
                "-outputck",
                f"pandora_{t1.strftime('%Y%j')}.bc",
                "-id",
                "-167395000",
                "-timetype",
                "utc",
                "-start",
                t1.strftime("%Y %b %d %H:%M:%S UTC").upper(),
                "-stop",
                t2.strftime("%Y %b %d %H:%M:%S UTC").upper(),
            ],
            check=True,
            cwd=CACHEDIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        shutil.move(
            CACHEDIR / f"pandora_{t1.strftime('%Y%j')}.bc",
            PACKAGEDIR / "data" / "kernels" / "Pandora" / f"pandora_{t1.strftime('%Y%j')}.bc",
        )

    return
