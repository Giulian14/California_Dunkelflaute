from pathlib import Path
import sys
import unittest
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from model_curve_coverage import curve_coverage


class CoverageTests(unittest.TestCase):
    def frame(self):
        return pd.DataFrame({'plant_id':[1,1,2],'generator_id':['A','B','C'],'capacity_mw':[10.,20.,30.],
            'reported_manufacturer':['Vestas','Vestas','GE'],'reported_model':['V47-660','V90-3.0','1.5 SLE']})
    def paths(self):
        return {'turbine_models/data/Onshore/VestasV47_660kW_47.csv','turbine_models/specs/Onshore/VestasV47_660kW_47.yaml'}
    def test_exact_candidate_does_not_cover_mixed_plant(self):
        details,summary=curve_coverage(self.frame(),self.paths())
        self.assertEqual(details.has_same_name_candidate.tolist(),[True,False,False])
        self.assertFalse(details.whole_plant_has_candidates.any())
        self.assertAlmostEqual(summary.loc[summary.same_name_candidate,'capacity_mw'].sum(),10.)
    def test_different_models_not_conflated_by_rating(self):
        frame=self.frame();frame.reported_model=['V90-1.8','V90-3.0','1.5-77']
        details,_=curve_coverage(frame,set());self.assertFalse(details.has_same_name_candidate.any())
    def test_missing_candidate_source_rejected(self):
        with self.assertRaises(ValueError):curve_coverage(self.frame(),set())


if __name__=='__main__':unittest.main()
