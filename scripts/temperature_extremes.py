"""Predefined UTC daily-mean extremes; no climatology inferred from the pilot."""
import numpy as np
import pandas as pd


def complete_utc_days(hourly_interval_temperature):
    """Average 24 end-labeled hourly interval means; flag incomplete edge days.

    UTC days avoid 23/25-hour local-day ambiguity. This is the daily mean of
    a statewide area-weighted temperature, not local Tmax/Tmin or demand.
    Missing interior hours fail rather than becoming cold/low-resource hours.
    """
    series=hourly_interval_temperature.astype(float).copy()
    index=pd.DatetimeIndex(series.index)
    if (index.tz is None or len(index)==0 or index.hasnans or index.has_duplicates
            or not np.isfinite(series.to_numpy()).all()):
        raise ValueError('Require finite temperatures at explicit hourly interval ends.')
    index=index.tz_convert('UTC')
    if not ((index==index.floor('h')).all() and
            ((index[1:]-index[:-1])==pd.Timedelta(hours=1)).all()):
        raise ValueError('Require consecutive, whole-hour interval ends.')
    series.index=(index-pd.Timedelta(hours=1)).normalize()
    grouped=series.groupby(level=0)
    result=pd.DataFrame({'temperature_c':grouped.mean(),'hours':grouped.size()})
    result['complete']=result.hours.eq(24)
    result.loc[~result.complete,'temperature_c']=np.nan
    result.index.name='day_utc'
    return result


def seasonal_thresholds(daily_temperature,minimum_other_years=18,half_window_days=15):
    """Leave-one-year-out 5/95% daily-mean quantiles on a circular 365-day year.

    Leap day is excluded from the fitting pool; its thresholds interpolate
    February 28 and March 1. Incomplete baseline years are rejected. Percentile
    estimates use NumPy's linear method. No observed threshold is chosen here.
    """
    series=daily_temperature.astype(float).copy();index=pd.DatetimeIndex(series.index)
    if (not isinstance(minimum_other_years,int) or minimum_other_years<1
            or not isinstance(half_window_days,int) or not 0<=half_window_days<=182
            or index.tz is None or not np.isfinite(series.to_numpy()).all()
            or index.has_duplicates or len(index)==0):
        raise ValueError('Invalid daily baseline or percentile settings.')
    index=index.tz_convert('UTC');series.index=index
    if not index.equals(pd.date_range(index[0],index[-1],freq='D')) or not (index==index.normalize()).all():
        raise ValueError('Daily baseline must be consecutive UTC midnight labels.')
    years=sorted(set(index.year))
    if len(years)<minimum_other_years+1:
        raise ValueError('Insufficient independent baseline years; do not estimate from the pilot.')
    for year in years:
        expected=pd.date_range(f'{year}-01-01',f'{year}-12-31',freq='D',tz='UTC')
        if not index[index.year==year].equals(expected):
            raise ValueError('Baseline requires complete calendar years.')
    # Nonleap reference produces stable month/day positions after February.
    leap=(index.month==2)&(index.day==29)
    phase=np.array([pd.Timestamp(2001,t.month,t.day).dayofyear if not l else 0 for t,l in zip(index,leap)])
    values=series.to_numpy();output=np.empty((len(index),2))
    for year in years:
        other=(index.year!=year)&~leap
        thresholds={}
        for day in range(1,366):
            distance=np.minimum(np.abs(phase-day),365-np.abs(phase-day))
            pool=values[other&(distance<=half_window_days)]
            thresholds[day]=np.quantile(pool,[.05,.95],method='linear')
        for pos in np.flatnonzero(index.year==year):
            output[pos]=(thresholds[59]+thresholds[60])/2 if leap[pos] else thresholds[phase[pos]]
    result=pd.DataFrame(output,index=index,columns=['cold_p05_c','heat_p95_c'])
    result['temperature_c']=values
    result['cold']=values<result.cold_p05_c
    result['heat']=values>result.heat_p95_c
    return result


def sustained_extremes(flags,minimum_days=3):
    """Return full-day support of runs; edge runs are explicitly censored."""
    if (not isinstance(minimum_days,int) or minimum_days<1
            or flags.dtype!=bool or flags.empty):
        raise ValueError('Require nonempty boolean daily flags and positive duration.')
    index=pd.DatetimeIndex(flags.index)
    if (index.tz is None or str(index.tz)!='UTC' or index.hasnans
            or not (index==index.normalize()).all()
            or not index.equals(pd.date_range(index[0],index[-1],freq='D'))):
        raise ValueError('Require consecutive UTC midnight daily labels.')
    values=flags.to_numpy();edges=np.flatnonzero(np.diff(np.r_[False,values,False]))
    rows=[]
    for start,stop in edges.reshape(-1,2):
        if stop-start>=minimum_days:
            rows.append(dict(start_utc=index[start],end_utc=index[stop-1]+pd.Timedelta(days=1),
                duration_days=int(stop-start),boundary_censored=bool(start==0 or stop==len(index))))
    return pd.DataFrame(rows,columns=['start_utc','end_utc','duration_days','boundary_censored'])
