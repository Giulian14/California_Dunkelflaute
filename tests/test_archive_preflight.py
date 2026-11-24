"""Calendar/request identity and input rejection before any large download."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np
import pandas as pd
import xarray as xr
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from archive_preflight import acquisition_plan,audit_weather,verified_receipt


class ArchiveTests(unittest.TestCase):
    def dataset(self):
        coords=dict(valid_time=pd.date_range('2020-01-01',periods=2,freq='h'),
            latitude=np.arange(42,31.99,-.25),longitude=np.arange(-125,-113.99,.25),
            expver=('valid_time',['0001','0001']))
        d=xr.Dataset({n:(('valid_time','latitude','longitude'),np.full((2,41,45),v))
            for n,v in [('u100',1.),('v100',1.),('t2m',280.),('ssrd',0.)]},coords=coords)
        for n in ['u100','v100']:d[n].attrs=dict(units='m s**-1',GRIB_stepType='instant',GRIB_uvRelativeToGrid=0)
        d.t2m.attrs=dict(units='K',GRIB_stepType='instant');d.ssrd.attrs=dict(units='J m**-2',GRIB_stepType='accum')
        return d

    def check(self,d):return audit_weather(d[['u100','v100','t2m']],d[['ssrd']],'2020-01-01T00:00Z','2020-01-01T01:00Z')

    def test_exact_calendar_core_and_context(self):
        p=acquisition_plan();self.assertEqual(len(p['batches']),242)
        self.assertEqual(sum(b['expected_snapshot_hours'] for b in p['batches'] if b['role']=='core'),175320)
        feb=[b for b in p['batches'] if b['batch_id']=='2020-02'][0]
        self.assertEqual(len(feb['request']['day']),29)
        self.assertEqual(p['batches'][-1]['batch_id'],'2025-01')

    def test_correct_pilot_and_missing_or_sentinel_rejection(self):
        self.assertEqual(self.check(self.dataset())['status'],'PASS')
        for value in [np.nan,3.4e38]:
            d=self.dataset();d.u100.values[0,0,0]=value
            with self.assertRaises(ValueError):self.check(d)

    def test_version_rotation_accumulation_and_grid_rejection(self):
        for change in ['version','rotation','accumulation','grid']:
            d=self.dataset()
            if change=='version':d=d.assign_coords(expver=('valid_time',['0005','0005']))
            if change=='rotation':d.u100.attrs['GRIB_uvRelativeToGrid']=1
            if change=='accumulation':d.ssrd.attrs['GRIB_stepType']='instant'
            if change=='grid':d=d.isel(latitude=slice(None,None,-1))
            with self.assertRaises(ValueError):self.check(d)

    def test_receipt_detects_partial_tampering_and_request_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'download.zip';receipt=Path(tmp)/'receipt.json';request={'year':['2020']}
            path.write_bytes(b'fixture')
            self.assertFalse(verified_receipt(path,receipt,request))
            receipt.write_text(json.dumps(dict(status='download_complete',bytes=7,
                sha256=hashlib.sha256(b'fixture').hexdigest(),
                request_sha256=hashlib.sha256(json.dumps(request,sort_keys=True,separators=(',',':')).encode()).hexdigest())))
            self.assertTrue(verified_receipt(path,receipt,request))
            self.assertFalse(verified_receipt(path,receipt,{'year':['2021']}))
            path.write_bytes(b'changed');self.assertFalse(verified_receipt(path,receipt,request))


if __name__=='__main__':unittest.main()
