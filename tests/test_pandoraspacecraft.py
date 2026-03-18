import numpy as np
from astropy.time import Time

import pandoraspacecraft


def test_tess_truncated():
    pandoraspacecraft.enable_test_mode()
    ps = pandoraspacecraft.PandoraSpacecraft()
    assert ps.start_time > Time("2026-01-20 20:09:56.999998", scale="tdb")
    assert ps.end_time < Time("2027-01-20 11:33:59.999999", scale="tdb")
    time = Time("2026-02-22 13:00:00", scale="tdb")
    ra = 300
    dec = 10
    velocity = ps.get_spacecraft_velocity(time, observer="EARTH")
    assert velocity.shape == (1, 3)
    position = ps.get_spacecraft_position(time, observer="EARTH")
    assert position.shape == (1, 3)
    lt = ps.get_spacecraft_light_travel_time(time)
    assert lt.shape == (1,)
    assert np.isclose(lt, 500, atol=50)
    ra_result, dec_result = ps.get_velocity_aberrated_positions(time, ra, dec)
    assert ra_result.shape == (1,)
    assert dec_result.shape == (1,)
    ra_result, dec_result = ps.get_differential_velocity_aberrated_positions(
        time, ra, dec, ra0=301, dec0=11
    )
    assert ra_result.shape == (1,)
    assert dec_result.shape == (1,)
    pandoraspacecraft.disable_test_mode()
