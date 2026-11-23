"""Replay a recorded public-data manifest; reuse caches and reject source drift."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import shutil
from urllib.request import urlopen


def checksum(data):return hashlib.sha256(data).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--offline',action='store_true',help='Verify the existing cache without any network request')
    args=parser.parse_args();manifest=json.loads(args.manifest.read_text());output=args.output_dir.resolve()
    entries=[{'relative_path':'.zmetadata','url':manifest['weatherbench_zarr_base']+'/.zmetadata','sha256':manifest['zmetadata_sha256']},
             {'relative_path':'LICENSE_COPERNICUS.txt','url':manifest['license_url'],'sha256':manifest['license_sha256']},
             *manifest['chunks'],*[entry for entry in manifest['USGS_requests'] if entry['status']=='downloaded']]
    def fetch(entry):
        path=(output/entry['relative_path']).resolve()
        if not path.is_relative_to(output):raise ValueError('Manifest file must stay inside output directory.')
        if path.exists():
            if checksum(path.read_bytes())!=entry['sha256']:raise ValueError(f'Existing source changed: {path.name}; preserve it and use a fresh directory.')
            return 'cached'
        if args.offline:raise ValueError(f'Offline cache missing: {path.name}')
        url=entry['url']
        if entry.get('google_generation'):url+='?generation='+str(entry['google_generation'])
        with urlopen(url,timeout=30) as response:data=response.read()
        if checksum(data)!=entry['sha256']:
            raise ValueError(f'Source bytes changed: {path.name}; record a new source version before regenerating results.')
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        return 'downloaded'
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(fetch,entries))
    output.mkdir(parents=True,exist_ok=True)
    if args.manifest.resolve()!=output/'source_manifest.json':shutil.copy2(args.manifest,output/'source_manifest.json')
    print(json.dumps({'verified_files':len(results),'cached':results.count('cached'),'downloaded':results.count('downloaded'),'offline':args.offline},indent=2))


if __name__=='__main__':main()
