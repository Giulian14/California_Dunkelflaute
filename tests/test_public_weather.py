"""Reject incompatible secondary weather responses before modeling."""
import importlib.util
from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
spec=importlib.util.spec_from_file_location('public_weather',Path(__file__).resolve().parents[1]/'scripts/20_rehearse_public_weather.py')
weather=importlib.util.module_from_spec(spec);spec.loader.exec_module(weather)


class ResponseTests(unittest.TestCase):
    def response(self):
        return dict(latitude=35.25,longitude=-118.5,utc_offset_seconds=0,
            hourly_units=dict(time='iso8601',wind_speed_100m='m/s',wind_direction_100m='°',
                temperature_2m='°C',shortwave_radiation='W/m²'),
            hourly=dict(time=pd.date_range('2020-01-01',periods=24,freq='h').strftime('%Y-%m-%dT%H:%M').tolist(),
                wind_speed_100m=[5.]*24,wind_direction_100m=[180.]*24,
                temperature_2m=[10.]*24,shortwave_radiation=[0.]*24))

    def validate(self,response):
        return weather.validate_response(response,35.25,-118.5,'2020-01-01','2020-01-01')

    def test_correct_contract_and_missing_values(self):
        self.assertEqual(self.validate(self.response())[1].shape,(24,4))
        response=self.response();response['hourly']['wind_speed_100m'][2]=None
        with self.assertRaises(ValueError):self.validate(response)

    def test_wrong_grid_units_timezone_or_hour_order(self):
        for key,value in [('latitude',35.5),('utc_offset_seconds',3600)]:
            response=self.response();response[key]=value
            with self.assertRaises(ValueError):self.validate(response)
        response=self.response();response['hourly_units']['shortwave_radiation']='J/m²'
        with self.assertRaises(ValueError):self.validate(response)
        response=self.response();response['hourly']['time'][3]=response['hourly']['time'][2]
        with self.assertRaises(ValueError):self.validate(response)


if __name__=='__main__':unittest.main()
