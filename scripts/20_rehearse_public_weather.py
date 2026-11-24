"""Limited, secondary-source ERA5 rehearsal; never a statewide validation run.

Open-Meteo data: CC BY 4.0, https://open-meteo.com/en/licence.
Reanalysis from ECMWF/Copernicus, processed by Open-Meteo. Cite both providers.
"""

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import time
from urllib.parse import urlencode
from urllib.request import urlopen

import numpy as np
import pandas as pd
import xarray as xr

from continuous_resources import interval_weather_files, join_resource_chunks, model_resource_block
from energy_events import simultaneous_events, combined_window_events

CELLS = [(40.5,-121.5),(38.5,-121.5),(36.5,-120.0),(35.25,-118.5),(33.5,-116.5)]
PERIODS = [('adjoining_2020','2020-01-01','2020-03-01'),
           ('summer_2020','2020-07-01','2020-08-01'),('held_out_2021','2021-01-01','2021-02-01')]
VARIABLES = ['wind_speed_100m','wind_direction_100m','temperature_2m','shortwave_radiation']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_response(response, latitude, longitude, start, stop):
    """Guard the explicitly requested model/grid/units/temporal contract."""
    expected_units=dict(time='iso8601',wind_speed_100m='m/s',wind_direction_100m='°',
                        temperature_2m='°C',shortwave_radiation='W/m²')
    if (response.get('utc_offset_seconds')!=0 or response.get('hourly_units')!=expected_units
            or abs(response.get('latitude',999)-latitude)>1e-5
            or abs(response.get('longitude',999)-longitude)>1e-5):
        raise ValueError('Response grid/timezone/units differ from requested contract.')
    hourly=response['hourly']; index=pd.DatetimeIndex(pd.to_datetime(hourly['time'],utc=True))
    expected=pd.date_range(start,pd.Timestamp(stop)+pd.Timedelta(hours=23),freq='h',tz='UTC')
    if not index.equals(expected):
        raise ValueError('Response has missing, duplicate, or unexpected timestamps.')
    values=np.array([hourly[n] for n in VARIABLES],dtype=float).T
    if values.shape!=(len(index),4) or not np.isfinite(values).all():
        raise ValueError('Invalid or missing weather values.')
    if (values[:,0]<0).any() or not ((values[:,1]>=0)&(values[:,1]<=360)).all() or (values[:,3]<0).any():
        raise ValueError('Invalid wind speed/direction or radiation.')
    return index,values


def make_weather(responses,start,stop):
    lat=sorted({p[0] for p in CELLS},reverse=True);lon=sorted({p[1] for p in CELLS})
    index=pd.date_range(start,stop,freq='h',tz='UTC')
    shape=(len(index),len(lat),len(lon)); arrays={n:np.full(shape,np.nan) for n in ['u100','v100','t2m','ssrd']}
    mask=np.zeros(shape[1:],dtype=np.int8)
    for (latitude,longitude),response in zip(CELLS,responses):
        source=pd.DatetimeIndex(pd.to_datetime(response['hourly']['time'],utc=True))
        positions=source.get_indexer(index)
        if (positions<0).any():
            raise ValueError('Missing required weather support.')
        d={n:np.array(response['hourly'][n],dtype=float)[positions] for n in VARIABLES}
        i,j=lat.index(latitude),lon.index(longitude);mask[i,j]=1
        direction=np.deg2rad(d['wind_direction_100m'])
        arrays['u100'][:,i,j]=-d['wind_speed_100m']*np.sin(direction)
        arrays['v100'][:,i,j]=-d['wind_speed_100m']*np.cos(direction)
        arrays['t2m'][:,i,j]=d['temperature_2m']+273.15
        arrays['ssrd'][:,i,j]=d['shortwave_radiation']*3600
    coords=dict(valid_time=index.tz_localize(None),latitude=lat,longitude=lon)
    ds=xr.Dataset({n:(('valid_time','latitude','longitude'),a) for n,a in arrays.items()},coords=coords)
    for n in ['u100','v100']:
        ds[n].attrs=dict(units='m/s',GRIB_uvRelativeToGrid=0,
            provenance='Reconstructed from rounded Open-Meteo ERA5 speed and direction; not original CDS components.')
    ds.t2m.attrs['units']='K';ds.ssrd.attrs['units']='J/m2'
    ds.attrs['source']='Open-Meteo model=era5, elevation=nan, nearest cell; secondary processed data'
    return ds[['u100','v100','t2m']],ds[['ssrd']],xr.DataArray(mask,dims=('latitude','longitude'),coords={k:coords[k] for k in ['latitude','longitude']})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache-dir',required=True,type=Path)
    parser.add_argument('--original-instant',required=True,type=Path)
    parser.add_argument('--original-accum',required=True,type=Path)
    parser.add_argument('--offline',action='store_true')
    parser.add_argument('--session-date',required=True,type=date.fromisoformat)
    parser.add_argument('--project-dir',type=Path,default=Path(__file__).resolve().parents[1])
    args=parser.parse_args();args.cache_dir.mkdir(parents=True,exist_ok=True)
    root=args.project_dir;manifest=[];summaries=[];overlap=[]
    for label,start,stop in PERIODS:
        responses=[]
        for cell,(latitude,longitude) in enumerate(CELLS):
            params=dict(latitude=latitude,longitude=longitude,start_date=start,end_date=stop,
                hourly=','.join(VARIABLES),models='era5',wind_speed_unit='ms',timezone='UTC',
                elevation='nan',cell_selection='nearest')
            url='https://archive-api.open-meteo.com/v1/archive?'+urlencode(params)
            path=args.cache_dir/f'{label}_cell{cell}.json';receipt=path.with_suffix('.receipt.json')
            if path.exists():
                if not receipt.exists() or json.loads(receipt.read_text())!={'url':url,'sha256':sha(path)}:
                    raise ValueError('Cached response receipt missing or changed.')
            else:
                if args.offline:
                    raise FileNotFoundError(path)
                # Bounded retries; never replace a previously verified cache entry.
                for attempt in range(3):
                    try:
                        with urlopen(url,timeout=45) as connection:
                            raw=connection.read()
                        response=json.loads(raw);validate_response(response,latitude,longitude,start,stop)
                        temp=path.with_suffix('.partial');temp.write_bytes(raw);temp.replace(path)
                        receipt.write_text(json.dumps(dict(url=url,sha256=sha(path)),indent=2)+'\n')
                        break
                    except Exception:
                        if attempt==2:
                            raise
                        time.sleep(2*(attempt+1))
            response=json.loads(path.read_text());validate_response(response,latitude,longitude,start,stop)
            responses.append(response);manifest.append(dict(period=label,cell=cell,url=url,sha256=sha(path),bytes=path.stat().st_size))
        instant,accum,mask=make_weather(responses,start,stop)
        baseline=model_resource_block(instant,accum,mask)
        # API parsing uses microseconds; NetCDF round-tripping uses nanoseconds.
        # Canonicalize precision before exact catalogue schema comparisons.
        baseline.index=baseline.index.as_unit('ns')
        # Real January/February files plus a final endpoint-only file. This
        # exercises carry-over at a true leap-month boundary and endpoint.
        partitions=[]
        for month in sorted(set(pd.DatetimeIndex(instant.valid_time.values).strftime('%Y-%m'))):
            selected=pd.DatetimeIndex(instant.valid_time.values).strftime('%Y-%m')==month
            i_path=args.cache_dir/f'{label}_{month}_instant.nc';a_path=args.cache_dir/f'{label}_{month}_accum.nc'
            instant.isel(valid_time=selected).to_netcdf(i_path);accum.isel(valid_time=selected).to_netcdf(a_path)
            partitions.append((i_path,a_path))
        chunked=join_resource_chunks(model_resource_block(i,a,mask) for i,a in interval_weather_files(partitions,mask))
        chunked.index=chunked.index.as_unit('ns')
        if not baseline.index.equals(chunked.index) or not np.allclose(baseline,chunked,atol=1e-12,rtol=0):
            raise AssertionError('Real month partition changed resource results.')
        low,strict=simultaneous_events(chunked)
        diagnostic,windows=combined_window_events(chunked)
        for expected,actual in [(simultaneous_events(baseline)[1],strict),
                                (combined_window_events(baseline)[1],windows)]:
            pd.testing.assert_frame_equal(expected,actual)
        for name,catalogue in [('strict',strict),('window48',windows)]:
            catalogue.to_csv(root/f'results/tables/rehearsal_{label}_{name}_five_cells.csv',index=False)
        output=root/f'data/processed/rehearsal_{label}_five_cells.csv';chunked.to_csv(output)
        summaries.append(dict(period=label,cell_count=len(CELLS),hours=len(chunked),first_interval_end=str(chunked.index[0]),
            last_interval_end=str(chunked.index[-1]),wind_mean=float(chunked.wind_cf.mean()),pv_mean=float(chunked.pv_cf.mean()),
            chunk_max_abs_difference=float(np.abs(baseline-chunked).to_numpy().max()),output_sha256=sha(output)))
        summaries[-1].update(strict_low_hours=int(low.sum()),strict_24h_events=int(strict.meets_minimum_duration.sum()),
            combined_48h_events=len(windows),qualifying_48h_windows=int(diagnostic.qualifying_window_endpoint.sum()))
        if label=='adjoining_2020':
            with xr.open_dataset(args.original_instant) as oi,xr.open_dataset(args.original_accum) as oa:
                for (latitude,longitude),response in zip(CELLS,responses):
                    frame=response['hourly'];p=oi.sel(latitude=latitude,longitude=longitude);q=oa.sel(latitude=latitude,longitude=longitude)
                    original=[np.hypot(p.u100,p.v100).values,p.t2m.values-273.15,q.ssrd.values/3600]
                    for name,values in zip(['wind_speed_100m','temperature_2m','shortwave_radiation'],original):
                        delta=np.array(frame[name][:744])-values
                        overlap.append(dict(latitude=latitude,longitude=longitude,variable=name,hours=744,
                            mean_abs_difference=float(np.abs(delta).mean()),max_abs_difference=float(np.abs(delta).max())))
        print(label,len(chunked),'hours passed',flush=True)
    for rows,name in [(summaries,'public_weather_rehearsal_summary.csv'),(overlap,'public_weather_overlap_2020_01.csv')]:
        pd.DataFrame(rows).to_csv(root/'results/tables'/name,index=False)
    record=dict(execution_date=str(args.session_date),source='https://open-meteo.com/en/docs/historical-weather-api',
        license='CC BY 4.0; attribute Open-Meteo and underlying ECMWF/Copernicus ERA5',cells=CELLS,requests=manifest,
        original_sha256={str(p):sha(p) for p in [args.original_instant,args.original_accum]},
        scope='Five preselected cells, not the 695-cell statewide model or independent weather observations.',
        parameters='Preserved cubic wind and PV35; no fitting to summer or held-out year.',
        limitations=['Secondary rounded/processed ERA5 differs from original CDS forcing; do not splice sources.',
            'No matched generation validation for summer or held-out period.',
            'This checks real-weather processing continuity, not physical or statewide climatology validity.'])
    (root/'results/tables/public_weather_rehearsal_metadata.json').write_text(json.dumps(record,indent=2)+'\n')


if __name__=='__main__':
    main()
