"""Classes for working with the orbits of spacecraft"""

from typing import Union

import astropy.units as u
import matplotlib.pyplot as plt
import numpy as np
import numpy.typing as npt
import spiceypy
from astropy.constants import c
from astropy.coordinates import SkyCoord
from astropy.time import Time
from astropy.utils.data import cache_contents

from . import is_test_mode, log
from .utils import (
    convert_tles,
    create_meta_kernel,
    create_meta_test_kernel,
    vec_to_coord,
)


class BadEphemeris(Exception):
    def __init__(self, message):
        super().__init__(message)


__all__ = ["PandoraSpacecraft"]


def _process_time(time) -> Time:
    """convert to astropy.time.Time, if needed"""
    if not isinstance(time, Time):
        try:
            time = Time(time, format="jd", scale="tdb")
        except ValueError:
            try:
                time = Time(time, scale="tdb")
            except Exception:
                raise ValueError(
                    "Can not parse input time. Pass an `astropy.time.Time` object."
                )
    if time.scale != "tdb":
        time = Time(time, scale="tdb")
    if time.ndim == 0:
        time = Time([time])
    return time


class Spacecraft(object):
    """
    A base class for handling spacecraft ephemeris data and calculations.

    This class provides methods to retrieve spacecraft position, velocity, light travel time,
    and related calculations using SPICE kernels. It supports transformations between
    time formats and computes barycentric time corrections and velocity aberration effects.

    Attributes
    ----------
    start_time : astropy.time.Time
        The start time of the loaded SPICE kernel data.
    end_time : astropy.time.Time
        The end time of the loaded SPICE kernel data.

    Methods
    -------
    get_spacecraft_position(time, observer="SOLAR SYSTEM BARYCENTER")
        Returns the position vector (x, y, z) in kilometers relative to the specified observer.
    get_spacecraft_velocity(time, observer="SOLAR SYSTEM BARYCENTER")
        Returns the velocity vector (vx, vy, vz) in kilometers per second relative to the observer.
    get_spacecraft_light_travel_time(time, observer="SOLAR SYSTEM BARYCENTER")
        Computes the one-way light travel time to the observer in seconds.
    get_barycentric_time_correction(time, ra, dec)
        Calculates the barycentric time correction for a target specified by RA and Dec.
    get_velocity_aberrated_positions(time, ra, dec)
        Computes the RA and Dec of a target after applying velocity aberration.
    """

    def __init__(self):
        """
        Initializes the Spacecraft object and loads SPICE kernels.

        This method clears any previously loaded SPICE kernels, loads the kernels specified
        in the `Meta.txt` file, and determines the start and end times of the kernel data.

        Parameters
        ----------
        test_mode: bool
            Whether to use the test kernels. Test kernels are small, truncated kernels for each spacecraft valid over a short time range.
            If you use this mode, pandoraspacecraft will not connect to the internet, download new kernels, or used cached kernels.
            Use this mode if you want to test pandoraspacecraft as a dependency in your package.

        Raises
        ------
        Exception
            If there is an issue loading the SPICE kernels or retrieving the kernel time coverage.
        """
        if is_test_mode():
            create_meta_test_kernel()
            log.warning(
                "`pandoraspacecraft` is in test mode, and will not download new kernels. Will truncated kernels."
            )
            self.meta_kernel = cache_contents(pkgname="pandoraspacecraft")[
                "https://github.com/pandoramission/pandoraspacecraft/src/pandoraspacecraft/data/TestMeta.txt"
            ]
        else:
            convert_tles(run_all=False)
            log.info(
                "`pandoraspacecraft` is not in test mode, and will download and use kernels if available."
            )
            create_meta_kernel()
            self.meta_kernel = cache_contents(pkgname="pandoraspacecraft")[
                "https://github.com/pandoramission/pandoraspacecraft/src/pandoraspacecraft/data/Meta.txt"
            ]
        spiceypy.kclear()
        spiceypy.furnsh(self.meta_kernel)
        self.start_time, self.end_time = self._get_kernel_start_and_end_times()

    def _get_all_kernel_start_and_end_times(self):
        # Get a list of loaded kernels
        kernel_list = spiceypy.ktotal("ALL")  # Get the count of all loaded kernels
        start_et = []
        end_et = []

        for i in range(kernel_list):
            kernel_name = spiceypy.kdata(i, "ALL")[0]

            # Check if the kernel is SPK or CK to calculate coverage
            kernel_type = spiceypy.kdata(i, "ALL")[1]

            if kernel_type in ["SPK", "CK"]:
                # Create a window for coverage
                coverage_window = spiceypy.stypes.SPICEDOUBLE_CELL(2**10)

                # Query coverage for the specific kernel
                try:
                    if kernel_type == "SPK":
                        spiceypy.spkcov(
                            kernel_name, self.spacecraft_code, coverage_window
                        )  # Replace with your NAIF ID
                    else:
                        continue

                    # Extract start and end times for the current kernel
                    interval_start = spiceypy.wnfetd(coverage_window, 0)[0]
                    interval_end = spiceypy.wnfetd(coverage_window, 0)[1]

                    # Update the global start and end times
                    start_et.append(interval_start)
                    end_et.append(interval_end)
                except Exception:
                    continue
        start_time = Time(spiceypy.et2datetime(start_et), scale="utc")
        end_time = Time(spiceypy.et2datetime(end_et), scale="utc")
        return start_time, end_time

    def _get_kernel_start_and_end_times(self):
        start, end = self._get_all_kernel_start_and_end_times()
        return start.min(), end.min()

    def __repr__(self):
        return "Spacecraft"

    def _get_state_vector(self, time: Time, observer="SOLAR SYSTEM BARYCENTER"):
        # ndim = time.ndim
        time = _process_time(time)
        # times are in BJD in TDB, we convert to ET in BJD
        et = np.asarray([spiceypy.unitim(t.jd, "JED", "ET") for t in time])
        try:
            state, light_travel_time = spiceypy.spkezr(
                f"{self.spacecraft_code}",
                et,
                "J2000",
                "NONE",
                observer,
            )
        except spiceypy.SpiceSPKINSUFFDATA:
            raise BadEphemeris(
                "The time you have requested is outside of the time range where data exists for this spacecraft."
            )
        # if ndim == 0:
        #     return np.asarray(state)[0], np.asarray(light_travel_time)[0]
        return np.asarray(state), np.asarray(light_travel_time)

    def get_spacecraft_position(
        self, time: Time, observer="SOLAR SYSTEM BARYCENTER"
    ) -> u.Quantity:
        """Returns the position vector (x, y, z) in [km] for all `time` w.r.t the observer.

        Parameters
        -----------
        time : astropy.time.Time
            Time array at which to estimate position. Time must be in BJD.
        observer : string
            Observer body. Common options include "SOLAR SYSTEM BARYCENTER", "EARTH BARYCENTER", "MOON BARYCENTER"
        """
        return self._get_state_vector(time=time, observer=observer)[0][:, :3] * u.km

    def get_spacecraft_velocity(
        self, time: Time, observer="SOLAR SYSTEM BARYCENTER"
    ) -> u.Quantity:
        """Returns the position vector (vx, vy, vz) in [km/s] for all `time` w.r.t the observer.

        Parameters
        ----------
        time : astropy.time.Time
            Time array at which to estimate velocity. Time must be in BJD.
        observer : string
            Observer body. Common options include "SOLAR SYSTEM BARYCENTER", "EARTH BARYCENTER", "MOON BARYCENTER"
        """
        return (
            self._get_state_vector(time=time, observer=observer)[0][:, 3:] * u.km / u.s
        )

    def get_spacecraft_light_travel_time(
        self, time: Time, observer="SOLAR SYSTEM BARYCENTER"
    ) -> u.Quantity:
        """Returns the one-way light travel time in seconds for all `time` w.r.t the observer.

        Parameters
        ----------
        time : astropy.time.Time
            Time array at which to estimate position. Time must be in BJD.
        observer : string
            Observer body. Common options include "SOLAR SYSTEM BARYCENTER", "EARTH BARYCENTER", "MOON BARYCENTER"
        """
        return self._get_state_vector(time=time, observer=observer)[1] * u.s

    def get_barycentric_time_correction(
        self, time: Time, ra: Union[float, npt.NDArray], dec: Union[float, npt.NDArray]
    ) -> npt.NDArray:
        """Returns the barycentric time correction in days for observations of a particular target specified by RA and Dec.

        Note that `time` here must be the time of the spacecraft clock.
        This means that for SPOC data this should be the time without the SPOC barycentric correction applied.

        Parameters
        ----------
        time : astropy.time.Time
            Time array at which to estimate position. Time must be at the spacecraft.
        ra : float, np.ndarray
            The right ascention of the target in degrees
        dec : float, np.ndarray
            The declination of the target in degrees

        Returns
        -------
        tcorr : u.Quantity
            Barycentric time correction in seconds
        """
        zerod = np.ndim(ra) == 0
        ra, dec = np.atleast_1d(ra), np.atleast_1d(dec)
        time = np.atleast_1d(time)

        # Compute the star vector (normalized direction vector for the target)
        star_vector = np.array(
            [
                np.cos(np.deg2rad(dec.ravel())) * np.cos(np.deg2rad(ra.ravel())),
                np.cos(np.deg2rad(dec.ravel())) * np.sin(np.deg2rad(ra.ravel())),
                np.sin(np.deg2rad(dec.ravel())),
            ]
        )
        star_vector /= np.linalg.norm(star_vector, axis=0)
        position = self.get_spacecraft_position(time=time)
        tcorr = ((position * u.km).dot(star_vector) / (c)).to(u.s).value
        if zerod:
            return tcorr[:, 0] * u.s
        return tcorr.reshape((*time.shape, *ra.shape)) * u.s

    def get_velocity_aberrated_positions(
        self, time: Time, ra: float, dec: float
    ) -> (u.Quantity, u.Quantity):
        """Returns the RA and Dec after velocity aberration has been applied.

        Note that `time` here must be time in spacecraft time.

        Parameters
        ----------
        time : astropy.time.Time
            Time array at which to estimate position. Time must be in TDB.
        ra : float, np.ndarray
            The right ascention of the target in degrees
        dec : float, np.ndarray
            The declination of the target in degrees

        Returns
        -------
        ra : u.Quantity
            Aberrated RA
        dec : u.Quantity
            Aberrated Dec
        """
        zerod = np.ndim(ra) == 0
        ra, dec = np.atleast_1d(ra), np.atleast_1d(dec)
        time = np.atleast_1d(time)

        # Compute the star vector (normalized direction vector for the target)
        star_vector = np.array(
            [
                np.cos(np.deg2rad(dec.ravel())) * np.cos(np.deg2rad(ra.ravel())),
                np.cos(np.deg2rad(dec.ravel())) * np.sin(np.deg2rad(ra.ravel())),
                np.sin(np.deg2rad(dec.ravel())),
            ]
        )
        # Normalize star_vector for safety (though it should already be normalized)
        star_vector /= np.linalg.norm(star_vector, axis=0)

        # Get the spacecraft velocity in m/s
        velocity = (
            self.get_spacecraft_velocity(time=time).value * 1000
        )  # Convert km/s to m/s

        # Compute beta vector (velocity / speed of light)
        beta = velocity / c.value

        # Compute the scalar product beta \cdot star_vector
        # beta_dot_star = np.sum(beta * star_vector, axis=-1)
        beta_dot_star = beta.dot(star_vector)

        # Compute the relativistic factor gamma
        gamma = 1 / np.sqrt(1 - np.sum(beta**2, axis=-1))

        # Apply the aberration formula
        factor = 1 / (1 + beta_dot_star)

        #    return factor.shape, gamma.shape, star_vector.shape, beta.shape
        star_vector_ab = factor[:, None, :] * (
            gamma[:, None, None] * star_vector[None, :, :] + beta[:, :, None]
        )

        # Normalize the aberrated vector
        star_vector_ab /= np.linalg.norm(star_vector_ab, axis=1, keepdims=True)

        # Convert back to RA and Dec
        ra_aberrated = np.rad2deg(
            np.arctan2(star_vector_ab[:, 1], star_vector_ab[:, 0])
        )
        dec_aberrated = np.rad2deg(np.arcsin(star_vector_ab[:, 2]))

        # Ensure RA is in [0, 360] range
        ra_aberrated = np.mod(ra_aberrated, 360)

        # Reshape output to match input dimensions
        ra_aberrated, dec_aberrated = (
            ra_aberrated.reshape((*time.shape, *ra.shape)),
            dec_aberrated.reshape((*time.shape, *dec.shape)),
        )
        if zerod:
            return ra_aberrated[:, 0] * u.deg, dec_aberrated[:, 0] * u.deg
        return (
            ra_aberrated.reshape((*time.shape, *ra.shape)) * u.deg,
            dec_aberrated.reshape((*time.shape, *ra.shape)) * u.deg,
        )

    def get_differential_velocity_aberrated_positions(
        self, time: Time, ra: float, dec: float, ra0: float, dec0: float
    ) -> (u.Quantity, u.Quantity):
        """Returns the RA and Dec after differential velocity aberration has been applied.

        This is the effect of velocity aberration, accounting for the fact that the spacecraft tracks a given point in the sky.
        All stars undergo velocity aberration. During observation, the spacecraft tracks stars, therefore accounting
        for the bulk of this motion. This function enables you to calculate the differential velocity aberration
        from the spacecraft pointing.

        Parameters
        ----------
        time : astropy.time.Time
            Time array at which to estimate position.
        ra : float, np.ndarray
            The right ascention of the target(s) in degrees
        dec : float, np.ndarray
            The declination of the target(s) in degrees
        ra0 : float
            The RA of the target which the spacecraft is pointed towards.
        dec0 : float
            The Dec of the target which the spacecraft is pointed towards.

        Returns
        -------
        ra : u.Quantity
            Aberrated RA
        dec : u.Quantity
            Aberrated Dec
        """
        zerod = np.ndim(ra) == 0
        ra, dec = np.atleast_1d(ra), np.atleast_1d(dec)
        time = np.atleast_1d(time)

        nt = len(time) if np.ndim(time) == 1 else 1
        ra_ab, dec_ab = self.get_velocity_aberrated_positions(
            time, ra.ravel(), dec.ravel()
        )
        ra_ab, dec_ab = np.atleast_2d(ra_ab), np.atleast_2d(dec_ab)
        ra0_ab, dec0_ab = self.get_velocity_aberrated_positions(time, ra0, dec0)
        sep = SkyCoord(ra0, dec0, unit="deg").separation(
            SkyCoord(ra0_ab, dec0_ab, unit="deg")
        )
        pa = SkyCoord(ra0, dec0, unit="deg").position_angle(
            SkyCoord(ra0_ab, dec0_ab, unit="deg")
        )

        recentered_coords = SkyCoord(ra_ab, dec_ab, unit="deg").directional_offset_by(
            separation=-sep[:, None], position_angle=pa[:, None]
        )

        ra_ab_recentered, dec_ab_recentered = (
            recentered_coords.ra.deg,
            recentered_coords.dec.deg,
        )
        ra_ab_recentered.reshape((nt, *ra.shape))
        ra_ab_recentered = ra_ab_recentered.reshape((nt, *ra.shape))
        dec_ab_recentered = dec_ab_recentered.reshape((nt, *ra.shape))
        if zerod:
            return ra_ab_recentered[:, 0] * u.deg, dec_ab_recentered[:, 0] * u.deg
        return ra_ab_recentered * u.deg, dec_ab_recentered * u.deg

    def plot_earth(self, ax=None):
        earth_rad = spiceypy.bodvrd("EARTH", "RADII", 3)[1][0]
        u = np.linspace(0, 2 * np.pi, 50)
        v = np.linspace(0, np.pi, 50)
        earth = np.asarray(
            [
                np.outer(np.cos(u), np.sin(v)) * earth_rad,
                np.outer(np.sin(u), np.sin(v)) * earth_rad,
                np.outer(np.ones_like(u), np.cos(v)) * earth_rad,
            ]
        )
        if ax is None:
            fig = plt.figure(figsize=(7, 7), dpi=150)
            ax = fig.add_subplot(111, projection="3d")
        ax.plot_surface(*earth, alpha=0.3, color="C0")
        ax.set(
            xlabel="x [km]",
            ylabel="y [km]",
            zlabel="z [km]",
            aspect="equal",
        )
        return ax

    def plot_position(self, time, ax=None):
        time
        position = self.get_spacecraft_position(time, "EARTH").value

        if ax is None:
            fig = plt.figure(figsize=(7, 7), dpi=150)
            ax = fig.add_subplot(111, projection="3d")
        ax.plot(*position.T, label="Pandora", c="grey")
        ax.set(
            title="Pandora Position",
            xlabel="x [km]",
            ylabel="y [km]",
            zlabel="z [km]",
            aspect="equal",
        )
        return ax

    def get_earth_subpoint(self, time) -> u.Quantity:
        """Returns the lattitude and longitude of the point underneath Pandora, accounting for light travel time and aberations.

        Parameters
        ----------
        time : astropy.time.Time
            Time array at which to estimate position.

        Returns
        -------
        lon : u.Quantity
            Longitude of the point on earth below the spacecraft in degrees
        lat : u.Quantity
            Latitude of the point on earth below the spacecraft in degrees
        """

        ndim = time.ndim
        time = _process_time(time)
        ets = np.asarray([spiceypy.utc2et(t) for t in time.isot])
        subpoint = np.zeros((len(ets), 3), dtype=float)
        for i, et in enumerate(ets):
            # 1) sub-spacecraft point on Earth
            subpoint[i], _, _ = spiceypy.subpnt(
                "NEAR POINT: ELLIPSOID",
                "EARTH",
                et,
                "IAU_EARTH",
                "LT+S",
                f"{self.spacecraft_code}",
            )

        # Earth radii (km) from the kernel set
        _, (re, rp, _) = spiceypy.bodvrd(
            "EARTH", "RADII", 3
        )  # re = equatorial, rp = polar
        f = (re - rp) / re  # flattening

        # spoint from subpnt is in km in IAU_EARTH
        lon, lat, _ = np.asarray(
            [spiceypy.recgeo(spoint, re, f) for spoint in subpoint]
        ).T  # radians, radians, km
        lon, lat = np.rad2deg(lon), np.rad2deg(lat)

        if ndim == 0:
            return lon[0] * u.deg, lat[0] * u.deg
        return lon * u.deg, lat * u.deg

    def get_earth_illumination(self, time) -> u.Quantity:
        """Returns the angle of incidence of sunlight on the earth directly under Pandora

        Parameters
        ----------
        time : astropy.time.Time
            Time array at which to estimate position.

        Returns
        -------
        incidence : u.Quantity
            Incidence of sunlight on the point on earth below the spacecraft in degrees.
        """

        ndim = time.ndim
        time = _process_time(time)
        ets = np.asarray([spiceypy.utc2et(t) for t in time.isot])
        phase, incidence = np.zeros((2, len(ets)), dtype=float)
        for i, et in enumerate(ets):
            # 1) sub-spacecraft point on Earth
            spoint, _, _ = spiceypy.subpnt(
                "NEAR POINT: ELLIPSOID",
                "EARTH",
                et,
                "IAU_EARTH",
                "LT+S",
                f"{self.spacecraft_code}",
            )

            # 2) illumination at that surface point (Sun as illuminator)
            # Returns: (trgepc, srfvec, phase, incdnc, emissn)
            _, _, phase[i], incidence[i], _ = spiceypy.illumg(
                "ELLIPSOID",
                "EARTH",
                "SUN",
                et,
                "IAU_EARTH",
                "LT+S",
                f"{self.spacecraft_code}",
                spoint,
            )

        if ndim == 0:
            return np.rad2deg(incidence[0]) * u.deg  # , np.rad2deg(phase[0])
        return np.rad2deg(incidence) * u.deg  # , np.rad2deg(phase)

    def get_period(self, time) -> u.Quantity:
        """Returns the orbital period of Pandora at each time in minutes.

        Parameters
        ----------
        time: astropy.time.Time
            Time array at which to estimate position.

        Returns
        -------
        period : u.Quantity
            Period of the spacecraft at the given time in minutes
        """

        GM_EARTH = 398600.4418
        ndim = time.ndim
        time = _process_time(time)

        # Osculating elements at epoch et
        # Returns: [rp, ecc, inc, lnode, argp, m0, t0, mu]
        elts = np.asarray(
            [
                spiceypy.oscelt(
                    spiceypy.spkezr(
                        f"{self.spacecraft_code}",
                        spiceypy.utc2et(t.isot),
                        "J2000",
                        "NONE",
                        "EARTH",
                    )[0],
                    spiceypy.utc2et(t.isot),
                    GM_EARTH,
                )
                for t in time
            ]
        )
        rp = elts[:, 0]  # periapsis radius (km)
        ecc = elts[:, 1]
        a = rp / (1.0 - ecc)  # km
        period = 2 * np.pi * np.sqrt(a**3 / GM_EARTH)  # seconds
        if ndim == 0:
            return (period[0] * u.second).to(u.minute)
        return (period * u.second).to(u.minute)

    def get_altitude(self, time) -> u.Quantity:
        """Returns the altitude of Pandora at each time in km.

        Parameters
        ----------
        time : astropy.time.Time
            Time array at which to estimate position.

        Returns
        -------
        altitude : u.Quantity
            Altitude of the spacecraft at the given time in km
        """
        return (
            np.linalg.norm(self.get_spacecraft_position(time, "earth").value, axis=1)
            * u.km
        )

    def get_angle_to_body(self, time, coord, body="SUN") -> u.Quantity:
        """Returns the angle between Pandora and the specified body in degrees.

        Parameters
        ----------
        time: astropy.time.Time
            Time array at which to estimate position.

        Returns
        -------
        angle : u.Quantity
            Angle between Pandora and the body in degrees.
        """
        time = _process_time(time)
        if body.endswith("_LIMB"):
            pos = -self.get_spacecraft_position(time, body.split("_LIMB")[0])
        else:
            pos = -self.get_spacecraft_position(time, body)
        angle = coord.separation(vec_to_coord(*pos.T)).deg
        if body.endswith("_LIMB"):
            R = spiceypy.bodvrd(body.split("_LIMB")[0], "RADII", 3)[1][0]
            # print(norm)
            angle_limb = np.rad2deg(np.arcsin((R) / (np.linalg.norm(pos, axis=1))))
            angle -= angle_limb
        return angle * u.deg


class PandoraSpacecraft(Spacecraft):
    """
    A class representing the Pandora spacecraft.

    This class extends the `Spacecraft` base class and includes spacecraft-specific
    configurations, such as the unique SPICE NAIF ID code for the Pandora mission.

    Attributes
    ----------
    spacecraft_code : int
        The SPICE NAIF ID code for the Pandora spacecraft.
    time_offset : int
        The JD value for the launch date of Pandora
    """

    spacecraft_code = -167395
    time_offset = 2461052

    def __repr__(self):
        return "PandoraSpacecraft"


# Pre launch ID 799998031
