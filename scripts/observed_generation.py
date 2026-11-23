"""January-only observation alignment and dimensionless shape diagnostics."""

import numpy as np
import pandas as pd


def january_starts(dates, hours, intervals):
    """Interpret CAISO market hours 1..24 and intervals 1..12 as Pacific starts.

    This pilot deliberately rejects other months: DST needs separate handling.
    The archive Date's time component is checked separately by the importer.
    """
    dates = pd.DatetimeIndex(pd.to_datetime(dates))
    hour = np.asarray(hours, dtype=float)
    interval = np.asarray(intervals, dtype=float)
    if (dates.tz is not None or dates.isna().any()
            or not ((dates.year == 2020) & (dates.month == 1)).all()
            or len(dates) != len(hour) or len(dates) != len(interval)
            or not np.isfinite(hour).all() or not np.isfinite(interval).all()
            or not ((hour >= 1) & (hour <= 24) & (hour == np.floor(hour))).all()
            or not ((interval >= 1) & (interval <= 12)
                    & (interval == np.floor(interval))).all()):
        raise ValueError("Expected January 2020 dates, hours 1..24 and intervals 1..12.")
    wall = dates.normalize() + pd.to_timedelta((hour - 1) * 60 + (interval - 1) * 5, unit="min")
    return wall.tz_localize("America/Los_Angeles", ambiguous="raise", nonexistent="raise").tz_convert("UTC")


def hourly_production(frame):
    """Energy-conserving mean of exactly twelve complete five-minute MW values."""
    if (not isinstance(frame.index, pd.DatetimeIndex) or str(frame.index.tz) != "UTC"
            or frame.empty or frame.index.has_duplicates or not frame.index.is_monotonic_increasing
            or not np.isfinite(frame.to_numpy(dtype=float)).all()):
        raise ValueError("Production requires finite values and unique ordered UTC starts.")
    expected = pd.date_range(frame.index[0].floor("h"),
                             frame.index[-1].ceil("h"), freq="5min", inclusive="left")
    if not frame.index.equals(expected):
        raise ValueError("Expected complete, consecutive hours of five-minute starts.")
    result = frame.resample("h", closed="left", label="right").mean()
    result.index.name = "interval_end_utc"
    return result


def shape_metrics(modeled, observed):
    """Own-mean scaling removes amplitude; these are not CF accuracy metrics."""
    a, b = np.asarray(modeled, dtype=float), np.asarray(observed, dtype=float)
    if (a.ndim != 1 or a.shape != b.shape or len(a) < 3
            or not np.isfinite(a).all() or not np.isfinite(b).all()
            or a.mean() <= 0 or b.mean() <= 0):
        raise ValueError("Shape diagnostics need paired finite positive-mean series.")
    def correlation(x, y):
        return float(np.corrcoef(x, y)[0, 1]) if x.std() > 0 and y.std() > 0 else None
    return {
        "paired_intervals": len(a),
        "modeled_mean_cf": float(a.mean()), "observed_mean_mw": float(b.mean()),
        "pearson_r": correlation(a, b),
        "first_difference_pearson_r": correlation(np.diff(a), np.diff(b)),
        "own_mean_scaled_rmse": float(np.sqrt(np.mean((a / a.mean() - b / b.mean()) ** 2))),
    }


def complete_local_days(frame):
    """Drop partial Pacific days before calculating daily means."""
    if (str(frame.index.tz) != "UTC" or frame.index.has_duplicates
            or not frame.index.is_monotonic_increasing
            or not np.isfinite(frame.to_numpy(dtype=float)).all()
            or not ((frame.index[1:] - frame.index[:-1]) == pd.Timedelta(hours=1)).all()):
        raise ValueError("Daily diagnostics require consecutive, finite UTC interval means.")
    # A label at midnight belongs to the preceding local day's final hour.
    starts = (frame.index - pd.Timedelta(hours=1)).tz_convert("America/Los_Angeles")
    if not ((starts.year == 2020) & (starts.month == 1)).all():
        raise ValueError("Only January 2020 local days are supported.")
    keys = starts.normalize()
    groups = frame.groupby(keys)
    means = groups.mean()
    return means.loc[groups.size().eq(24)]
