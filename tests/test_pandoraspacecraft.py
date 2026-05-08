import astropy.units as u
import numpy as np
from astropy.coordinates import Angle
from astropy.time import Time

import pandoraspacecraft


def test_pandora_truncated():
    pandoraspacecraft.enable_test_mode()
    ps = pandoraspacecraft.PandoraSpacecraft()
    assert ps.start_time > Time("2026-2-19 20:09:56.999998", scale="tdb")
    assert ps.end_time < Time("2026-02-26 11:33:59.999999", scale="tdb")
    time = Time("2026-02-22 13:00:00", scale="tdb")
    ra = 300
    dec = 10
    velocity = ps.get_spacecraft_velocity(time, observer="EARTH")
    assert velocity.shape == (1, 3)
    position = ps.get_spacecraft_position(time, observer="EARTH")
    assert position.shape == (1, 3)
    lt = ps.get_spacecraft_light_travel_time(time)
    assert lt.shape == (1,)
    assert np.isclose(lt.value, 500, atol=50)
    ra_result, dec_result = ps.get_velocity_aberrated_positions(time, ra, dec)
    assert ra_result.shape == (1,)
    assert dec_result.shape == (1,)
    ra_result, dec_result = ps.get_differential_velocity_aberrated_positions(
        time, ra, dec, ra0=301, dec0=11
    )
    assert ra_result.shape == (1,)
    assert dec_result.shape == (1,)

    # ps.get_angle_to_body(time, "z", "earth")
    # ps.get_angle_to_body(time, [0, 0, 1], "earth")
    ps.get_angle_to_body(time, "z", "earth", pointing_vecs=[0, 0, 1])

    pandoraspacecraft.disable_test_mode()


def test_utils():
    ra, dec = 10, 10
    pandoraspacecraft.utils.radec_to_vec(ra, dec)
    pandoraspacecraft.utils.radec_to_vec(ra * u.deg, dec * u.deg)
    vec = pandoraspacecraft.utils.radec_to_vec(Angle(ra * u.deg), Angle(dec * u.deg))
    ra2, dec2 = pandoraspacecraft.utils.radec_from_vec(vec)
    assert np.isclose(ra, ra2)
    assert np.isclose(dec, dec2)

    assert np.allclose(
        [ra, dec],
        pandoraspacecraft.utils.vec_to_radec(
            *pandoraspacecraft.utils.radec_to_vec(ra, dec)
        ),
    )
