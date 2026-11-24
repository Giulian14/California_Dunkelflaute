"""Write a reviewable request plan and audit the supplied pilot; no downloads."""
import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import xarray as xr
from archive_preflight import acquisition_plan,audit_weather


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--instant',required=True,type=Path)
    parser.add_argument('--accum',required=True,type=Path)
    parser.add_argument('--project-dir',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--session-date',required=True,type=date.fromisoformat)
    args=parser.parse_args();tables=args.project_dir/'results/tables'
    plan=acquisition_plan();(tables/'era5_2005_2024_request_plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    with xr.open_dataset(args.instant) as i,xr.open_dataset(args.accum) as a:
        report=audit_weather(i,a,'2020-01-01T00:00Z','2020-01-31T23:00Z')
    report['source_sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [args.instant,args.accum]}
    report['execution_date']=str(args.session_date)
    (tables/'archive_preflight_january_2020.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f'Plan only: {len(plan["batches"])} requests; original pilot QC {report["status"]}; no requests submitted.')


if __name__=='__main__':main()
