"""Physical and time-alignment checks for the representative PV scenario."""

from dataclasses import replace
import unittest

import numpy as np
import pandas as pd
import xarray as xr

from scripts.pv_model import (
    PVConfig, hourly_utc, model_cell, power_from_poa, prepare_forcing,
)


class PVPhysicsTests(unittest.TestCase):
    def test_darkness_is_zero_and_missing_inputs_are_rejected(self):
        times = pd.date_range("2020-01-15 08:00", periods=2, freq="h", tz="UTC")
        output = model_cell(times, [0, 0], [10, 10], 35, -120, PVConfig())
        np.testing.assert_array_equal(output.pv_ac_capacity_factor, [0, 0])
        with self.assertRaises(ValueError):
            model_cell(times, [np.nan, 0], [10, 10], 35, -120, PVConfig())

    def test_horizontal_panel_preserves_ghi_at_daylight(self):
        times = pd.date_range("2020-01-15 20:00", periods=2, freq="h", tz="UTC")
        output = model_cell(times, [500, 600], [10, 10], 35, -120,
                            replace(PVConfig(), tilt_deg=0))
        np.testing.assert_allclose(output.poa_global_w_m2, [500, 600], rtol=1e-12)

    def test_hotter_cells_and_larger_losses_reduce_unclipped_output(self):
        config = PVConfig()
        cold, _ = power_from_poa([500], [10], config)
        hot, _ = power_from_poa([500], [40], config)
        lossy, _ = power_from_poa([500], [10], replace(config, other_loss_fraction=0.30))
        self.assertLess(hot[0], cold[0])
        self.assertLess(lossy[0], cold[0])

    def test_ac_rating_clips_at_one_and_dc_ratio_is_not_inverter_rating(self):
        high, _ = power_from_poa([3000], [-30], PVConfig())
        self.assertAlmostEqual(high[0], 1.0)
        small, _ = power_from_poa([500], [10], replace(PVConfig(), dc_ac_ratio=0.8))
        large, _ = power_from_poa([500], [10], replace(PVConfig(), dc_ac_ratio=1.2))
        self.assertGreater(large[0], small[0])

    def test_ross_noct_reference_conditions(self):
        _, cell_temperature = power_from_poa([800], [20], PVConfig(noct_c=45))
        self.assertAlmostEqual(cell_temperature[0], 45.0)

    def test_low_sun_hourly_ghi_is_not_silently_deleted(self):
        times = pd.date_range("2020-01-15 08:00", periods=2, freq="h", tz="UTC")
        output = model_cell(times, [1, 1], [10, 10], 35, -120, PVConfig())
        self.assertTrue((output.solar_zenith_deg > 90).all())
        self.assertTrue((output.poa_global_w_m2 > 0).all())

    def test_invalid_parameters_are_rejected(self):
        for kwargs in [{"tilt_deg": 100}, {"dc_ac_ratio": 0},
                       {"other_loss_fraction": 1}, {"noct_c": np.nan}]:
            with self.assertRaises(ValueError):
                PVConfig(**kwargs)


class IntervalTests(unittest.TestCase):
    @staticmethod
    def datasets():
        coords = {"valid_time": pd.date_range("2020-01-01", periods=3, freq="h"),
                  "latitude": [35.0], "longitude": [-120.0]}
        instant = xr.Dataset({"t2m": (("valid_time", "latitude", "longitude"),
                                     np.array([273.15, 293.15, 313.15]).reshape(3, 1, 1))},
                             coords=coords)
        accum = xr.Dataset({"ssrd": (("valid_time", "latitude", "longitude"),
                                   np.array([3600, 7200, 10800]).reshape(3, 1, 1))},
                           coords=coords)
        instant.t2m.attrs["units"] = "K"
        accum.ssrd.attrs["units"] = "J m**-2"
        mask = xr.DataArray([[1]], dims=("latitude", "longitude"),
                            coords={"latitude": [35.0], "longitude": [-120.0]})
        return instant, accum, mask

    def test_preceding_hour_energy_and_bracketing_temperature(self):
        data = prepare_forcing(*self.datasets())
        np.testing.assert_allclose(data["ghi"][:, 0], [2, 3])
        np.testing.assert_allclose(data["temp_air"][:, 0], [10, 30])
        self.assertEqual(data["interval_end"][0], pd.Timestamp("2020-01-01 01:00Z"))

    def test_midpoint_geometry_is_used_but_end_labels_are_preserved(self):
        import pvlib
        times = pd.date_range("2020-01-15 20:00", periods=2, freq="h", tz="UTC")
        out = model_cell(times, [500, 500], [10, 10], 35, -120, PVConfig())
        expected = pvlib.solarposition.get_solarposition(
            times - pd.Timedelta(minutes=30), 35, -120,
            altitude=0, pressure=101325, temperature=np.array([10, 10]),
        )
        np.testing.assert_allclose(out.solar_zenith_deg, expected.zenith)
        self.assertTrue(out.index.equals(times))

    def test_gaps_wrong_units_and_bad_masks_are_rejected(self):
        with self.assertRaises(ValueError):
            hourly_utc(pd.to_datetime(["2020-01-01", "2020-01-01 02:00"], format="mixed"))
        instant, accum, mask = self.datasets()
        accum.ssrd.attrs["units"] = "W m-2"
        with self.assertRaises(ValueError):
            prepare_forcing(instant, accum, mask)
        instant, accum, mask = self.datasets()
        with self.assertRaises(ValueError):
            prepare_forcing(instant, accum, mask * 2)


if __name__ == "__main__":
    unittest.main()
