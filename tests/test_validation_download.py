"""Calendar support, January reuse and authentication-free bounded planning."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from validation_download import BASE_VARIABLES,ADDITIONAL_VARIABLES,limited_validation_plan,request_hash


class ValidationPlanTests(unittest.TestCase):
    def test_existing_January_base_not_requested_again(self):
        plan=limited_validation_plan('2026-11-25');first=plan['batches'][0]
        self.assertEqual(first['expected_snapshot_hours'],744)
        self.assertEqual(first['request']['variable'],ADDITIONAL_VARIABLES)
        self.assertFalse(set(BASE_VARIABLES)&set(first['request']['variable']))
        self.assertTrue(first['requires_existing_January_baseline'])

    def test_leap_month_boundary_and_nonoverlapping_stages(self):
        plan=limited_validation_plan('2026-11-25');self.assertEqual(len(plan['batches']),9)
        winter=[b for b in plan['batches'] if b['stage']=='discovery_winter']
        self.assertEqual(sum(b['expected_snapshot_hours'] for b in winter),1449)
        self.assertEqual(len(winter[1]['request']['day']),29)
        final=winter[2]['request'];self.assertEqual(final['month'],['03'])
        self.assertEqual(final['day'],['01']);self.assertEqual(final['time'][-1],'08:00')
        for b in plan['batches']:
            self.assertEqual(request_hash(b['request']),b['request_sha256'])
            year=int(b['request']['year'][0]);self.assertEqual(year,2021 if b['stage'].startswith('validation') else 2020)

    def test_no_download_default_creates_only_requested_plan(self):
        script=Path(__file__).resolve().parents[1]/'scripts/23_download_validation_batch.py'
        with tempfile.TemporaryDirectory() as directory:
            plan=Path(directory)/'plan.json';data=Path(directory)/'raw'
            result=subprocess.run([sys.executable,str(script),'--session-date','2026-11-25',
                '--plan-output',str(plan),'--output-dir',str(data)],capture_output=True,text=True,check=True)
            self.assertIn('NO DOWNLOAD OR AUTHENTICATION',result.stdout)
            self.assertFalse(data.exists());self.assertEqual(json.loads(plan.read_text())['status'],'PLAN_ONLY_NOT_SUBMITTED')

    def test_all_batch_download_rejected_before_output_or_authentication(self):
        script=Path(__file__).resolve().parents[1]/'scripts/23_download_validation_batch.py'
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'raw'
            result=subprocess.run([sys.executable,str(script),'--download','--output-dir',str(output)],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0);self.assertIn('one explicit --batch',result.stderr)
            self.assertFalse(output.exists())


if __name__=='__main__':unittest.main()
