"""Bounded validation requests informed by Li (2021) and Mockert (2023).

Planning never authenticates. Existing January baseline fields are reused;
only missing January fields are requested. No 2005–2024 batch is supported.
"""
import calendar
import hashlib
import json


BASE_VARIABLES = [
    '100m_u_component_of_wind', '100m_v_component_of_wind',
    '2m_temperature', 'surface_solar_radiation_downwards',
]
ADDITIONAL_VARIABLES = [
    '10m_u_component_of_wind', '10m_v_component_of_wind',
    'forecast_surface_roughness', 'surface_net_solar_radiation',
    'toa_incident_solar_radiation', 'total_sky_direct_solar_radiation_at_surface',
]


def request_hash(request):
    return hashlib.sha256(json.dumps(request,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def limited_validation_plan(session_date):
    """Discovery winter, contrasting training season, then untouched energy years.

    Nine UTC hours in each following month cover Pacific month-end support
    (UTC−8 winter / UTC−7 summer). One summer hour is deliberate extra context.
    January 2021 weather at five cells was previously inspected; its matched
    generation has not been used for fitting. Do not call all weather unseen.
    """
    periods=[
        ('winter_2020_01_extra',2020,1,'month','discovery_winter',ADDITIONAL_VARIABLES),
        ('winter_2020_02',2020,2,'month','discovery_winter',BASE_VARIABLES+ADDITIONAL_VARIABLES),
        ('winter_2020_end',2020,3,'boundary','discovery_winter',BASE_VARIABLES+ADDITIONAL_VARIABLES),
        ('summer_2020_07',2020,7,'month','training_summer',BASE_VARIABLES+ADDITIONAL_VARIABLES),
        ('summer_2020_end',2020,8,'boundary','training_summer',BASE_VARIABLES+ADDITIONAL_VARIABLES),
        ('holdout_2021_01',2021,1,'month','validation_winter',BASE_VARIABLES+ADDITIONAL_VARIABLES),
        ('holdout_2021_winter_end',2021,2,'boundary','validation_winter',BASE_VARIABLES+ADDITIONAL_VARIABLES),
        ('holdout_2021_07',2021,7,'month','validation_summer',BASE_VARIABLES+ADDITIONAL_VARIABLES),
        ('holdout_2021_summer_end',2021,8,'boundary','validation_summer',BASE_VARIABLES+ADDITIONAL_VARIABLES),
    ]
    batches=[]
    for name,year,month,kind,stage,variables in periods:
        days=range(1,calendar.monthrange(year,month)[1]+1) if kind=='month' else [1]
        hours=range(24) if kind=='month' else range(9)
        request=dict(product_type=['reanalysis'],year=[str(year)],month=[f'{month:02d}'],
            day=[f'{day:02d}' for day in days],time=[f'{hour:02d}:00' for hour in hours],
            data_format='netcdf',download_format='zip',grid=[.25,.25],area=[42,-125,32,-114],
            variable=list(variables))
        batches.append(dict(batch_id=name,stage=stage,dataset='reanalysis-era5-single-levels',request=request,
            request_sha256=request_hash(request),expected_snapshot_hours=len(days)*len(hours),
            expected_spatial_shape=[41,45],requires_existing_January_baseline=name=='winter_2020_01_extra'))
    return dict(status='PLAN_ONLY_NOT_SUBMITTED',prepared_on=session_date,
        purpose='Limited source-consistent resource-model and matched-generation validation before archive expansion.',
        first_stage='discovery_winter',batches=batches,
        reuse='January 2020 u100/v100/t2m/ssrd remain the preserved existing files; merge supplemental fields only after exact grid/time/version QC.',
        physics='fdir is direct radiation on a horizontal surface, not DNI; diffuse=ssrd−fdir and albedo=(ssrd−ssr)/ssrd need documented guards and interval treatment.',
        calibration='German regression coefficients and fallback factors are not transferable. Fit only with compatible observed CF populations; freeze parameters before 2021 energy validation.',
        scope='No direct-CDS request has been tested or submitted by plan generation; no full-period download supported.')
