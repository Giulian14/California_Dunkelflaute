"""Plan CDS requests and audit original-style ERA5 inputs without downloading."""
import calendar
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr


def acquisition_plan():
    """242 monthly requests, including one context month on either side.

    Context does not guarantee an event ends within the acquired range: retain
    edge censoring. Creating this object makes no network request.
    """
    batches=[]
    for month in pd.period_range('2004-12','2025-01',freq='M'):
        days=calendar.monthrange(month.year,month.month)[1]
        request=dict(product_type=['reanalysis'],year=[str(month.year)],month=[f'{month.month:02d}'],
            day=[f'{day:02d}' for day in range(1,days+1)],time=[f'{hour:02d}:00' for hour in range(24)],
            data_format='netcdf',download_format='zip',grid=[.25,.25],area=[42,-125,32,-114],
            variable=['100m_u_component_of_wind','100m_v_component_of_wind','2m_temperature',
                      'surface_solar_radiation_downwards'])
        encoded=json.dumps(request,sort_keys=True,separators=(',',':')).encode()
        batches.append(dict(batch_id=str(month),role='core' if 2005<=month.year<=2024 else 'context',
            dataset='reanalysis-era5-single-levels',request=request,request_sha256=hashlib.sha256(encoded).hexdigest(),
            expected_snapshot_hours=days*24,expected_spatial_shape=[41,45]))
    return dict(status='PLAN_ONLY_NOT_SUBMITTED',core_start_utc='2005-01-01T00:00:00Z',
        core_stop_utc='2025-01-01T00:00:00Z',core_hours=175320,batches=batches,
        resume_rule='Reuse only a complete archive with matching request hash, byte SHA256 and passing NetCDF QC; partial files never qualify.',
        execution_gate='Resolve scientific model gates and verify a limited direct-CDS multi-month rehearsal before submitting the archive.',
        context_rule='Detect on joined extended data; retain events intersecting core, clip exposure summaries to core and flag censored durations.')


def audit_weather(instant,accum,expected_start,expected_stop):
    """Fail closed on grid, support, product semantics, units or missing values."""
    for ds,names in [(instant,['u100','v100','t2m']),(accum,['ssrd'])]:
        if not set(names).issubset(ds.data_vars):
            raise ValueError('Missing required variables.')
        for coordinate,expected in [('latitude',np.arange(42,31.99,-.25)),('longitude',np.arange(-125,-113.99,.25))]:
            if not np.array_equal(ds[coordinate].values,expected):
                raise ValueError('Unexpected grid or coordinate ordering.')
        index=pd.DatetimeIndex(ds.valid_time.values)
        index=index.tz_localize('UTC') if index.tz is None else index.tz_convert('UTC')
        expected=pd.date_range(expected_start,expected_stop,freq='h',tz='UTC')
        if not index.equals(expected):
            raise ValueError('Unexpected, missing, duplicate or out-of-order hourly timestamps.')
        if 'expver' not in ds.coords or not set(np.asarray(ds.expver.values).astype(str).ravel())<= {'1','0001'}:
            raise ValueError('Require explicit final ERA5 expver=1; review other product versions separately.')
    xr.align(instant,accum,join='exact')
    summary={}
    for name,ds,units,step,low,high in [
        ('u100',instant,{'m s**-1','m/s'},'instant',-150,150),
        ('v100',instant,{'m s**-1','m/s'},'instant',-150,150),
        ('t2m',instant,{'K','kelvin'},'instant',150,350),
        ('ssrd',accum,{'J m**-2','J/m2'},'accum',-1,6000000)]:
        data=ds[name]
        if (set(data.dims)!={'valid_time','latitude','longitude'} or data.attrs.get('units') not in units
                or data.attrs.get('GRIB_stepType')!=step):
            raise ValueError('Unexpected dimensions, units or product accumulation convention.')
        if name in ['u100','v100'] and data.attrs.get('GRIB_uvRelativeToGrid')!=0:
            raise ValueError('Unknown or rotated wind vector convention.')
        values=np.asarray(data.values)
        if not np.isfinite(values).all() or (values<low).any() or (values>high).any():
            raise ValueError('Missing, sentinel or implausible forcing values.')
        summary[name]=dict(minimum=float(values.min()),maximum=float(values.max()),dtype=str(values.dtype),units=data.attrs['units'])
    return dict(status='PASS',snapshot_hours=len(expected),variables=summary,expver='1',
        note='Checks product consistency and broad physical bounds; does not validate weather accuracy.')


def verified_receipt(archive_path,receipt_path,request):
    """A resumable cache accepts exactly the requested, byte-verified archive.

    A successful downloaded zip still needs extraction and weather QC before
    scientific processing. Never interpret a download receipt as scientific QC.
    """
    archive_path,receipt_path=Path(archive_path),Path(receipt_path)
    if not archive_path.is_file() or not receipt_path.is_file():
        return False
    receipt=json.loads(receipt_path.read_text())
    request_hash=hashlib.sha256(json.dumps(request,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if receipt.get('request_sha256')!=request_hash or receipt.get('status')!='download_complete':
        return False
    digest=hashlib.sha256()
    with archive_path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):
            digest.update(block)
    return receipt.get('sha256')==digest.hexdigest() and receipt.get('bytes')==archive_path.stat().st_size
