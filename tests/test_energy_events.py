"""Window-support, duration, missing-data and edge-context regression checks."""

import unittest

import numpy as np
import pandas as pd

from scripts.energy_events import (
    align_wind_pv, combined_window_events, coverage_from_windows,
    covered_periods, simultaneous_events,
)


def index(n):
    return pd.date_range("2020-01-01 01:00", periods=n, freq="h", tz="UTC")


def resources(values):
    values = np.asarray(values, dtype=float)
    return pd.DataFrame({"wind_cf": values, "pv_cf": values}, index=index(len(values)))


class AlignmentTests(unittest.TestCase):
    def test_wind_averaged_once_pv_not_averaged_again(self):
        wind = pd.Series([0.0, 0.2, 0.6], index=pd.date_range("2020-01-01", periods=3, freq="h"))
        pv = pd.Series([0.8, 0.1], index=index(2))
        out = align_wind_pv(wind, pv)
        np.testing.assert_allclose(out.wind_cf, [0.1, 0.4])
        np.testing.assert_allclose(out.pv_cf, [0.8, 0.1])
        self.assertTrue(out.index.equals(pv.index))

    def test_missing_gapped_duplicate_and_misaligned_values_rejected(self):
        wind = pd.Series([0.1, 0.2, 0.3], index=pd.date_range("2020-01-01", periods=3, freq="h", tz="UTC"))
        for pv in [pd.Series([np.nan, 0.2], index=index(2)),
                   pd.Series([0.2, 0.2], index=index(2) + pd.Timedelta(hours=1)),
                   pd.Series([0.2, 0.2], index=[index(3)[0], index(3)[2]]),
                   pd.Series([0.2, 0.2], index=[index(2)[0], index(2)[0]]),
                   pd.Series([0.2, 1.1], index=index(2))]:
            with self.assertRaises(ValueError):
                align_wind_pv(wind, pv)


class SimultaneousTests(unittest.TestCase):
    def test_duration_is_hour_count_not_timestamp_difference(self):
        data = resources([0.5] + [0.1] * 24 + [0.5])
        low, events = simultaneous_events(data)
        self.assertEqual(int(low.sum()), 24)
        self.assertEqual(events.duration_hours.tolist(), [24])
        self.assertTrue(events.meets_minimum_duration.item())
        self.assertFalse(events.boundary_context_incomplete.item())
        self.assertEqual(events.end_utc.item() - events.start_utc.item(), pd.Timedelta(hours=24))

    def test_both_technologies_must_be_low_and_equality_is_not_low(self):
        data = resources([0.1, 0.2, 0.1])
        data.loc[data.index[0], "pv_cf"] = 0.5
        low, events = simultaneous_events(data)
        np.testing.assert_array_equal(low, [False, False, True])
        self.assertTrue(events.touches_data_end.item())


class RollingTests(unittest.TestCase):
    def test_high_individual_hour_can_belong_to_low_mean_window(self):
        diagnostic, events = combined_window_events(resources([0.15, 0, 0, 0]), window_hours=4)
        self.assertEqual(int(diagnostic.qualifying_window_endpoint.sum()), 1)
        self.assertEqual(events.duration_hours.tolist(), [4])
        self.assertEqual(events.qualifying_window_count.tolist(), [1])
        self.assertEqual(diagnostic.rolling_mean_cf.isna().sum(), 3)

    def test_overlapping_windows_are_one_union_not_multiple_events(self):
        diagnostic, events = combined_window_events(resources([0.01] * 8), window_hours=4)
        self.assertEqual(int(diagnostic.qualifying_window_endpoint.sum()), 5)
        self.assertEqual(int(diagnostic.covered_by_qualifying_window.sum()), 8)
        self.assertEqual(events.duration_hours.tolist(), [8])
        self.assertTrue(events.touches_data_start.item())
        self.assertTrue(events.touches_data_end.item())

    def test_adjacent_supports_merge_even_if_intermediate_means_do_not_qualify(self):
        endpoints = np.zeros(8, dtype=bool)
        endpoints[[3, 7]] = True
        covered = coverage_from_windows(endpoints, 4)
        events = covered_periods(index(8), covered, endpoints, 4)
        self.assertEqual(events.duration_hours.tolist(), [8])
        self.assertEqual(events.qualifying_window_count.tolist(), [2])

    def test_gaps_between_window_supports_produce_separate_events(self):
        endpoints = np.zeros(14, dtype=bool)
        endpoints[[3, 9]] = True
        covered = coverage_from_windows(endpoints, 4)
        events = covered_periods(index(14), covered, endpoints, 4)
        self.assertEqual(events.duration_hours.tolist(), [4, 4])
        self.assertEqual(int(covered.sum()), 8)

    def test_no_event_equality_and_insufficient_context(self):
        for values, window in [([0.5] * 8, 4), ([0.0] * 3, 4)]:
            diagnostic, events = combined_window_events(resources(values), threshold=0.5, window_hours=window)
            self.assertTrue(events.empty)
            self.assertFalse(diagnostic.qualifying_window_endpoint.any())
        bad = np.zeros(8, dtype=bool)
        bad[1] = True
        with self.assertRaises(ValueError):
            coverage_from_windows(bad, 4)

    def test_missing_outside_windows_can_extend_an_event_not_touching_the_edge(self):
        endpoints = np.zeros(30, dtype=bool)
        endpoints[[5, 12, 27]] = True
        covered = coverage_from_windows(endpoints, 4)
        events = covered_periods(index(30), covered, endpoints, 4)
        self.assertEqual(events.boundary_context_incomplete.tolist(), [True, False, True])
        self.assertFalse(events.touches_data_start.any())
        self.assertFalse(events.touches_data_end.any())

    def test_capacity_mix_extremes_use_the_intended_technology(self):
        data = resources([0.1] * 8)
        data["pv_cf"] = 0.9
        wind_only, _ = combined_window_events(data, wind_share=1, window_hours=4)
        pv_only, _ = combined_window_events(data, wind_share=0, window_hours=4)
        np.testing.assert_allclose(wind_only.combined_cf, 0.1)
        np.testing.assert_allclose(pv_only.combined_cf, 0.9)

    def test_invalid_parameters_are_rejected(self):
        for kwargs in [{"wind_share": 1.1}, {"threshold": np.nan},
                       {"window_hours": 0}, {"window_hours": 1.5}]:
            with self.assertRaises(ValueError):
                combined_window_events(resources([0.1] * 8), **kwargs)


if __name__ == "__main__":
    unittest.main()
