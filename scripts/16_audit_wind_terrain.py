"""Compare wind-grid terrain with independently sourced DEM point elevations."""

import argparse
import hashlib
import json
from pathlib import Path
import platform
import shutil

import numpy as np
import pandas as pd

from terrain_reference import decode_single_chunk, exact_grid_values, usgs_elevation


def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir',type=Path,required=True)
    parser.add_argument('--project-dir',type=Path,default=Path(__file__).resolve().parent.parent)
    parser.add_argument('--headless',action='store_true')
    args=parser.parse_args();project=args.project_dir.resolve();source=args.source_dir.resolve()
    reference=project/'data/reference/terrain';reference.mkdir(parents=True,exist_ok=True)
    tables,figures=project/'results/tables',project/'results/figures'
    manifest=json.loads((source/'source_manifest.json').read_text())
    if checksum(source/'.zmetadata')!=manifest['zmetadata_sha256']:
        raise ValueError('Static metadata checksum mismatch.')
    if checksum(source/'LICENSE_COPERNICUS.txt')!=manifest['license_sha256']:
        raise ValueError('Source license checksum mismatch.')
    metadata=json.loads((source/'.zmetadata').read_text())['metadata']
    arrays={}
    for entry in manifest['chunks']:
        path=source/entry['relative_path']
        if checksum(path)!=entry['sha256']:raise ValueError('Static chunk checksum mismatch.')
        name=entry['relative_path'].split('/')[0]
        arrays[name]=decode_single_chunk(path.read_bytes(),metadata[name+'/.zarray'])
    required={'latitude','longitude','geopotential_at_surface','standard_deviation_of_orography','land_sea_mask'}
    if set(arrays)!=required:raise ValueError('Unexpected set of static fields.')
    for field,units in [('geopotential_at_surface','m**2 s**-2'),('standard_deviation_of_orography','m')]:
        if metadata[field+'/.zattrs']['units']!=units:raise ValueError('Unexpected static units.')
        if metadata[field+'/.zattrs']['_ARRAY_DIMENSIONS']!=['latitude','longitude']:
            raise ValueError('Unexpected static axis ordering.')
    plants_path=project/'data/reference/jan2020_wind_capacity_consistent_plants.csv'
    coordinates_path=tables/'wind_site_coordinate_audit_2020_01.csv'
    diagnostic_path=tables/'wind_site_iec2_diagnostics_2020_01.csv'
    prior_metadata_path=tables/'wind_site_diagnostic_metadata_2020_01.json'
    prior=json.loads(prior_metadata_path.read_text())
    for path in [plants_path,coordinates_path,diagnostic_path]:
        if checksum(path)!=prior['artifacts_sha256'][str(path.relative_to(project))]:
            raise ValueError('Prior site artifact checksum mismatch.')
    plants=pd.read_csv(plants_path)
    coordinates=pd.read_csv(coordinates_path)
    sites=plants.merge(coordinates[['plant_id','nearest_latitude','nearest_longitude','nearest_distance_km']],on='plant_id',validate='one_to_one')
    diagnostic=pd.read_csv(diagnostic_path);diagnostic=diagnostic.loc[diagnostic.sampling.eq('nearest')]
    sites=sites.merge(diagnostic[['plant_id','monthly_cf_upper_bound','observed_minus_model_upper_mwh']],on='plant_id',validate='one_to_one')
    sites['observed_minus_model_upper_cf']=sites.observed_monthly_cf_nominal-sites.monthly_cf_upper_bound
    for name,column in [('geopotential_at_surface','era5_surface_geopotential_m2_s2'),
                        ('standard_deviation_of_orography','era5_orography_std_m'),('land_sea_mask','era5_land_fraction')]:
        sites[column]=exact_grid_values(arrays[name],arrays['latitude'],arrays['longitude'],sites.nearest_latitude.to_numpy(),sites.nearest_longitude.to_numpy())
    sites['era5_geopotential_height_m']=sites.era5_surface_geopotential_m2_s2/9.80665
    if not sites.era5_land_fraction.between(0,1).all() or not sites.era5_orography_std_m.ge(0).all():
        raise ValueError('Invalid land fraction or orography variability.')
    requests={entry['plant_id']:entry for entry in manifest['USGS_requests']}
    if len(requests)!=len(manifest['USGS_requests']) or set(requests)!=set(plants.plant_id):
        raise ValueError('USGS request population differs from the selected cohort.')
    point_rows=[]
    for plant in sites.itertuples():
        entry=requests[plant.plant_id]
        row={'plant_id':plant.plant_id,'usgs_status':entry['status'],'usgs_elevation_m':None,
             'usgs_raster_id':None,'usgs_resolution_reported':None,'usgs_acquisition_date':None,'usgs_error':entry.get('error','')}
        if entry['status']=='downloaded':
            path=source/entry['relative_path']
            if checksum(path)!=entry['sha256']:raise ValueError('USGS response checksum mismatch.')
            response=json.loads(path.read_text())
            try:
                row['usgs_elevation_m']=usgs_elevation(response,plant.latitude,plant.longitude)
                row['usgs_status']='valid'
                row['usgs_raster_id']=response.get('rasterId')
                row['usgs_resolution_reported']=response.get('resolution')
                row['usgs_acquisition_date']=response.get('attributes',{}).get('AcquisitionDate')
            except (ValueError,KeyError,TypeError) as error:
                row['usgs_status']='invalid_response';row['usgs_error']=str(error)
        point_rows.append(row)
    sites=sites.merge(pd.DataFrame(point_rows),on='plant_id',validate='one_to_one')
    sites['point_minus_grid_height_m']=sites.usgs_elevation_m-sites.era5_geopotential_height_m
    valid=sites.loc[sites.usgs_status.eq('valid')]
    if len(valid)<3:raise ValueError('Insufficient valid point references for a terrain comparison.')
    sites_path=tables/'wind_terrain_site_audit_2020_01.csv';sites.to_csv(sites_path,index=False)
    manifest_path=reference/'source_manifest.json';shutil.copy2(source/'source_manifest.json',manifest_path)
    license_path=reference/'LICENSE_COPERNICUS.txt';shutil.copy2(source/'LICENSE_COPERNICUS.txt',license_path)
    static_metadata_path=reference/'static_field_metadata.json'
    static_metadata={key:value for key,value in metadata.items() if any(key.startswith(name+'/') for name in required)}
    static_metadata_path.write_text(json.dumps(static_metadata,indent=2)+'\n')
    if args.headless:
        import matplotlib
        matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(13,5))
    sizes=12+valid.capacity_mw/5
    points=axes[0].scatter(valid.era5_geopotential_height_m,valid.usgs_elevation_m,c=valid.era5_orography_std_m,s=sizes,cmap='viridis',alpha=.8)
    lower=min(valid.era5_geopotential_height_m.min(),valid.usgs_elevation_m.min())
    upper=max(valid.era5_geopotential_height_m.max(),valid.usgs_elevation_m.max())
    axes[0].plot([lower,upper],[lower,upper],'--',color='gray',linewidth=.8)
    axes[0].set(xlabel='Nearest ERA5 geopotential height (m)',ylabel='USGS DEM point elevation (m)',title='Different spatial support and vertical references')
    axes[1].scatter(valid.point_minus_grid_height_m,valid.observed_minus_model_upper_cf,c=valid.era5_orography_std_m,s=sizes,cmap='viridis',alpha=.8)
    axes[1].axhline(0,color='gray',linestyle='--',linewidth=.8)
    axes[1].set(xlabel='Point minus grid height (m)',ylabel='Observed CF minus IEC II model upper bound',title='Exploratory association; no causal or significance claim')
    for ax in axes:ax.grid(alpha=.2)
    fig.subplots_adjust(bottom=.25,right=.85,wspace=.36,top=.87)
    color_axis=fig.add_axes([.89,.25,.015,.62])
    fig.colorbar(points,cax=color_axis,label='ERA5 orography standard deviation (m)')
    fig.suptitle('January wind sites — terrain-reference diagnostic',y=.97,va='top',fontsize=13)
    fig.text(.5,.09,'Contains modified Copernicus Climate Change Service information (2026); USGS 3DEP/EPQS.',ha='center',fontsize=8)
    fig.text(.5,.05,'Neither the European Commission nor ECMWF is responsible for use of the Copernicus information or data.',ha='center',fontsize=8)
    fig.text(.5,.015,'Point markers share weather cells; elevations are not surveyed turbine positions or a wind correction.',ha='center',fontsize=8)
    figure_path=figures/'wind_terrain_comparison_2020_01.png';fig.savefig(figure_path,dpi=180);plt.close(fig)
    unique_centers=sites[['nearest_latitude','nearest_longitude']].drop_duplicates()
    summary={'plants':len(sites),'unique_weather_centers':len(unique_centers),'valid_USGS_points':len(valid),
        'point_status_counts':sites.usgs_status.value_counts().to_dict(),
        'median_point_minus_grid_height_m':float(valid.point_minus_grid_height_m.median()),
        'median_absolute_point_grid_height_difference_m':float(valid.point_minus_grid_height_m.abs().median()),
        'minimum_point_minus_grid_height_m':float(valid.point_minus_grid_height_m.min()),
        'maximum_point_minus_grid_height_m':float(valid.point_minus_grid_height_m.max()),
        'minimum_orography_std_m':float(sites.era5_orography_std_m.min()),'maximum_orography_std_m':float(sites.era5_orography_std_m.max())}
    output={'status':'Terrain context and approximate point/grid differences; not wind bias attribution or calibration',
        'python':platform.python_version(),'retrieved_on':manifest['retrieved_on'],'summary':summary,
        'geopotential_height_conversion':'ERA5 z / 9.80665 m s-2; geopotential height, not exact geometric/orthometric datum conversion',
        'point_reference':'USGS EPQS interpolated 3DEP DEM at EIA plant coordinates; request EPSG:4326 and Meters; raster/acquisition fields retained',
        'vertical_and_spatial_limits':'Point DEM elevations and grid-scale geopotential heights have different support and vertical definitions; EIA plant points are not surveyed turbine locations.',
        'statistical_limits':'Plants share ERA5 cells; no independent-sample p-value, fitted terrain correction or causal attribution.',
        'wind_validation':'No independent hub-height wind observations acquired; no wind, PV or event model changed.',
        'attribution':'Contains modified Copernicus Climate Change Service information (2026). Neither the European Commission nor ECMWF is responsible for any use of the Copernicus information or data. USGS 3DEP/EPQS.',
        'source_manifest_sha256':checksum(source/'source_manifest.json'),
        'input_sha256':{str(p.relative_to(project)):checksum(p) for p in [plants_path,coordinates_path,diagnostic_path,prior_metadata_path]},
        'artifacts_sha256':{str(p.relative_to(project)):checksum(p) for p in [sites_path,manifest_path,license_path,static_metadata_path,figure_path]}}
    (tables/'wind_terrain_metadata_2020_01.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
