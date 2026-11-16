"""Hourly and window-based low-resource detection with explicit UTC intervals."""

import numpy as np
import pandas as pd


def utc_hourly_index(index):
    """Interpret legacy naive ERA5 labels as UTC; reject gaps and duplicates."""
    index = pd.DatetimeIndex(pd.to_datetime(index, utc=True))
    if len(index) == 0 or index.hasnans or not index.is_unique:
        raise ValueError("Expected a nonempty, unique UTC time index.")
    if not ((index[1:] - index[:-1]) == pd.Timedelta(hours=1)).all():
        raise ValueError("Intervals must be strictly increasing and consecutive hours.")
    return index


def capacity_series(series):
    series = series.astype(float).copy()
    series.index = utc_hourly_index(series.index)
    if not np.isfinite(series.to_numpy()).all() or not series.between(0, 1).all():
        raise ValueError("Capacity values must be finite and within [0, 1].")
    return series


def read_series(path, column):
    table = pd.read_csv(path, index_col=0)
    return capacity_series(table[column])


def align_wind_pv(wind_snapshots, pv_hourly):
    """Approximate wind interval means; use PV interval means without smoothing."""
    wind = capacity_series(wind_snapshots)
    pv = capacity_series(pv_hourly)
    if len(wind) < 2:
        raise ValueError("At least two wind snapshots are required.")
    wind = wind.rolling(2, min_periods=2).mean().iloc[1:]
    if not wind.index.equals(pv.index):
        raise ValueError("PV interval ends must exactly match complete wind intervals.")
    return pd.DataFrame({"wind_cf": wind, "pv_cf": pv})


def validate_resources(resources):
    if not utc_hourly_index(resources.index).equals(resources.index):
        raise ValueError("Resources must use an explicit UTC index.")
    for column in ["wind_cf", "pv_cf"]:
        capacity_series(resources[column])


def positive_integer(value):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)) or value < 1:
        raise ValueError("Window and duration lengths must be positive integers.")


def threshold_value(value):
    if not np.isfinite(value) or not 0 <= value <= 1:
        raise ValueError("Thresholds and capacity shares must be within [0, 1].")


def coverage_from_windows(qualifying_endpoints, window_hours):
    """Union all hourly samples contributing to qualifying complete windows."""
    positive_integer(window_hours)
    flags = np.asarray(qualifying_endpoints, dtype=bool)
    if flags.ndim != 1:
        raise ValueError("Window endpoint flags must be one-dimensional.")
    ends = np.flatnonzero(flags)
    if (ends < window_hours - 1).any():
        raise ValueError("A qualifying window cannot have incomplete input context.")
    difference = np.zeros(len(flags) + 1, dtype=np.int64)
    np.add.at(difference, ends - window_hours + 1, 1)
    np.add.at(difference, ends + 1, -1)
    return np.cumsum(difference[:-1]) > 0


def covered_periods(index, covered, qualifying_endpoints, context_hours=1):
    """Merge adjacent covered hours and flag missing boundary-window context.

    For window length W, unknown windows outside the dataset can cover the
    first/last W-1 known hours and connect to an adjacent event. Consequently
    edge-context uncertainty can occur without touching the exact data edge.
    """
    index = utc_hourly_index(index)
    positive_integer(context_hours)
    covered = np.asarray(covered, dtype=bool)
    qualifying = np.asarray(qualifying_endpoints, dtype=bool)
    if covered.shape != (len(index),) or qualifying.shape != covered.shape:
        raise ValueError("Coverage flags must match the time index.")
    boundaries = np.flatnonzero(np.diff(np.r_[False, covered, False]))
    records = []
    for start, stop in boundaries.reshape(-1, 2):
        records.append({
            "start_utc": index[start] - pd.Timedelta(hours=1),
            "end_utc": index[stop - 1],
            "duration_hours": int(stop - start),
            "qualifying_window_count": int(qualifying[start:stop].sum()),
            "touches_data_start": start == 0,
            "touches_data_end": stop == len(index),
            "boundary_context_incomplete": (
                start < context_hours or len(index) - stop < context_hours
            ),
        })
    columns = ["start_utc", "end_utc", "duration_hours", "qualifying_window_count",
               "touches_data_start", "touches_data_end", "boundary_context_incomplete"]
    table = pd.DataFrame.from_records(records, columns=columns)
    for column in ["start_utc", "end_utc"]:
        table[column] = pd.to_datetime(table[column], utc=True)
    for column in ["duration_hours", "qualifying_window_count"]:
        table[column] = table[column].astype(int)
    for column in columns[4:]:
        table[column] = table[column].astype(bool)
    return table


def simultaneous_events(resources, threshold=0.20, minimum_hours=24):
    validate_resources(resources)
    threshold_value(threshold)
    positive_integer(minimum_hours)
    low = (resources.wind_cf < threshold) & (resources.pv_cf < threshold)
    catalogue = covered_periods(resources.index, low, low)
    catalogue["meets_minimum_duration"] = catalogue.duration_hours >= minimum_hours
    return low, catalogue


def combined_window_events(resources, wind_share=0.50, threshold=0.06, window_hours=48):
    """Use full trailing windows; an event is the union of qualifying supports."""
    validate_resources(resources)
    threshold_value(wind_share)
    threshold_value(threshold)
    positive_integer(window_hours)
    combined = wind_share * resources.wind_cf + (1 - wind_share) * resources.pv_cf
    rolling = combined.rolling(window_hours, min_periods=window_hours).mean()
    qualifying = rolling.notna() & (rolling < threshold)
    covered = coverage_from_windows(qualifying, window_hours)
    catalogue = covered_periods(resources.index, covered, qualifying, window_hours)
    diagnostic = pd.DataFrame({
        "combined_cf": combined,
        "rolling_mean_cf": rolling,
        "full_window_available": rolling.notna(),
        "qualifying_window_endpoint": qualifying,
        "covered_by_qualifying_window": covered,
    })
    return diagnostic, catalogue
