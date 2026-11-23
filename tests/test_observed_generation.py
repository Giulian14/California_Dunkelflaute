"""Scientific checks for observation time support, conservation and scaling."""

from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from observed_generation import complete_local_days, hourly_production, january_starts, shape_metrics


class ObservationTimingTests(unittest.TestCase):
    def test_market_hour_and_interval_are_starts_in_pacific(self):
        result = january_starts(["2020-01-01", "2020-01-31"], [1, 24], [1, 12])
        expected = pd.to_datetime(["2020-01-01T08:00Z", "2020-02-01T07:55Z"])
        self.assertTrue(result.equals(expected))

    def test_other_months_fractional_or_invalid_market_fields_rejected(self):
        for date, hour, interval in [("2020-03-08", 1, 1), ("2020-01-01", 0, 1),
                                     ("2020-01-01", 24, 13), ("2020-01-01", 1.5, 1)]:
            with self.assertRaises(ValueError):
                january_starts([date], [hour], [interval])

    def test_hour_end_labels_and_energy_conservation(self):
        index = pd.date_range("2020-01-01T08:00Z", periods=24, freq="5min")
        source = pd.DataFrame({"mw": np.arange(24.)}, index=index)
        hourly = hourly_production(source)
        self.assertTrue(hourly.index.equals(pd.date_range("2020-01-01T09:00Z", periods=2, freq="h")))
        np.testing.assert_allclose(hourly.mw, [5.5, 17.5])
        self.assertAlmostEqual(hourly.mw.sum(), source.mw.sum() / 12)

    def test_missing_duplicate_nonfinite_and_partial_hours_rejected(self):
        index = pd.date_range("2020-01-01T08:00Z", periods=12, freq="5min")
        data = pd.DataFrame({"mw": np.ones(12)}, index=index)
        bads = [data.iloc[1:], data.drop(index[4]), pd.concat([data, data.iloc[-1:]])]
        missing = data.copy(); missing.iloc[2, 0] = np.nan
        bads.append(missing)
        for bad in bads:
            with self.assertRaises(ValueError):
                hourly_production(bad)

    def test_midnight_end_belongs_to_previous_day_and_partial_days_dropped(self):
        index = pd.date_range("2020-01-01T09:00Z", periods=27, freq="h")
        daily = complete_local_days(pd.DataFrame({"mw": np.arange(27.)}, index=index))
        self.assertEqual(len(daily), 1)
        self.assertEqual(daily.index[0], pd.Timestamp("2020-01-01", tz="America/Los_Angeles"))
        self.assertAlmostEqual(daily.mw.iloc[0], 11.5)

    def test_missing_hour_rejected_before_daily_aggregation(self):
        index = pd.date_range("2020-01-01T09:00Z", periods=25, freq="h")
        data = pd.DataFrame({"mw": np.ones(25)}, index=index).drop(index[3])
        with self.assertRaises(ValueError):
            complete_local_days(data)


class ShapeTests(unittest.TestCase):
    def test_multiplicative_scale_not_treated_as_shape_error(self):
        modeled = np.array([.1, .3, .2, .05])
        result = shape_metrics(modeled, modeled * 6000)
        self.assertAlmostEqual(result["pearson_r"], 1)
        self.assertAlmostEqual(result["own_mean_scaled_rmse"], 0)
        self.assertAlmostEqual(result["observed_mean_mw"], modeled.mean() * 6000)

    def test_constant_series_has_undefined_correlation_not_invented_skill(self):
        result = shape_metrics(np.ones(5), np.ones(5) * 2)
        self.assertIsNone(result["pearson_r"])
        self.assertIsNone(result["first_difference_pearson_r"])

    def test_missing_mismatched_and_nonpositive_mean_rejected(self):
        for a, b in [([1, 2, 3], [1, 2]), ([0, 0, 0], [1, 2, 3]),
                     ([1, 2, np.nan], [1, 2, 3])]:
            with self.assertRaises(ValueError):
                shape_metrics(a, b)


if __name__ == "__main__":
    unittest.main()
