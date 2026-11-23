"""Record conservative turbine-model coverage without substituting similar ratings."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil

import pandas as pd

from model_curve_coverage import CANDIDATES, curve_coverage


def checksum(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive-source-dir',type=Path,required=True)
    parser.add_argument('--project-dir',type=Path,default=Path(__file__).resolve().parent.parent)
    args=parser.parse_args();project=args.project_dir.resolve();source=args.archive_source_dir.resolve()
    tables=project/'results/tables';reference=project/'data/reference/curve_coverage';reference.mkdir(parents=True,exist_ok=True)
    tree_path=source/'turbine_archive_tree.json';tree=json.loads(tree_path.read_text())
    if tree.get('truncated'):raise ValueError('Need complete archive file tree.')
    paths={r['path']:r for r in tree['tree']}
    audit_path=project/'data/reference/jan2020_wind_annual_turbine_audit.csv'
    prior=json.loads((tables/'wind_site_diagnostic_metadata_2020_01.json').read_text())
    if checksum(audit_path)!=prior['artifacts_sha256'][str(audit_path.relative_to(project))]:
        raise ValueError('Annual equipment audit checksum mismatch.')
    generators=pd.read_csv(audit_path);generators=generators.loc[generators.whole_plant_capacity_consistent]
    details,coverage=curve_coverage(generators,paths)
    spec_provenance=[];spec_artifacts=[]
    for group,name in CANDIDATES.values():
        path=source/f'{name}.yaml';blob=paths[f'turbine_models/specs/{group}/{name}.yaml']['sha']
        data=path.read_bytes();git_blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        if git_blob!=blob:raise ValueError('Candidate spec differs from pinned Git blob.')
        text=data.decode()
        if "power_curve_type: 'theoretical'" not in text or 'reference_links: []' not in text:
            raise ValueError('Candidate provenance changed; review its qualification.')
        dest=reference/path.name;shutil.copy2(path,dest);spec_artifacts.append(dest)
        spec_provenance.append({'path':str(dest.relative_to(project)),'sha256':checksum(dest),'upstream_blob_sha':blob,
                                'power_curve_type':'theoretical','linked_primary_references':0})
    license_path=reference/'LICENSE_BSD.txt';shutil.copy2(project/'data/reference/wind_curves/LICENSE.txt',license_path)
    details_path=tables/'turbine_curve_candidate_generators_2020_01.csv';details.to_csv(details_path,index=False)
    coverage_path=tables/'turbine_curve_candidate_coverage_2020_01.csv';coverage.to_csv(coverage_path,index=False)
    source_commit=json.loads((project/'data/reference/wind_curves/manifest.json').read_text())['commit']
    candidate_mw=float(details.loc[details.has_same_name_candidate,'capacity_mw'].sum())
    metadata={'status':'Candidate availability in one pinned archive; no manufacturer-specific curve substituted',
        'source_repository':'https://github.com/NatLabRockies/turbine-models','source_commit':source_commit,
        'archive_tree_sha':tree['sha'],'archive_tree_response_sha256':checksum(tree_path),
        'source_specs':spec_provenance,'subset_generators':len(details),'reported_model_groups':len(coverage),
        'subset_capacity_mw':float(details.capacity_mw.sum()),'same_name_candidate_capacity_mw':candidate_mw,
        'candidate_capacity_share':candidate_mw/float(details.capacity_mw.sum()),
        'whole_plant_candidate_capacity_mw':float(details.loc[details.whole_plant_has_candidates,'capacity_mw'].sum()),
        'manufacturer_provenance_confirmed_capacity_mw_in_this_audit':0,
        'limitations':['Same-name candidates are theoretical and have no linked primary references in the pinned specs.',
            'Similar rating or rotor diameter is not sufficient to map a DOE research model to GE commercial equipment.',
            'No candidate does not mean a documented curve is unavailable elsewhere.',
            'Annual predominant model labels do not prove January per-turbine identity.'],
        'inaccessible_sources':[{'url':'https://www.maine.gov/dacf/lupc/projects/windpower/redington/Documents/Section01_Development_Description/Development_Electric/E_Pro_Reports/Appendix%20A%20V90%20General%20Spec%20950010R1.pdf','status':'HTTP 403; no PDF data used'},
            {'url':'https://report.ndc.gov.tw/ReportFront/PageSystem/reportFileDownload/C09503816/002','status':'HTTP 403; no PDF data used'},
            {'url':'https://www.commissiemer.nl/docs/mer/p29/p2959/2959-022generalspecification.pdf','status':'HTTP 403; no PDF data used'}],
        'input_sha256':{str(audit_path.relative_to(project)):checksum(audit_path)},
        'artifacts_sha256':{str(p.relative_to(project)):checksum(p) for p in [details_path,coverage_path,license_path,*spec_artifacts]}}
    (tables/'turbine_curve_coverage_metadata_2020_01.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print(json.dumps(metadata,indent=2))


if __name__=='__main__':main()
