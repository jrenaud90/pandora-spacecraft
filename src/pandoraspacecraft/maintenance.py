"""Tools to maintain package"""

import spiceypy
import pandas as pd
import numpy as np
from astropy.time import Time
import tempfile
from pathlib import Path
import shutil
from astropy.utils.data import cache_contents
from datetime import datetime, timezone, timedelta
from .utils import (
    convert_telemetry_to_cks,
    convert_telemetry_to_spks,
    create_meta_test_kernel,
)
from . import PACKAGEDIR
import os


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
