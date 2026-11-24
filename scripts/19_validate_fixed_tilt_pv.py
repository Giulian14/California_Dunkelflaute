"""Match January PV-only energy to stable whole plants and reported geometry."""

import argparse
from datetime import date
from dataclasses import asdict
import hashlib
from io import BytesIO
import json
from pathlib import Path
import zipfile

import numpy as np
import pandas as pd
import shapely
import xarray as xr

from january_pv import match_pv, monthly_pv
from january_wind import monthly_bounds
from pv_model import PVConfig, model_cell


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ['december','january','annual','instant','accum']:
        parser.add_argument('--'+arg,required=True,type=Path)
    parser.add_argument('--project-dir',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--session-date',required=True,type=date.fromisoformat)
    parser.add_argument('--headless',action='store_true')
    args = parser.parse_args(); root = args.project_dir
    prior=json.loads((root/'data/reference/jan2020_wind_inventory_metadata.json').read_text())
    annual_meta=json.loads((root/'data/reference/eia2020_ca_wind_metadata.json').read_text())
    for path,expected in [(args.december,prior['sources'][0]['sha256']),
                          (args.january,prior['sources'][1]['sha256']),
                          (args.annual,annual_meta['archive_sha256'])]:
        if sha(path)!=expected:
            raise ValueError('Use the preserved December/January/annual source versions.')
    frames = []
    with zipfile.ZipFile(args.annual) as z:
        raw = z.read('3_3_Solar_Y2020.xlsx')
    for sheet in ['Operable','Retired and Canceled']:
        f = pd.read_excel(BytesIO(raw),sheet_name=sheet,header=1,engine='openpyxl')
        f['annual_source_sheet'] = sheet; f['annual_source_excel_row'] = f.index+3
        frames.append(f.loc[f.State.eq('CA') & f.Technology.eq('Solar Photovoltaic')].copy())
    annual = pd.concat(frames).rename(columns={'Plant Code':'plant_id','Generator ID':'generator_id',
        'Nameplate Capacity (MW)':'capacity_mw','DC Net Capacity (MW)':'dc_capacity_mw',
        'Tilt Angle':'tilt_deg','Azimuth Angle':'azimuth_deg','Fixed Tilt?':'fixed_tilt',
        'Single-Axis Tracking?':'single_axis','Dual-Axis Tracking?':'dual_axis',
        'East West Fixed Tilt?':'east_west','Lenses / Mirrors?':'concentrator','Other Solar Technology?':'other_solar'})
    annual['generator_id'] = annual.generator_id.astype(str).str.strip()
    for col in ['capacity_mw','dc_capacity_mw','tilt_deg','azimuth_deg']:
        annual[col] = pd.to_numeric(annual[col],errors='coerce')
    dec, jan = [monthly_pv(pd.read_excel(p,sheet_name='Operating',header=1,engine='openpyxl'))
                for p in [args.december,args.january]]
    genpath = root/'data/processed/eia923_generation_scope_audit_2020_01.csv'
    boundarypath = root/'data/boundaries/california_census_2026.geojson'
    obj = json.loads(boundarypath.read_text())
    boundary = shapely.union_all([shapely.from_geojson(json.dumps(f['geometry'])) for f in obj['features']]) if obj['type']=='FeatureCollection' else shapely.from_geojson(json.dumps(obj['geometry'] if obj['type']=='Feature' else obj))
    audit, units = match_pv(dec,jan,annual,pd.read_csv(genpath),boundary)
    if units.empty:
        raise ValueError('No complete fixed-tilt plants available.')
    ref = root/'data/reference'; tables=root/'results/tables'; processed=root/'data/processed'
    outputs = []
    for f,name,directory in [(audit,'jan2020_pv_matching_audit.csv',tables),(units,'jan2020_fixed_tilt_pv_generators.csv',ref)]:
        path=directory/name; f.to_csv(path,index=False); outputs.append(path)
    with xr.open_dataset(args.instant,engine='netcdf4') as source:
        instant=source[['t2m']].load()
    with xr.open_dataset(args.accum,engine='netcdf4') as source:
        accum=source[['ssrd']].load()
    instant,accum=xr.align(instant,accum,join='exact')
    if instant.t2m.attrs.get('units') != 'K' or accum.ssrd.attrs.get('units') != 'J m**-2':
        raise ValueError('Unexpected forcing units.')
    times=pd.DatetimeIndex(instant.valid_time.values).tz_localize('UTC')
    expected=pd.date_range('2020-01-01',periods=744,freq='h',tz='UTC')
    if not times.equals(expected):
        raise ValueError('This validation driver is restricted to the January pilot.')
    ends=times[1:]; retain=ends>=pd.Timestamp('2020-01-01T09:00Z')
    diagnostics=[]; plants=[]; hourly=np.zeros(len(ends)); total=units.capacity_mw.sum()
    for pid,group in units.groupby('plant_id'):
        plant_cf=np.zeros(len(ends)); capacity=group.capacity_mw.sum()
        for row in group.itertuples():
            i=instant.sel(latitude=row.latitude,longitude=row.longitude,method='nearest')
            a=accum.sel(latitude=i.latitude,longitude=i.longitude)
            ghi=np.maximum(a.ssrd.values[1:],0)/3600
            if (a.ssrd.values < -1).any():
                raise ValueError('Unexpected negative radiation.')
            temp=(i.t2m.values[:-1].astype(float)+i.t2m.values[1:].astype(float))/2-273.15
            config=PVConfig(tilt_deg=row.tilt_deg,azimuth_deg=row.azimuth_deg,
                            dc_ac_ratio=row.dc_capacity_mw/row.capacity_mw)
            cf=model_cell(ends,ghi,temp,row.latitude,row.longitude,config).pv_ac_capacity_factor.to_numpy()
            plant_cf+=cf*row.capacity_mw/capacity
            diagnostics.append(dict(plant_id=int(pid),generator_id=row.generator_id,grid_latitude=float(i.latitude),
                grid_longitude=float(i.longitude),capacity_mw=row.capacity_mw,**asdict(config)))
        bounds=monthly_bounds(plant_cf[retain],ends[retain],capacity)
        observed=float(audit.loc[audit.plant_id.eq(pid),'january_net_generation_mwh'].iloc[0])
        plants.append(dict(plant_id=int(pid),plant_name=group.plant_name.iloc[0],capacity_mw=capacity,
            observed_energy_mwh=observed,observed_cf=observed/(744*capacity),**bounds))
        hourly+=plant_cf*capacity/total
    planttable=pd.DataFrame(plants)
    observed=planttable.observed_energy_mwh.sum()
    summary=dict(plant_count=len(planttable),generator_count=len(units),capacity_mw=float(total),
        observed_energy_mwh=float(observed),observed_cf=float(observed/(744*total)),
        **monthly_bounds(hourly[retain],ends[retain],total))
    import matplotlib
    if args.headless:
        matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(10,4))
    axes[0].bar([0,1],[summary['observed_cf'],summary['monthly_cf_lower_bound']],
                color=['#356c9b','#ce7625'])
    axes[0].errorbar([1],[summary['monthly_cf_lower_bound']],
        yerr=[[0],[summary['monthly_cf_upper_bound']-summary['monthly_cf_lower_bound']]],
        color='black',capsize=5,fmt='none')
    axes[0].set(xticks=[0,1],xticklabels=['Observed net','Modeled AC'],ylabel='Monthly capacity factor',
        title=f'{len(planttable)} fixed-tilt plants; {total:,.1f} MW AC')
    midpoint=(planttable.monthly_cf_lower_bound+planttable.monthly_cf_upper_bound)/2
    error=(planttable.monthly_cf_upper_bound-planttable.monthly_cf_lower_bound)/2
    axes[1].errorbar(planttable.observed_cf,midpoint,yerr=error,fmt='.',alpha=.4,markersize=4,
        color='#356c9b',elinewidth=.5)
    limit=max(float(planttable.observed_cf.max()),float(planttable.monthly_cf_upper_bound.max()))*1.05
    axes[1].plot([0,limit],[0,limit],'--',color='grey')
    axes[1].set(xlabel='Observed net capacity factor',ylabel='Modeled AC capacity factor',
        title='Whole-plant comparison',xlim=(0,limit),ylim=(0,limit))
    fig.suptitle('Pacific January 2020 — conservative fixed-tilt PV subset')
    fig.text(.5,.01,'Bars/lines bound nine unavailable hours; annual equipment properties are proxies. No fitting.',
        ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.05,1,.95))
    figure=root/'results/figures/fixed_tilt_pv_validation_2020_01.png'
    fig.savefig(figure,dpi=180);plt.close(fig);outputs.append(figure)
    for frame,name,directory in [(planttable,'fixed_tilt_pv_plant_bounds_2020_01.csv',tables),
        (pd.DataFrame(diagnostics),'fixed_tilt_pv_model_parameters_2020_01.csv',tables),
        (pd.DataFrame({'pv_cf':hourly},index=ends),'fixed_tilt_pv_hourly_2020_01.csv',processed)]:
        path=directory/name; frame.to_csv(path,index=True if directory==processed else False);outputs.append(path)
    sources={str(p):sha(p) for p in [args.december,args.january,args.annual,args.instant,args.accum,genpath,boundarypath]}
    metadata=dict(execution_date=str(args.session_date),summary=summary,stable_capacity_matched_plants=int(audit.stable_capacity_matched.sum()),
        exclusion_counts=audit.exclusion_reason.value_counts().to_dict(),sources_sha256=sources,
        artifacts_sha256={str(p.relative_to(root)):sha(p) for p in outputs},
        limitations=['Annual technology and geometry are year-end proxies, not verified January equipment.',
        'Select-all blank flags mean not selected; tracking absence is not independently verified.',
        'Fixed-tilt subset does not validate tracker fleet, distributed PV, or solar thermal.',
        'EIA net generation includes effects not modeled by fixed loss/temperature assumptions.',
        'Nine missing Pacific-month hours are bounded, not imputed.'])
    path=tables/'fixed_tilt_pv_validation_metadata_2020_01.json';path.write_text(json.dumps(metadata,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
