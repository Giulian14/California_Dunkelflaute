"""Conservative whole-plant PV inventory matching, without fitting generation."""

import numpy as np
import pandas as pd
import shapely


def monthly_pv(frame):
    selected = frame.loc[frame['Plant State'].eq('CA') & frame.Technology.eq('Solar Photovoltaic')].copy()
    selected['source_excel_row'] = selected.index + 3
    result = selected.rename(columns={'Plant ID':'plant_id', 'Generator ID':'generator_id',
        'Plant Name':'plant_name', 'Nameplate Capacity (MW)':'capacity_mw', 'Status':'status',
        'Latitude':'latitude', 'Longitude':'longitude', 'Operating Year':'operating_year',
        'Operating Month':'operating_month', 'Energy Source Code':'fuel', 'Prime Mover Code':'prime_mover'})
    columns = ['plant_id','generator_id','plant_name','capacity_mw','status','latitude','longitude',
               'operating_year','operating_month','fuel','prime_mover','source_excel_row']
    result = result[columns].copy()
    identifiers=pd.to_numeric(result.plant_id,errors='raise')
    if not (np.isfinite(identifiers)&identifiers.gt(0)&identifiers.eq(np.floor(identifiers))).all():
        raise ValueError('Invalid plant IDs.')
    result['plant_id'] = identifiers.astype(int)
    if result.generator_id.isna().any():
        raise ValueError('Missing generator IDs.')
    result['generator_id'] = result.generator_id.astype(str).str.strip()
    result['status'] = result.status.astype(str).str.extract(r'^\((\w+)\)', expand=False)
    for col in ['capacity_mw','latitude','longitude','operating_year','operating_month']:
        result[col] = pd.to_numeric(result[col], errors='coerce')
    if (result.status.isna().any() or result.generator_id.eq('').any()
            or result.duplicated(['plant_id','generator_id']).any()):
        raise ValueError('Unrecognized status or duplicate PV keys.')
    return result


def match_pv(december, january, annual, generation, boundary):
    """Match all PV units at a plant; annual properties are qualified proxies.

    Missing nonselected technology flags mean not selected on EIA's select-all
    form, not proven absence. Any positive tracking/mixed flag excludes the
    fixed-tilt comparison. No partial-plant energy denominators are permitted.
    """
    keys = ['plant_id','generator_id']
    for frame in [december,january,annual]:
        if frame.duplicated(keys).any():
            raise ValueError('Duplicate generator keys.')
    energy = generation.loc[generation.state.eq('CA') & generation.fuel.eq('SUN')
        & generation.prime_mover.eq('PV') & ~generation.is_state_fuel_increment].copy()
    if energy.plant_id.duplicated().any():
        raise ValueError('Require one PV generation row per physical plant.')
    rows, selected = [], []
    stable_fields = ['status','capacity_mw','operating_year','operating_month','fuel','prime_mover']
    for pid in sorted(set(december.plant_id) | set(january.plant_id) | set(energy.plant_id)):
        dec = december.loc[december.plant_id.eq(pid)].set_index('generator_id').sort_index()
        jan = january.loc[january.plant_id.eq(pid)].set_index('generator_id').sort_index()
        ann = annual.loc[annual.plant_id.eq(pid)].set_index('generator_id').sort_index()
        obs = energy.loc[energy.plant_id.eq(pid)]
        reason = ''
        if jan.empty or not jan.index.equals(dec.index):
            reason = 'monthly_unit_set_changed_or_absent'
        elif not jan[stable_fields].equals(dec[stable_fields]):
            reason = 'monthly_status_capacity_or_service_changed'
        elif not (jan.status.eq('OP') & jan.fuel.eq('SUN') & jan.prime_mover.eq('PV')).all():
            reason = 'not_all_units_operating_PV'
        elif not (jan.capacity_mw.gt(0) & np.isfinite(jan.capacity_mw)
                  & jan.operating_year.between(1900,2019) & jan.operating_month.between(1,12)).all():
            reason = 'invalid_capacity_or_preJanuary_service'
        elif (not np.isfinite(jan[['latitude','longitude']]).all().all()
              or not jan.latitude.between(32,42).all() or not jan.longitude.between(-125,-114).all()
              or jan.latitude.max()-jan.latitude.min()>1e-6 or jan.longitude.max()-jan.longitude.min()>1e-6):
            reason = 'invalid_or_inconsistent_coordinates'
        elif not shapely.intersects_xy(boundary,jan.longitude.iloc[0],jan.latitude.iloc[0]):
            reason = 'outside_saved_boundary'
        elif not jan.index.equals(ann.index):
            reason = 'annual_unit_population_differs'
        elif not np.isclose(jan.capacity_mw.to_numpy(),ann.capacity_mw.to_numpy(),atol=1e-8,rtol=0).all():
            reason = 'annual_AC_capacity_differs'
        elif obs.empty or not np.isfinite(obs.january_net_generation_mwh.iloc[0]):
            reason = 'missing_January_PV_generation'
        stable = not reason
        if stable:
            flags = ['single_axis','dual_axis','east_west','concentrator','other_solar']
            if not ann.fixed_tilt.eq('Y').all() or ann[flags].eq('Y').any().any():
                reason = 'tracking_mixed_or_unclassified_technology'
            elif not (ann.tilt_deg.between(0,90) & ann.azimuth_deg.ge(0) & ann.azimuth_deg.lt(360)
                      & ann.dc_capacity_mw.gt(0) & np.isfinite(ann.dc_capacity_mw)).all():
                reason = 'missing_or_invalid_orientation_or_DC_capacity'
        capacity = float(jan.capacity_mw.sum()) if len(jan) else np.nan
        value = float(obs.january_net_generation_mwh.iloc[0]) if len(obs) else np.nan
        if not reason and not 0 <= value / (capacity*744) <= 1:
            reason = 'observed_nominal_CF_outside_0_1'
        name = jan.plant_name.iloc[0] if len(jan) else (obs.plant_name.iloc[0] if len(obs) else dec.plant_name.iloc[0])
        rows.append(dict(plant_id=int(pid),plant_name=name,
            capacity_mw=capacity,generator_count=len(jan),january_net_generation_mwh=value,
            stable_capacity_matched=stable,selected_fixed_tilt=not reason,exclusion_reason=reason))
        if not reason:
            merged = jan.reset_index().merge(ann.reset_index()[['generator_id','tilt_deg','azimuth_deg',
                'dc_capacity_mw','annual_source_sheet','annual_source_excel_row']],on='generator_id',validate='one_to_one')
            selected.append(merged)
    audit = pd.DataFrame(rows)
    generators = pd.concat(selected,ignore_index=True) if selected else pd.DataFrame()
    return audit, generators
