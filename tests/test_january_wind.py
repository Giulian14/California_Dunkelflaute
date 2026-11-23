"""Checks for whole-plant matching and bounds without fabricated observations."""

from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd
from shapely.geometry import box

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from january_wind import eia930_january, match_january_plants, monthly_bounds, monthly_wind


def inventory():
    return pd.DataFrame({"plant_id": [10, 10, 20], "generator_id": ["A", "B", "C"],
        "plant_name": ["First", "First", "Second"], "capacity_mw": [30., 20., 40.],
        "status": ["OP"]*3, "operating_year": [2012]*3, "operating_month": [6]*3,
        "fuel": ["WND"]*3, "prime_mover": ["WT"]*3,
        "latitude": [35., 35., 36.], "longitude": [-120., -120., -121.]})


def generation():
    return pd.DataFrame({"plant_id": [10, 20], "plant_name": ["First", "Second"],
        "state": ["CA"]*2, "fuel": ["WND"]*2, "prime_mover": ["WT"]*2,
        "respondent_frequency": ["A", "M"], "january_net_generation_mwh": [7440., 7440.]})


class CohortTests(unittest.TestCase):
    def compare(self, dec=None, jan=None, energy=None):
        return match_january_plants(dec if dec is not None else inventory(),
            jan if jan is not None else inventory(), energy if energy is not None else generation(),
            box(-125, 32, -114, 42))

    def test_whole_plant_nominal_capacity_denominator(self):
        _, _, cohort, generators = self.compare()
        self.assertEqual(len(generators), 3)
        row = cohort.set_index("plant_id").loc[10]
        self.assertEqual(row.capacity_mw, 50)
        self.assertAlmostEqual(row.observed_monthly_cf_nominal, .2)

    def test_one_changed_or_removed_unit_excludes_entire_plant(self):
        changed = inventory(); changed.loc[0, "capacity_mw"] = 35
        for jan in [changed, inventory().iloc[1:]]:
            _, audit, cohort, _ = self.compare(jan=jan)
            self.assertEqual(cohort.plant_id.tolist(), [20])
            self.assertEqual(audit.set_index("plant_id").loc[10, "exclusion_reason"], "wind_records_changed_between_snapshots")
            self.assertAlmostEqual(cohort.january_net_generation_mwh.sum(), 7440.)

    def test_nonoperating_unit_excludes_plant_even_if_unchanged(self):
        frame = inventory(); frame.loc[0, "status"] = "OA"
        _, audit, cohort, _ = self.compare(frame, frame)
        self.assertEqual(cohort.plant_id.tolist(), [20])
        self.assertEqual(audit.set_index("plant_id").loc[10, "exclusion_reason"], "not_all_wind_units_OP_in_both_snapshots")

    def test_missing_generation_is_excluded_not_zero_filled(self):
        energy = generation(); energy.loc[0, "january_net_generation_mwh"] = np.nan
        for frame in [energy, generation().iloc[1:]]:
            _, audit, cohort, _ = self.compare(energy=frame)
            self.assertEqual(cohort.plant_id.tolist(), [20])
            self.assertTrue(pd.isna(audit.set_index("plant_id").loc[10, "january_net_generation_mwh"]))

    def test_duplicate_generation_or_generator_keys_rejected(self):
        with self.assertRaises(ValueError):
            self.compare(energy=pd.concat([generation(), generation().iloc[:1]]))
        with self.assertRaises(ValueError):
            self.compare(jan=pd.concat([inventory(), inventory().iloc[:1]]))

    def test_new_plant_or_missing_geography_not_silently_matched(self):
        _, _, cohort, _ = self.compare(dec=inventory().iloc[2:])
        self.assertEqual(cohort.plant_id.tolist(), [20])
        frame = inventory(); frame.loc[:1, "latitude"] = 0
        _, audit, cohort, _ = self.compare(frame, frame)
        self.assertEqual(cohort.plant_id.tolist(), [20])
        self.assertEqual(audit.set_index("plant_id").loc[10, "exclusion_reason"], "invalid_or_out_of_domain_coordinates")

    def test_excess_generation_is_flagged_not_selected_away(self):
        energy = generation(); energy.loc[0, "january_net_generation_mwh"] = 50 * 744 * 1.1
        _, _, cohort, _ = self.compare(energy=energy)
        self.assertEqual(len(cohort), 2)
        self.assertTrue(cohort.set_index("plant_id").loc[10, "observed_cf_outside_0_1"])


class BoundsTests(unittest.TestCase):
    def setUp(self):
        self.ends = pd.date_range("2020-01-01T09:00Z", "2020-02-01T08:00Z", freq="h")

    def test_missing_nine_hours_bound_all_possible_values(self):
        bounds = monthly_bounds(np.full(735, .1), self.ends[:735], 100.)
        self.assertEqual(bounds["missing_hours"], 9)
        self.assertAlmostEqual(bounds["monthly_cf_lower_bound"], 73.5/744)
        self.assertAlmostEqual(bounds["monthly_cf_upper_bound"], 82.5/744)
        self.assertAlmostEqual(bounds["monthly_energy_upper_bound_mwh"], 8250.)
        for unknown in [0, .2, 1]:
            truth = (73.5 + 9*unknown)/744
            self.assertLessEqual(bounds["monthly_cf_lower_bound"]-1e-14, truth)
            self.assertGreaterEqual(bounds["monthly_cf_upper_bound"]+1e-14, truth)

    def test_complete_month_bounds_collapse_to_mean(self):
        bounds = monthly_bounds(np.full(744, .25), self.ends, 80)
        self.assertEqual(bounds["missing_hours"], 0)
        self.assertEqual(bounds["monthly_cf_lower_bound"], .25)
        self.assertEqual(bounds["monthly_cf_upper_bound"], .25)

    def test_wrong_support_duplicate_bad_cf_or_capacity_rejected(self):
        bads = [(np.ones(3), self.ends[:2], 100),
                (np.ones(3), self.ends[:3].tz_localize(None), 100),
                (np.ones(3), pd.DatetimeIndex([self.ends[0]]*3), 100),
                (np.full(3, np.nan), self.ends[:3], 100),
                (np.full(3, 1.1), self.ends[:3], 100), (np.ones(3), self.ends[:3], 0)]
        for values, index, capacity in bads:
            with self.assertRaises(ValueError):
                monthly_bounds(values, index, capacity)


class NormalizeTests(unittest.TestCase):
    def test_normalize_status_keys_and_source_rows(self):
        frame = pd.DataFrame({"Plant State": ["CA"], "Technology": ["Onshore Wind Turbine"],
            "Plant ID": [10.], "Generator ID": [1.], "Plant Name": ["First"],
            "Nameplate Capacity (MW)": [20], "Status": ["(OP) Operating"],
            "Latitude": [35], "Longitude": [-120], "Operating Month": [1], "Operating Year": [2010],
            "Balancing Authority Code": ["CISO"], "Energy Source Code": ["WND"], "Prime Mover Code": ["WT"]})
        row = monthly_wind(frame).iloc[0]
        self.assertEqual(row.generator_id, "1")
        self.assertEqual(row.status, "OP")
        self.assertEqual(row.source_excel_row, 3)
        with self.assertRaises(ValueError):
            monthly_wind(pd.concat([frame, frame], ignore_index=True))


class EIA930Tests(unittest.TestCase):
    def response(self):
        rows = [{"period": stamp.strftime("%Y-%m-%dT%H"), "fueltype": fuel,
                 "respondent": "CISO", "value-units": "megawatthours", "value": str(value)}
                for stamp in pd.date_range("2020-01-01T09:00Z", "2020-02-01T08:00Z", freq="h")
                for fuel, value in [("WND", 100), ("SUN", -1)]]
        return {"response": {"frequency": "hourly", "total": "1488", "data": rows}}

    def test_complete_pair_preserves_negative_net_energy(self):
        result = eia930_january(self.response())
        self.assertEqual(len(result), 744)
        self.assertTrue(result.eia930_solar_mwh.eq(-1).all())

    def test_missing_duplicate_and_wrong_population_rejected(self):
        for fault in ["missing", "duplicate", "respondent", "units"]:
            response = self.response();rows = response["response"]["data"]
            if fault == "missing":rows.pop()
            elif fault == "duplicate":rows[-1] = rows[0].copy()
            elif fault == "respondent":rows[0]["respondent"] = "ERCO"
            else:rows[0]["value-units"] = "megawatts"
            with self.assertRaises(ValueError):
                eia930_january(response)

    def test_wrong_month_support_rejected(self):
        response = self.response();response["response"]["data"][0]["period"] = "2020-01-01T08"
        with self.assertRaises(ValueError):
            eia930_january(response)


if __name__ == "__main__":
    unittest.main()
