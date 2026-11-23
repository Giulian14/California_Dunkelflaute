from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd
import xarray as xr

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from wind_sites import distance_km, sample_wind, turbine_capacity_audit


class SiteTests(unittest.TestCase):
    def field(self, descending=False):
        lat = np.array([34., 36.]);lon = np.array([-122., -120.])
        y, x = np.meshgrid(lat, lon, indexing="ij")
        ds = xr.Dataset({"u100": (("valid_time", "latitude", "longitude"), (y+x+90)[None]),
                         "v100": (("valid_time", "latitude", "longitude"), np.zeros((1,2,2)))},
                         coords={"valid_time": [0], "latitude": lat, "longitude": lon})
        return ds.sortby("latitude", ascending=False) if descending else ds

    def test_bilinear_linear_field_and_axis_order(self):
        plants = pd.DataFrame({"latitude": [35.], "longitude": [-121.]})
        for descending in [False, True]:
            speed, _, _ = sample_wind(self.field(descending), plants, "bilinear")
            self.assertAlmostEqual(speed[0,0], 4.)

    def test_vector_interpolation_precedes_speed(self):
        ds = self.field();ds.u100.values[:] = [[[-1., 1.], [-1., 1.]]]
        speed, _, _ = sample_wind(ds, pd.DataFrame({"latitude": [35.], "longitude": [-121.]}), "bilinear")
        self.assertAlmostEqual(speed[0,0], 0.)

    def test_nearest_tie_follows_file_order(self):
        plants = pd.DataFrame({"latitude": [35.], "longitude": [-121.]})
        _, iy, ix = sample_wind(self.field(True), plants, "nearest")
        self.assertEqual((iy[0], ix[0]), (0,0))

    def test_outside_points_and_nonfinite_fields_rejected(self):
        with self.assertRaises(ValueError):
            sample_wind(self.field(), pd.DataFrame({"latitude": [30.], "longitude": [-121.]}), "bilinear")
        ds = self.field();ds.u100.values[0,0,0] = np.nan
        with self.assertRaises(ValueError):
            sample_wind(ds, pd.DataFrame({"latitude": [35.], "longitude": [-121.]}), "nearest")

    def test_distance_same_point_and_one_degree(self):
        self.assertEqual(float(distance_km(35,-120,35,-120)), 0.)
        self.assertAlmostEqual(float(distance_km(0,0,0,1)), 111.1950802, places=5)


class CapacityTests(unittest.TestCase):
    def sources(self):
        return (pd.DataFrame({"plant_id": [1,1,2], "generator_id": ["A","B","C"], "capacity_mw": [10.,20.,30.]}),
                pd.DataFrame({"plant_id": [1,1,2], "generator_id": ["A","B","C"], "annual_capacity_mw": [10.,25.,30.]}))

    def test_one_unit_mismatch_excludes_whole_plant(self):
        audit = turbine_capacity_audit(*self.sources())
        self.assertEqual(audit.annual_capacity_consistent.tolist(), [True,False,True])
        self.assertEqual(audit.whole_plant_capacity_consistent.tolist(), [False,False,True])

    def test_missing_and_duplicate_records_rejected_or_flagged(self):
        gen, annual = self.sources()
        audit = turbine_capacity_audit(gen, annual.iloc[1:])
        self.assertFalse(audit.whole_plant_capacity_consistent.iloc[0])
        with self.assertRaises(ValueError):
            turbine_capacity_audit(gen, pd.concat([annual, annual.iloc[:1]]))


if __name__ == "__main__":
    unittest.main()
