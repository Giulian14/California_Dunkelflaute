"""Plan limited validation, or explicitly download ONE selected batch locally.

Without --download this never imports cdsapi or authenticates. Credentials
are read by the official client from its private configuration, not arguments.
"""
import argparse
from datetime import date,datetime,timezone
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import zipfile

from archive_preflight import verified_receipt
from validation_download import limited_validation_plan


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session-date',type=date.fromisoformat,default=date.today())
    parser.add_argument('--plan-output',type=Path)
    parser.add_argument('--batch')
    parser.add_argument('--download',action='store_true')
    parser.add_argument('--output-dir',type=Path,
        default=Path(__file__).resolve().parents[1]/'data/raw/validation')
    args=parser.parse_args()
    plan=limited_validation_plan(str(args.session_date))
    if args.plan_output:
        args.plan_output.parent.mkdir(parents=True,exist_ok=True)
        args.plan_output.write_text(json.dumps(plan,indent=2)+'\n')
    selected=[batch for batch in plan['batches'] if batch['batch_id']==args.batch] if args.batch else []
    if args.batch and len(selected)!=1:
        parser.error('Unknown batch. Run without --batch to list the supported validation batches.')
    if not args.download:
        print('PLAN ONLY — NO DOWNLOAD OR AUTHENTICATION')
        for batch in selected or plan['batches']:
            print(batch['batch_id'],batch['stage'],batch['expected_snapshot_hours'],'snapshots',
                  len(batch['request']['variable']),'variables')
        if selected:
            print(json.dumps(selected[0]['request'],indent=2))
        return
    if not selected:
        parser.error('--download requires one explicit --batch; no all-batch download is implemented.')
    batch=selected[0]
    args.output_dir.mkdir(parents=True,exist_ok=True)
    target=args.output_dir/(batch['batch_id']+'.zip')
    receipt=target.with_suffix('.receipt.json')
    if verified_receipt(target,receipt,batch['request']):
        print('Verified completed download reused:',target)
        return
    partial=target.with_suffix('.zip.partial')
    if target.exists() or receipt.exists() or partial.exists():
        raise FileExistsError('Unverified or partial output exists; inspect it before retrying. Existing files were not overwritten.')
    import cdsapi
    client=cdsapi.Client()
    client.retrieve(batch['dataset'],batch['request'],str(partial))
    if not zipfile.is_zipfile(partial):
        raise ValueError('Expected requested ZIP archive. Retained partial file for inspection; no completion receipt written.')
    with zipfile.ZipFile(partial) as archive:
        members=archive.namelist()
        if not any(name.endswith('.nc') for name in members) or archive.testzip() is not None:
            raise ValueError('Expected intact NetCDF members in ZIP; no completion receipt written.')
    digest=hashlib.sha256(partial.read_bytes()).hexdigest()
    partial.replace(target)
    record=dict(status='download_complete',batch_id=batch['batch_id'],dataset=batch['dataset'],
        request=batch['request'],request_sha256=batch['request_sha256'],sha256=digest,
        bytes=target.stat().st_size,retrieved_at_utc=datetime.now(timezone.utc).isoformat(),
        cdsapi=version('cdsapi'),netcdf_qc='NOT_YET_RUN',members=members)
    temporary=receipt.with_suffix('.json.partial')
    temporary.write_text(json.dumps(record,indent=2)+'\n');temporary.replace(receipt)
    print('Downloaded one batch:',target)
    print('Archive integrity checked. Scientific grid/time/units/version QC and merging remain required.')


if __name__=='__main__':main()
