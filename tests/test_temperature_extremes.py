"""Calendar support and no-pilot/no-self-fitting controls for extremes."""
from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from temperature_extremes import complete_utc_days,seasonal_thresholds,sustained_extremes


class TemperatureTests(unittest.TestCase):
    def test_interval_end_midnight_belongs_to_previous_day(self):
        index=pd.date_range('2020-02-28T01:00Z',periods=48,freq='h')
        result=complete_utc_days(pd.Series(np.r_[np.ones(24)*10,np.ones(24)*20],index=index))
        self.assertEqual(result.temperature_c.tolist(),[10.,20.])
        self.assertEqual(result.hours.tolist(),[24,24])
        self.assertEqual(result.index[-1],pd.Timestamp('2020-02-29T00:00Z'))

    def test_incomplete_edges_flagged_and_interior_gap_rejected(self):
        index=pd.date_range('2020-01-01T02:00Z',periods=48,freq='h');s=pd.Series(10.,index=index)
        result=complete_utc_days(s)
        self.assertEqual(result.complete.tolist(),[False,True,False])
        self.assertTrue(result.temperature_c.iloc[[0,2]].isna().all())
        with self.assertRaises(ValueError):complete_utc_days(s.drop(s.index[20]))

    def test_leave_one_year_out_and_leap_interpolation(self):
        index=pd.date_range('2019-01-01','2021-12-31',freq='D',tz='UTC')
        series=pd.Series(np.where(index.year==2020,100.,0.),index=index)
        result=seasonal_thresholds(series,minimum_other_years=2)
        self.assertTrue(result.loc['2020','heat_p95_c'].eq(0).all())
        self.assertTrue(result.loc['2020','heat'].all())
        self.assertEqual(result.loc['2020-02-29','heat_p95_c'],0)

    def test_no_quantiles_from_pilot_or_partial_years(self):
        with self.assertRaises(ValueError):
            seasonal_thresholds(pd.Series(10.,index=pd.date_range('2020-01-01',periods=31,freq='D',tz='UTC')))
        index=pd.date_range('2019-01-02','2021-12-31',freq='D',tz='UTC')
        with self.assertRaises(ValueError):seasonal_thresholds(pd.Series(0.,index=index),minimum_other_years=2)

    def test_sustained_runs_and_boundary_censoring(self):
        index=pd.date_range('2020-01-01',periods=10,freq='D',tz='UTC')
        result=sustained_extremes(pd.Series([True]*3+[False]+[True]*2+[False]+[True]*3,index=index))
        self.assertEqual(result.duration_days.tolist(),[3,3])
        self.assertTrue(result.boundary_censored.all())
        self.assertEqual(result.end_utc.iloc[0],pd.Timestamp('2020-01-04T00:00Z'))


if __name__=='__main__':unittest.main()
