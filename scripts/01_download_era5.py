#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Nov 10 11:36:37 2026

@author: giulianlaudisa
"""

# California Dunkelflaute Project
# Download ERA5 meteorological data
# January 2020 test dataset

import cdsapi
from pathlib import Path

# Define the output folder
output_dir = Path(
    "/Users/giulianlaudisa/Documents/Hopkins Fall 2026/"
    "Energy Meteorology/California_Dunkelflaute/data/raw"
)

output_dir.mkdir(parents=True, exist_ok=True)

# Connect to Copernicus
client = cdsapi.Client()

# ERA5 dataset
dataset = "reanalysis-era5-single-levels"

# Request January 2020 data for California
request = {
    "product_type": ["reanalysis"],
    "year": ["2020"],
    "month": ["01"],
    "day": [f"{d:02d}" for d in range(1, 32)],
    "time": [f"{h:02d}:00" for h in range(24)],
    "data_format": "netcdf",
    "download_format": "unarchived",
    "variable": [
        "100m_u_component_of_wind",
        "100m_v_component_of_wind",
        "2m_temperature",
        "surface_solar_radiation_downwards"
    ],
    "area": [42, -125, 32, -114]
}

# Save the downloaded data
output_file = output_dir / "era5_ca_2020_01.nc"

client.retrieve(dataset, request, str(output_file))

print("ERA5 download completed successfully!")
print("Saved to:", output_file)