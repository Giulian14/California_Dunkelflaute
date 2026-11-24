"""Independent source/denominator and five-cell equation checks, without downloads.

Does not import the new matching, adapter or model helpers. Uses pvlib's
documented equations to check the adapter's preserved physical configuration.
This is computational verification, not independent weather validation.
"""
import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
import zipfile
import numpy as np
import pandas as pd
import pvlib


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache-dir',required=True,type=Path)
    parser.add_argument('--eia923-archive',required=True,type=Path)
    parser.add_argument('--project-dir',type=Path,default=Path(__file__).resolve().parents[1])
    args=parser.parse_args();root=args.project_dir;tables=root/'results/tables'
    meta=json.loads((tables/'fixed_tilt_pv_validation_metadata_2020_01.json').read_text())
    for path,digest in meta['sources_sha256'].items():assert sha(path)==digest,path
    for path,digest in meta['artifacts_sha256'].items():assert sha(root/path)==digest,path
    source=lambda name:next(Path(p) for p in meta['sources_sha256'] if Path(p).name==name)
    units=pd.read_csv(root/'data/reference/jan2020_fixed_tilt_pv_generators.csv')
    plant=pd.read_csv(tables/'fixed_tilt_pv_plant_bounds_2020_01.csv').set_index('plant_id')
    for name in ['december_generator2019.xlsx','january_generator2020.xlsx']:
        raw=pd.read_excel(source(name),sheet_name='Operating',header=1,engine='openpyxl')
        raw=raw.loc[raw['Plant State'].eq('CA') & raw.Technology.eq('Solar Photovoltaic')]
        for pid,group in units.groupby('plant_id'):
            r=raw.loc[raw['Plant ID'].eq(pid)]
            assert set(r['Generator ID'].astype(str))==set(group.generator_id.astype(str))
            assert r.Status.eq('(OP) Operating').all()
            assert np.isclose(r['Nameplate Capacity (MW)'].sum(),plant.loc[pid,'capacity_mw'])
    with zipfile.ZipFile(source('eia8602020.zip')) as z:
        frames=[pd.read_excel(BytesIO(z.read('3_3_Solar_Y2020.xlsx')),sheet_name=s,header=1,engine='openpyxl')
                for s in ['Operable','Retired and Canceled']]
    annual=pd.concat(frames);annual=annual.loc[annual.State.eq('CA')&annual.Technology.eq('Solar Photovoltaic')]
    for pid,group in units.groupby('plant_id'):
        r=annual.loc[annual['Plant Code'].eq(pid)]
        assert set(r['Generator ID'].astype(str))==set(group.generator_id.astype(str))
        assert r['Fixed Tilt?'].eq('Y').all()
        assert not r[['Single-Axis Tracking?','Dual-Axis Tracking?','East West Fixed Tilt?',
                      'Lenses / Mirrors?','Other Solar Technology?']].eq('Y').any().any()
        assert np.isclose(r['Nameplate Capacity (MW)'].sum(),plant.loc[pid,'capacity_mw'])
    original=json.loads((tables/'generation_observation_metadata_2020_01.json').read_text())['sources'][1]
    assert sha(args.eia923_archive)==original['sha256']
    with zipfile.ZipFile(args.eia923_archive) as z:
        energy=pd.read_excel(BytesIO(z.read(original['member'])),sheet_name=original['sheet'],header=5,engine='openpyxl')
    energy=energy.loc[energy['Plant State'].eq('CA')&energy['Reported\nFuel Type Code'].eq('SUN')
                     &energy['Reported\nPrime Mover'].eq('PV')].set_index('Plant Id')
    observed=pd.to_numeric(energy.loc[plant.index,'Netgen\nJanuary'],errors='raise').to_numpy()
    np.testing.assert_allclose(observed,plant.observed_energy_mwh,rtol=0,atol=1e-8)
    capacity=float(units.capacity_mw.sum());summary=meta['summary']
    assert np.isclose(observed.sum()/(capacity*744),summary['observed_cf'])
    hourly=pd.read_csv(root/'data/processed/fixed_tilt_pv_hourly_2020_01.csv',index_col=0)
    index=pd.to_datetime(hourly.index,utc=True);values=hourly.pv_cf.to_numpy()[index>=pd.Timestamp('2020-01-01T09:00Z')]
    assert len(values)==735
    assert np.isclose(values.sum()/744,summary['monthly_cf_lower_bound'])
    assert np.isclose((values.sum()+9)/744,summary['monthly_cf_upper_bound'])
    for bound in ['lower','upper']:
        assert np.isclose(plant[f'monthly_energy_{bound}_bound_mwh'].sum(),summary[f'monthly_energy_{bound}_bound_mwh'])
    weather=json.loads((tables/'public_weather_rehearsal_metadata.json').read_text())
    errors=[]
    for label in ['adjoining_2020','summer_2020','held_out_2021']:
        saved=pd.read_csv(root/f'data/processed/rehearsal_{label}_five_cells.csv',index_col=0)
        ends=pd.to_datetime(saved.index,utc=True);mid=ends-pd.Timedelta(minutes=30)
        independent=np.zeros((len(ends),2));weights=np.cos(np.deg2rad([p[0] for p in weather['cells']]))
        weights/=weights.sum()
        for cell,((lat,lon),weight) in enumerate(zip(weather['cells'],weights)):
            receipt=next(r for r in weather['requests'] if r['period']==label and r['cell']==cell)
            path=args.cache_dir/f'{label}_cell{cell}.json';assert sha(path)==receipt['sha256']
            raw=json.loads(path.read_text())['hourly'];positions=pd.Index(pd.to_datetime(raw['time'],utc=True)).get_indexer(ends)
            assert (positions>0).all()
            speed=np.array(raw['wind_speed_100m'],float)
            curve=np.where((speed>=3)&(speed<12),(speed**3-27)/(1728-27),np.where((speed>=12)&(speed<25),1.,0.))
            independent[:,0]+=weight*(curve[positions-1]+curve[positions])/2
            ghi=np.array(raw['shortwave_radiation'],float)[positions]
            temperature=np.array(raw['temperature_2m'],float)
            temp=(temperature[positions-1]+temperature[positions])/2
            solar=pvlib.solarposition.get_solarposition(mid,lat,lon,altitude=0,pressure=101325,temperature=temp,method='nrel_numpy')
            zenith=solar.zenith.to_numpy();parts=pvlib.irradiance.erbs(ghi,zenith,mid.day_of_year.to_numpy())
            dni=np.where(zenith>=87,0,parts['dni']);dhi=np.where(zenith>=87,ghi,parts['dhi'])
            poa=np.maximum(pvlib.irradiance.get_total_irradiance(35,180,zenith,solar.azimuth,dni,ghi,dhi,albedo=.2,model='isotropic')['poa_global'],0)
            celltemp=pvlib.temperature.ross(poa,temp,noct=45)
            dc=np.maximum(pvlib.pvsystem.pvwatts_dc(poa,celltemp,1.2,-.004,temp_ref=25),0)*.86
            ac=np.clip(pvlib.inverter.pvwatts(dc,pdc0=1/.96,eta_inv_nom=.96),0,1)
            independent[:,1]+=weight*np.asarray(ac)
        delta=np.abs(independent-saved[['wind_cf','pv_cf']].to_numpy())
        assert delta.max()<1e-12
        errors.append(dict(period=label,hours=len(saved),max_abs_difference=float(delta.max())))
        low=(independent[:,0]<.2)&(independent[:,1]<.2)
        edges=np.flatnonzero(np.diff(np.r_[False,low,False])).reshape(-1,2)
        catalogue=pd.read_csv(tables/f'rehearsal_{label}_strict_five_cells.csv')
        assert catalogue.duration_hours.tolist()==[int(b-a) for a,b in edges]
        combined=independent.mean(axis=1)
        flags=np.array([np.mean(combined[i-47:i+1])<.06 for i in range(47,len(combined))])
        assert not flags.any()  # All three predefined limited cases have no qualifying windows.
    result=dict(status='PASS',execution_date=meta['execution_date'],matched_plants=len(plant),matched_generators=len(units),
        capacity_mw=capacity,observed_energy_mwh=float(observed.sum()),independent_weather_equations=errors,
        method='Direct raw EIA unit/technology/capacity and EIA923 energy checks; manual aggregation/bounds; direct pvlib equations and cubic curve, without new project helpers.',
        limitations='Does not independently validate ERA5 weather or annual equipment timing; full physical/held-out validation remains open.',
        eia923_source_sha256=sha(args.eia923_archive))
    (tables/'pre_expansion_independent_checks.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
