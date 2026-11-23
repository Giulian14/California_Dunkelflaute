"""Checks for published curves, inventory filtering and nameplate weights."""

import json
from pathlib import Path
import unittest

import numpy as np
import pandas as pd
from shapely.geometry import box

from scripts.wind_model import (
    capacity_grid_weights, cubic_capacity_factor,
    published_capacity_factor, select_eia_inventory,
)


class CurveTests(unittest.TestCase):
    def test_original_cubic_operating_bounds(self):
        result = cubic_capacity_factor(np.array([0, 3, 12, 24.9, 25]))
        np.testing.assert_allclose(result, [0, 0, 1, 1, 0])

    def test_published_knots_interpolation_and_cutout(self):
        curve = pd.DataFrame({"Wind Speed [m/s]": [0, 3, 5, 10], "Power [-]": [0, .1, .5, 1]})
        values = published_capacity_factor([2.9, 3, 4, 10, 10.01], curve, 3, 10)
        np.testing.assert_allclose(values, [0, .1, .3, 1, 0])

    def test_actual_iec_three_shutdown_does_not_ramp_to_23(self):
        directory = Path(__file__).resolve().parent.parent / "data/reference/wind_curves"
        metadata = json.loads((directory / "manifest.json").read_text())
        spec = metadata["curves"]["wtk_iec3"]
        curve = pd.read_csv(directory / spec["csv"])
        out = published_capacity_factor([22, 22.1, 23, 26], curve,
                                       spec["cut_in_wind_speed"], spec["cut_out_wind_speed"])
        np.testing.assert_allclose(out, [1, 0, 0, 0])

    def test_missing_wind_and_malformed_curves_rejected(self):
        curve = pd.DataFrame({"Wind Speed [m/s]": [0, 3, 10], "Power [-]": [0, .1, 1]})
        with self.assertRaises(ValueError):
            published_capacity_factor([np.nan], curve, 3, 10)
        with self.assertRaises(ValueError):
            published_capacity_factor([5], curve.iloc[::-1], 3, 10)
        with self.assertRaises(ValueError):
            cubic_capacity_factor([-1])


class WeightTests(unittest.TestCase):
    def setUp(self):
        self.plants = pd.DataFrame({"plant_id": [1, 2], "latitude": [40., 30.],
                                    "longitude": [-120., -110.], "capacity_mw": [1., 3.]})

    def test_weights_are_mw_shares_not_area_weights(self):
        weight, _ = capacity_grid_weights(self.plants, [40., 30.], [-120., -110.], np.ones((2, 2)))
        np.testing.assert_allclose(weight, [[.25, 0], [0, .75]])
        self.assertAlmostEqual(weight.sum(), 1)

    def test_capacity_at_shared_grid_cell_is_added(self):
        self.plants.loc[1, ["latitude", "longitude"]] = [40., -120.]
        weight, _ = capacity_grid_weights(self.plants, [40., 30.], [-120., -110.], np.ones((2, 2)))
        np.testing.assert_allclose(weight, [[1, 0], [0, 0]])

    def test_nearest_center_outside_admin_mask_is_recorded_not_removed(self):
        weight, assigned = capacity_grid_weights(self.plants, [40., 30.], [-120., -110.], [[1, 0], [0, 0]])
        self.assertEqual(assigned.nearest_center_inside_admin_mask.tolist(), [True, False])
        self.assertAlmostEqual(weight[1, 1], .75)

    def test_ties_follow_coordinate_file_order(self):
        self.plants.loc[:, "latitude"] = 35.
        _, assigned = capacity_grid_weights(self.plants, [40., 30.], [-120., -110.], np.ones((2, 2)))
        self.assertEqual(assigned.grid_latitude.tolist(), [40., 40.])

    def test_outside_locations_and_duplicate_ids_rejected(self):
        self.plants.loc[0, "latitude"] = 41.
        with self.assertRaises(ValueError):
            capacity_grid_weights(self.plants, [40., 30.], [-120., -110.], np.ones((2, 2)))
        self.plants.loc[0, "latitude"] = 40.
        self.plants.loc[1, "plant_id"] = 1
        with self.assertRaises(ValueError):
            capacity_grid_weights(self.plants, [40., 30.], [-120., -110.], np.ones((2, 2)))


class InventoryTests(unittest.TestCase):
    @staticmethod
    def frames():
        wind = pd.DataFrame({
            "Plant Code": [1, 1, 2, 3, 4], "Generator ID": ["a", "b", "c", "d", "e"],
            "Plant Name": ["A", "A", "B", "C", "D"], "State": ["CA"] * 4 + ["NV"],
            "Technology": ["Onshore Wind Turbine"] * 5,
            "Status": ["OP", "OP", "OS", "OP", "OP"],
            "Nameplate Capacity (MW)": [10., 5., 20., 5., 30.],
            "Turbine Hub Height (Feet)": [200.] * 5,
            "Operating Year": [2010] * 5, "Operating Month": [1] * 5,
            "Number of Turbines": [1] * 5,
        })
        plants = pd.DataFrame({"Plant Code": [1, 2, 3, 4], "Latitude": [35., 35., np.nan, 39.],
                               "Longitude": [-120., -120., -120., -116.]})
        return wind, plants

    def test_selection_aggregation_and_exclusions_are_explicit(self):
        wind, plants = self.frames()
        kept, aggregate, excluded, qa = select_eia_inventory(wind, plants, box(-125, 32, -114, 42))
        self.assertEqual(len(kept), 2)
        self.assertEqual(len(aggregate), 1)
        self.assertAlmostEqual(aggregate.capacity_mw.item(), 15.)
        self.assertEqual(len(excluded), 2)
        self.assertEqual(qa["exclusion_counts"], {"not_operating_status_OP": 1,
                                                 "outside_grid_or_invalid_coordinates": 1})
        self.assertAlmostEqual(qa["candidate_capacity_mw"], 40.)
        self.assertAlmostEqual(qa["retained_capacity_mw"] + qa["excluded_capacity_mw"], 40.)
        np.testing.assert_allclose(kept.reported_hub_height_m, 60.96)

    def test_duplicate_generators_rejected(self):
        wind, plants = self.frames()
        wind.loc[1, "Generator ID"] = "a"
        with self.assertRaises(ValueError):
            select_eia_inventory(wind, plants, box(-125, 32, -114, 42))


if __name__ == "__main__":
    unittest.main()
