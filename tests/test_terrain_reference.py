from pathlib import Path
import sys
import unittest

import numpy as np
from numcodecs import Blosc

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from terrain_reference import decode_single_chunk, exact_grid_values, usgs_elevation


class TerrainTests(unittest.TestCase):
    def test_single_chunk_decoding_preserves_values_and_shape(self):
        array=np.arange(6,dtype='<f4').reshape(2,3);codec=Blosc(cname='lz4',clevel=5,shuffle=1)
        spec={'zarr_format':2,'filters':None,'shape':[2,3],'chunks':[2,3],'order':'C','dtype':'<f4','compressor':codec.get_config()}
        np.testing.assert_array_equal(decode_single_chunk(codec.encode(array),spec),array)
        spec['chunks']=[1,3]
        with self.assertRaises(ValueError):decode_single_chunk(codec.encode(array),spec)

    def test_mismatched_decoded_size_rejected(self):
        codec=Blosc();spec={'zarr_format':2,'filters':None,'shape':[2,3],'chunks':[2,3],'order':'C','dtype':'<f4','compressor':codec.get_config()}
        with self.assertRaises(ValueError):decode_single_chunk(codec.encode(np.ones(2,dtype='<f4')),spec)

    def test_negative_longitudes_are_mapped_to_exact_positive_centers(self):
        result=exact_grid_values(np.array([[1.,2.],[3.,4.]]),[36,35],[239,240],[35],[-120])
        self.assertEqual(result.tolist(),[4.])

    def test_no_nearest_substitution_for_mismatched_grid(self):
        with self.assertRaises(ValueError):exact_grid_values(np.ones((2,2)),[36,35],[239,240],[35.1],[-120])

    def response(self):
        return {'location':{'x':-120.,'y':35.,'spatialReference':{'wkid':4326}},'value':'123.4'}

    def test_point_identity_and_finite_elevation(self):
        self.assertEqual(usgs_elevation(self.response(),35,-120),123.4)
        with self.assertRaises(ValueError):usgs_elevation(self.response(),35,-121)

    def test_nodata_rejected_not_treated_as_extreme_terrain(self):
        response=self.response();response['value']='-1000000'
        with self.assertRaises(ValueError):usgs_elevation(response,35,-120)


if __name__=='__main__':unittest.main()
