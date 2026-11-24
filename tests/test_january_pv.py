"""Whole-plant exclusions prevent partial capacity/energy comparisons."""
from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd
from shapely.geometry import box
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from january_pv import match_pv


class PVMatchingTests(unittest.TestCase):
    def setUp(self):
        self.monthly=pd.DataFrame(dict(plant_id=[10,10,20],generator_id=['A','B','C'],
            plant_name=['First','First','Second'],capacity_mw=[1.,2.,3.],status=['OP']*3,
            latitude=[35.]*3,longitude=[-120.]*3,operating_year=[2015]*3,
            operating_month=[1]*3,fuel=['SUN']*3,prime_mover=['PV']*3))
        self.annual=self.monthly[['plant_id','generator_id','capacity_mw']].copy()
        for name in ['single_axis','dual_axis','east_west','concentrator','other_solar']:
            self.annual[name]=np.nan
        self.annual=self.annual.assign(fixed_tilt='Y',tilt_deg=25.,azimuth_deg=180.,
            dc_capacity_mw=[1.2,2.4,3.6],annual_source_sheet='Operable',annual_source_excel_row=[3,4,5])
        self.energy=pd.DataFrame(dict(plant_id=[10,20,99999],plant_name=['First','Second','Increment'],
            state=['CA']*3,fuel=['SUN']*3,prime_mover=['PV']*3,
            is_state_fuel_increment=[False,False,True],january_net_generation_mwh=[300.,350.,40.]))

    def run_match(self,jan=None,annual=None,energy=None):
        return match_pv(self.monthly,jan if jan is not None else self.monthly,
            annual if annual is not None else self.annual,energy if energy is not None else self.energy,
            box(-125,32,-114,42))

    def test_complete_units_and_synthetic_increment_excluded(self):
        audit,units=self.run_match()
        self.assertEqual(set(audit.plant_id),{10,20})
        self.assertEqual(units.capacity_mw.sum(),6.)

    def test_changed_single_unit_excludes_whole_plant(self):
        jan=self.monthly.copy();jan.loc[0,'capacity_mw']=2.
        _,units=self.run_match(jan=jan)
        self.assertEqual(units.plant_id.tolist(),[20])

    def test_annual_extra_unit_or_capacity_difference_excludes_whole_plant(self):
        changed=self.annual.copy();changed.loc[0,'capacity_mw']=1.1
        extra=pd.concat([self.annual,self.annual.iloc[[0]].assign(generator_id='NEW')])
        for annual in [changed,extra]:
            _,units=self.run_match(annual=annual)
            self.assertEqual(units.plant_id.tolist(),[20])

    def test_mixed_tracker_flag_excludes_whole_plant(self):
        annual=self.annual.copy();annual['single_axis']=annual.single_axis.astype(object)
        annual.loc[0,'single_axis']='Y'
        _,units=self.run_match(annual=annual)
        self.assertEqual(units.plant_id.tolist(),[20])

    def test_missing_orientation_or_energy_is_not_imputed(self):
        annual=self.annual.copy();annual.loc[0,'tilt_deg']=np.nan
        _,units=self.run_match(annual=annual);self.assertEqual(units.plant_id.tolist(),[20])
        energy=self.energy.copy();energy.loc[0,'january_net_generation_mwh']=np.nan
        _,units=self.run_match(energy=energy);self.assertEqual(units.plant_id.tolist(),[20])

    def test_duplicate_keys_fail(self):
        with self.assertRaises(ValueError):
            self.run_match(annual=pd.concat([self.annual,self.annual.iloc[[0]]]))


if __name__=='__main__':
    unittest.main()
