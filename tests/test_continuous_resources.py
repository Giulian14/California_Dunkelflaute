"""Checks that arbitrary file boundaries do not become physical/event boundaries."""

from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd
import xarray as xr

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from continuous_resources import interval_weather_pairs, join_resource_chunks
from energy_events import combined_window_events, simultaneous_events
from pv_model import prepare_forcing


def weather(start='2019-12-31T22:00', periods=5):
    time=pd.date_range(start,periods=periods,freq='h')
    coords={'valid_time':time,'latitude':[35.,34.],'longitude':[-120.,-119.]}
    shape=(periods,2,2);dims=('valid_time','latitude','longitude')
    instant=xr.Dataset({'u100':(dims,np.full(shape,6.,dtype=np.float32)),
        'v100':(dims,np.zeros(shape,dtype=np.float32)),
        't2m':(dims,np.broadcast_to((273.15+np.arange(periods))[:,None,None],shape).copy())},coords=coords)
    for name in ['u100','v100']:instant[name].attrs={'units':'m s**-1','GRIB_uvRelativeToGrid':0}
    instant.t2m.attrs['units']='K'
    accum=xr.Dataset({'ssrd':(dims,np.broadcast_to((np.arange(periods)+1.)[:,None,None]*3600,shape).copy())},coords=coords)
    accum.ssrd.attrs['units']='J m**-2'
    mask=xr.DataArray(np.ones((2,2),dtype=bool),dims=('latitude','longitude'),coords={key:coords[key] for key in ['latitude','longitude']})
    return instant,accum,mask


def resources(start='2019-12-28T01:00Z',periods=216):
    values=np.full(periods,.5);values[72:144]=.01
    return pd.DataFrame({'wind_cf':values,'pv_cf':values},index=pd.date_range(start,periods=periods,freq='h'))


class WeatherContinuityTests(unittest.TestCase):
    def test_first_single_snapshot_and_boundary_brackets_are_preserved(self):
        instant,accum,mask=weather();cuts=[0,1,3,5]
        pairs=[(instant.isel(valid_time=slice(a,b)),accum.isel(valid_time=slice(a,b))) for a,b in zip(cuts,cuts[1:])]
        forcings=[prepare_forcing(i,a,mask) for i,a in interval_weather_pairs(pairs,mask)]
        self.assertEqual(sum(len(f['interval_end']) for f in forcings),4)
        ends=forcings[0]['interval_end'].append(forcings[1]['interval_end'])
        expected=pd.date_range('2019-12-31T23:00Z',periods=4,freq='h')
        self.assertTrue(ends.equals(expected))
        np.testing.assert_allclose(np.concatenate([f['temp_air'] for f in forcings])[:,0],[.5,1.5,2.5,3.5],atol=1e-12)
        np.testing.assert_allclose(np.concatenate([f['ghi'] for f in forcings])[:,0],[2,3,4,5])

    def test_duplicate_and_missing_weather_boundary_rejected(self):
        instant,accum,mask=weather()
        for second in [slice(2,5),slice(4,5)]:
            pairs=[(instant.isel(valid_time=slice(0,3)),accum.isel(valid_time=slice(0,3))),
                   (instant.isel(valid_time=second),accum.isel(valid_time=second))]
            with self.assertRaises(ValueError):list(interval_weather_pairs(pairs,mask))

    def test_instant_and_accum_time_disagreement_rejected(self):
        instant,accum,mask=weather();accum=accum.assign_coords(valid_time=accum.valid_time+np.timedelta64(1,'h'))
        with self.assertRaises(ValueError):list(interval_weather_pairs([(instant,accum)],mask))

    def test_grid_or_unit_change_rejected(self):
        instant,accum,mask=weather();first=(instant.isel(valid_time=slice(0,3)),accum.isel(valid_time=slice(0,3)))
        later=instant.isel(valid_time=slice(3,5)).copy(deep=True);later.u100.attrs['units']='knots'
        with self.assertRaises(ValueError):list(interval_weather_pairs([first,(later,accum.isel(valid_time=slice(3,5)))],mask))
        bad=instant.assign_coords(latitude=[35.1,34.1])
        with self.assertRaises(ValueError):list(interval_weather_pairs([(bad,accum)],mask))
        later=instant.isel(valid_time=slice(3,5)).copy(deep=True);later['u100']=later.u100.astype(np.float64)
        with self.assertRaises(ValueError):list(interval_weather_pairs([first,(later,accum.isel(valid_time=slice(3,5)))],mask))

    def test_insufficient_global_bracket_rejected(self):
        instant,accum,mask=weather(periods=1)
        with self.assertRaises(ValueError):list(interval_weather_pairs([(instant,accum)],mask))
        with self.assertRaises(ValueError):list(interval_weather_pairs([],mask))

    def test_leap_day_survives_hourly_file_splits(self):
        instant,accum,mask=weather('2020-02-28T23:00',27)
        chunks=[(instant.isel(valid_time=slice(n,n+1)),accum.isel(valid_time=slice(n,n+1))) for n in range(27)]
        ends=[]
        for i,a in interval_weather_pairs(chunks,mask):ends.extend(prepare_forcing(i,a,mask)['interval_end'])
        ends=pd.DatetimeIndex(ends)
        self.assertEqual(sum(ends.strftime('%Y-%m-%d')=='2020-02-29'),24)
        self.assertEqual(len(ends),26)


class ResourceContinuityTests(unittest.TestCase):
    def test_event_spans_year_boundary_without_reset(self):
        whole=resources();joined=join_resource_chunks([whole.iloc[:95],whole.iloc[95:]])
        pd.testing.assert_frame_equal(joined,whole)
        _,reference=simultaneous_events(joined);diagnostic,combined=combined_window_events(joined)
        self.assertEqual(reference.duration_hours.tolist(),[72])
        self.assertEqual(combined.duration_hours.tolist(),[80])
        self.assertEqual(int(diagnostic.qualifying_window_endpoint.sum()),33)
        self.assertFalse(combined.boundary_context_incomplete.any())

    def test_calendar_leap_and_nonleap_events_have_same_duration(self):
        for start in ['2020-02-26T01:00Z','2019-02-25T01:00Z']:
            whole=resources(start);joined=join_resource_chunks([whole.iloc[:95],whole.iloc[95:]])
            _,periods=simultaneous_events(joined);_,events=combined_window_events(joined)
            self.assertEqual(periods.duration_hours.tolist(),[72]);self.assertEqual(events.duration_hours.tolist(),[80])

    def test_naive_monthly_rolling_loses_known_event_support(self):
        whole=resources();chunks=[whole.iloc[:95],whole.iloc[95:]]
        _,correct=combined_window_events(join_resource_chunks(chunks))
        naive=sum(int(combined_window_events(chunk)[1].duration_hours.sum()) for chunk in chunks)
        self.assertEqual(int(correct.duration_hours.sum()),80)
        self.assertEqual(naive,53)

    def test_resource_gaps_overlaps_missing_and_schema_changes_rejected(self):
        whole=resources();first=whole.iloc[:95]
        invalid=[whole.iloc[96:],whole.iloc[94:],whole.iloc[95:].assign(extra=1.)]
        missing=whole.iloc[95:].copy();missing.iloc[0,0]=np.nan;invalid.append(missing)
        for second in invalid:
            with self.assertRaises(ValueError):join_resource_chunks([first,second])
        with self.assertRaises(ValueError):join_resource_chunks([])

    def test_dst_aware_labels_convert_to_unique_consecutive_utc(self):
        for start,periods in [('2020-11-01T00:00',6),('2020-03-08T00:00',5)]:
            local=pd.date_range(start,periods=periods,freq='h',tz='America/Los_Angeles')
            frame=pd.DataFrame({'wind_cf':.1,'pv_cf':.2},index=local)
            joined=join_resource_chunks([frame.iloc[:2],frame.iloc[2:]])
            self.assertTrue(joined.index.equals(local.tz_convert('UTC')))

    def test_naive_local_resource_labels_rejected(self):
        frame=resources();frame.index=frame.index.tz_localize(None)
        with self.assertRaises(ValueError):join_resource_chunks([frame])

    def test_numeric_csv_values_are_returned_as_numeric_resources(self):
        frame=resources().astype(str)
        joined=join_resource_chunks([frame.iloc[:95],frame.iloc[95:]])
        diagnostic,_=combined_window_events(joined)
        self.assertEqual(int(diagnostic.qualifying_window_endpoint.sum()),33)
        self.assertTrue(all(np.issubdtype(dtype,np.floating) for dtype in joined.dtypes))


if __name__=='__main__':unittest.main()
