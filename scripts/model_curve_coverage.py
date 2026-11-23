"""Exact-name candidate availability in one pinned archive, not curve validation."""

import pandas as pd


CANDIDATES={
    ('Vestas','V47-660'):('Onshore','VestasV47_660kW_47'),
    ('Vestas','V27-225'):('Distributed','VestasV27_225kW_27'),
}


def curve_coverage(generators, paths):
    if generators.duplicated(['plant_id','generator_id']).any() or generators.empty:
        raise ValueError('Require a nonempty, unique generator inventory.')
    table=generators.copy();candidate=[]
    for row in table.itertuples():
        match=CANDIDATES.get((row.reported_manufacturer,row.reported_model))
        if match:
            group,name=match
            csv=f'turbine_models/data/{group}/{name}.csv'
            spec=f'turbine_models/specs/{group}/{name}.yaml'
            if csv not in paths or spec not in paths:raise ValueError('Candidate absent from pinned archive tree.')
            candidate.append(spec)
        else:candidate.append('')
    table['candidate_spec_path']=candidate
    table['has_same_name_candidate']=table.candidate_spec_path.ne('')
    table['whole_plant_has_candidates']=table.groupby('plant_id').has_same_name_candidate.transform('all')
    rows=[];total=table.capacity_mw.sum()
    for (manufacturer,model),group in table.groupby(['reported_manufacturer','reported_model'],dropna=False):
        rows.append({'manufacturer':manufacturer,'reported_model':model,'generators':len(group),
            'plants':group.plant_id.nunique(),'capacity_mw':group.capacity_mw.sum(),
            'share_of_subset_capacity':group.capacity_mw.sum()/total,
            'same_name_candidate':bool(group.has_same_name_candidate.all()),
            'candidate_spec_path':group.candidate_spec_path.iloc[0],
            'status':'Theoretical archive candidate; manufacturer provenance unverified' if group.has_same_name_candidate.all()
                     else 'No exact-name candidate assigned in this archive audit'})
    return table,pd.DataFrame(rows).sort_values('capacity_mw',ascending=False)
