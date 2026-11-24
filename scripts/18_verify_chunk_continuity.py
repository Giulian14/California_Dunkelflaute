"""Verify real January file partitions and explicitly synthetic calendar cases."""

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import platform
import tempfile

import numpy as np
import pandas as pd
import xarray as xr

from continuous_resources import interval_weather_files, join_resource_chunks, model_resource_block
from energy_events import combined_window_events, simultaneous_events
from pv_model import prepare_forcing


def checksum(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def compare_events(reference, candidate):
    low_a, periods_a=simultaneous_events(reference)
    low_b, periods_b=simultaneous_events(candidate)
    np.testing.assert_array_equal(low_a,low_b)
    pd.testing.assert_frame_equal(periods_a,periods_b)
    rows=[]
    for share in [.25,.5,.75]:
        for threshold in [.05,.06,.10]:
            diagnostic_a,events_a=combined_window_events(reference,share,threshold)
            diagnostic_b,events_b=combined_window_events(candidate,share,threshold)
            pd.testing.assert_frame_equal(diagnostic_a,diagnostic_b,check_exact=False,rtol=0,atol=1e-12)
            pd.testing.assert_frame_equal(events_a,events_b)
            rows.append({'wind_share':share,'threshold':threshold,
                'qualifying_windows':int(diagnostic_b.qualifying_window_endpoint.sum()),
                'covered_hours':int(diagnostic_b.covered_by_qualifying_window.sum()),
                'union_events':len(events_b),'event_catalogue_matches':True})
    return rows,{'low_hours':int(low_b.sum()),'low_periods':len(periods_b),
                 'qualifying_at_least_24h':int(periods_b.meets_minimum_duration.sum()),'catalogue_matches':True}


def write_partitions(instant,accum,cuts,folder):
    paths=[]
    for n,(start,stop) in enumerate(zip(cuts,cuts[1:])):
        pair=[]
        for name,source in [('instant',instant),('accum',accum)]:
            block=source.isel(valid_time=slice(start,stop)).copy(deep=True)
            # Preserve decoded physical values, not the original full-month chunk encoding.
            for variable in block.variables:block[variable].encoding={}
            path=folder/f'{name}_{n:02d}.nc';block.to_netcdf(path,engine='netcdf4');pair.append(path)
        paths.append(tuple(pair))
    return paths


def synthetic_calendars():
    rows=[];catalogues=[]
    for name,start in [('synthetic_new_year','2019-12-28T01:00Z'),
                       ('synthetic_leap_day','2020-02-26T01:00Z'),
                       ('synthetic_nonleap_february','2019-02-25T01:00Z')]:
        index=pd.date_range(start,periods=216,freq='h')
        values=np.full(216,.5);values[72:144]=.01
        whole=pd.DataFrame({'wind_cf':values,'pv_cf':values},index=index)
        labels=index.strftime('%Y-%m')
        boundaries=np.r_[0,np.flatnonzero(labels[1:]!=labels[:-1])+1,len(index)]
        pieces=[whole.iloc[a:b] for a,b in zip(boundaries,boundaries[1:])]
        joined=join_resource_chunks(pieces);pd.testing.assert_frame_equal(joined,whole)
        _,strict=simultaneous_events(joined);diag,combined=combined_window_events(joined)
        assert strict.duration_hours.tolist()==[72] and combined.duration_hours.tolist()==[80]
        assert int(diag.qualifying_window_endpoint.sum())==33
        assert not combined.boundary_context_incomplete.any()
        naive_strict=[simultaneous_events(piece)[1] for piece in pieces]
        naive_combined=[combined_window_events(piece)[1] for piece in pieces]
        naive_union_hours=sum(int(table.duration_hours.sum()) for table in naive_combined)
        assert naive_union_hours==53
        rows.append({'case':name,'data_kind':'synthetic','intervals':len(joined),'calendar_files':len(pieces),
            'strict_low_period_hours':72,'joined_window_union_hours':80,'joined_qualifying_windows':33,
            'naive_independent_window_union_hours':naive_union_hours,
            'naive_strict_periods':sum(len(table) for table in naive_strict),
            'joined_strict_periods':len(strict),'join_matches_continuous_reference':True})
        catalogues.extend([strict.assign(case=name,definition='hourly simultaneous',data_kind='synthetic'),
                           combined.assign(case=name,definition='48h window support union',data_kind='synthetic')])
    return pd.DataFrame(rows),pd.concat(catalogues,ignore_index=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-dir',type=Path,default=Path(__file__).resolve().parent.parent)
    parser.add_argument('--instant',type=Path)
    parser.add_argument('--accum',type=Path)
    parser.add_argument('--mask',type=Path)
    parser.add_argument('--session-date',required=True)
    args=parser.parse_args();date.fromisoformat(args.session_date)
    project=args.project_dir.resolve();processed,tables=project/'data/processed',project/'results/tables'
    instant_path=args.instant or project/'data/raw/data_stream-oper_stepType-instant.nc'
    accum_path=args.accum or project/'data/raw/data_stream-oper_stepType-accum.nc'
    mask_path=args.mask or processed/'california_mask.nc'
    with xr.open_dataset(instant_path,engine='netcdf4') as source:instant=source.load()
    with xr.open_dataset(accum_path,engine='netcdf4') as source:accum=source.load()
    with xr.open_dataset(mask_path,engine='netcdf4') as source:mask=source.california_mask.load()
    if instant.sizes['valid_time']!=744:
        raise ValueError('This validation driver is specifically the 744-snapshot January pilot.')
    forcing=prepare_forcing(instant,accum,mask)
    print('Modeling continuous January reference across all selected cells.',flush=True)
    reference=model_resource_block(instant,accum,mask)
    reference_path=processed/'continuity_reference_resources_2020_01.csv'
    reference.to_csv(reference_path,index_label='interval_end_utc')
    wind_path=processed/'wind_assessment_2020_01.csv';pv_path=processed/'pv_ac_capacity_factor_2020_01.csv'
    archived_wind=pd.read_csv(wind_path,index_col=0);archived_wind.index=pd.to_datetime(archived_wind.index,utc=True)
    archived_pv=pd.read_csv(pv_path,index_col=0);archived_pv.index=pd.to_datetime(archived_pv.index,utc=True)
    assert reference.index.equals(archived_wind.index) and reference.index.equals(archived_pv.index)
    wind_regression=float(np.max(abs(reference.wind_cf.to_numpy()-archived_wind.cubic_uniform.to_numpy())))
    pv_regression=float(np.max(abs(reference.pv_cf.to_numpy()-archived_pv.pv_ac_capacity_factor.to_numpy())))
    assert wind_regression<1e-12 and pv_regression<1e-12
    weather_checks=[];event_checks=[];hourly_checks=[];artifacts=[reference_path]
    case_cuts={'two_files':[0,500,744],'irregular_files':[0,1,25,169,481,743,744]}
    for name,cuts in case_cuts.items():
        print(f'Checking {name}: {len(cuts)-1} temporary NetCDF pairs.',flush=True)
        with tempfile.TemporaryDirectory(prefix='california_continuity_') as scratch:
            paths=write_partitions(instant,accum,cuts,Path(scratch))
            resources=[];position=0;ghi_error=temp_error=0.
            for i,a in interval_weather_files(paths,mask):
                f=prepare_forcing(i,a,mask);n=len(f['interval_end'])
                assert f['interval_end'].equals(forcing['interval_end'][position:position+n])
                ghi_error=max(ghi_error,float(np.max(abs(f['ghi']-forcing['ghi'][position:position+n]))))
                temp_error=max(temp_error,float(np.max(abs(f['temp_air']-forcing['temp_air'][position:position+n]))))
                resources.append(model_resource_block(i,a,mask));position+=n
            joined=join_resource_chunks(resources)
            pd.testing.assert_frame_equal(joined,reference,check_exact=False,rtol=0,atol=1e-12)
            assert position==743 and ghi_error==0 and temp_error==0
            wind_error=float(np.max(abs(joined.wind_cf-reference.wind_cf)))
            pv_error=float(np.max(abs(joined.pv_cf-reference.pv_cf)))
            checks,strict=compare_events(reference,joined)
            event_checks.extend([dict(case=name,**row) for row in checks]);hourly_checks.append(dict(case=name,**strict))
            # Demonstrate why per-file event catalogues must not be treated as final.
            naive=[combined_window_events(piece,.75,.06)[1] for piece in resources]
            whole_d,whole_c=combined_window_events(joined,.75,.06)
            weather_checks.append({'case':name,'data_kind':'real_January_repartitioned','file_pairs':len(paths),
                'input_snapshots':744,'output_intervals':len(joined),'global_initial_unbracketed_records':1,
                'maximum_ghi_difference_w_m2':ghi_error,'maximum_air_temperature_difference_c':temp_error,
                'maximum_wind_cf_difference':wind_error,'maximum_pv_cf_difference':pv_error,
                'joined_75pct_006_union_events':len(whole_c),'naive_per_file_75pct_006_events':sum(len(frame) for frame in naive),
                'joined_75pct_006_covered_hours':int(whole_d.covered_by_qualifying_window.sum()),
                'naive_per_file_75pct_006_union_hour_sum':sum(int(frame.duration_hours.sum()) for frame in naive)})
        output=processed/f'continuity_{name}_resources_2020_01.csv';joined.to_csv(output,index_label='interval_end_utc');artifacts.append(output)
    for stem,frame in [('weather_checks',pd.DataFrame(weather_checks)),('event_checks',pd.DataFrame(event_checks)),
                       ('hourly_reference_checks',pd.DataFrame(hourly_checks))]:
        path=tables/f'continuity_{stem}_2020_01.csv';frame.to_csv(path,index=False);artifacts.append(path)
    synthetic,synthetic_events=synthetic_calendars()
    for stem,frame in [('synthetic_calendar_checks',synthetic),('synthetic_events',synthetic_events)]:
        path=tables/f'continuity_{stem}.csv';frame.to_csv(path,index=False);artifacts.append(path)
    core=pd.date_range('2005-01-01T01:00Z','2025-01-01T00:00Z',freq='h')
    assert len(core)==175320
    metadata={'session_date':args.session_date,'python':platform.python_version(),
        'status':'Computational continuity verification; not a new climate or physical-model validation',
        'real_data_scope':'Existing January 2020 fields repartitioned into new temporary files, not actual adjacent-month observations',
        'physical_models':'Unchanged cubic/uniform wind and 35-degree fixed-tilt PV; every selected cell modeled before averaging',
        'selected_cells':int(mask.values.sum()),'input_snapshots':744,'complete_intervals':len(reference),
        'weather_partition_cases':case_cuts,'rolling_event_cases':len(event_checks),'synthetic_calendar_cases':len(synthetic),
        'wind_regression_max_abs_difference':wind_regression,'pv_regression_max_abs_difference':pv_regression,
        'core_2005_2024_hours':len(core),'core_interval_end_first':str(core[0]),'core_interval_end_last':str(core[-1]),
        'architecture':'Read one weather pair plus its preceding snapshot; join compact resource means before global rolling/event calculations',
        'strict_data_handling':'Reject gaps, overlaps, missing values, changed units/dtypes/grids; no zero fill, sorting repair, or per-file event reset',
        'limits':['Real multi-month data, full-scale acquisition and performance not tested.','Synthetic new-year/leap/nonleap calendar cases are algorithm checks, not observed events.',
            'Existing wind energy bias, asset lineage, PV amplitude and held-out physical validation remain open.',
            'Hourly ERA5 accumulation semantics assumed established; no forecast or ERA5-Land deaccumulation inferred.',
            'Calendar core needs endpoint samples and external context; remaining outer event censoring must be retained.'],
        'input_sha256':{'instant_NetCDF':checksum(instant_path),'accum_NetCDF':checksum(accum_path),'mask_NetCDF':checksum(mask_path),
            str(wind_path.relative_to(project)):checksum(wind_path),str(pv_path.relative_to(project)):checksum(pv_path)},
        'artifacts_sha256':{str(path.relative_to(project)):checksum(path) for path in artifacts}}
    (tables/'continuity_metadata_2020_01.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print(pd.DataFrame(weather_checks).to_string(index=False));print(synthetic.to_string(index=False))


if __name__=='__main__':main()
