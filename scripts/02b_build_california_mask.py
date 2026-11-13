#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Nov 12 19:47:42 2026

@author: giulianlaudisa
"""

"""Build a California grid-center mask from the saved Census boundary."""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import shapely
import xarray as xr
from shapely.geometry import shape


PROJECT_DIR = Path(__file__).resolve().parent.parent


def main():
    boundary_path = (
        PROJECT_DIR / "data/boundaries/california_census_2026.geojson"
    )
    with boundary_path.open(encoding="utf-8") as file:
        boundary = json.load(file)

    california = shape(boundary["features"][0]["geometry"])
    if not california.is_valid:
        raise ValueError("The saved California boundary is invalid.")

    with xr.open_dataset(
        PROJECT_DIR / "data/raw/data_stream-oper_stepType-instant.nc",
        engine="netcdf4",
    ) as ds:
        longitude = ds["longitude"].load()
        latitude = ds["latitude"].load()

    lon_grid, lat_grid = np.meshgrid(
        longitude.values, latitude.values
    )
    inside = shapely.intersects_xy(
        california, lon_grid, lat_grid
    )

    mask = xr.DataArray(
        inside.astype("int8"),
        coords={"latitude": latitude, "longitude": longitude},
        dims=("latitude", "longitude"),
        name="california_mask",
        attrs={
            "long_name": "California administrative boundary grid-center mask",
            "description": "1 = inside or on boundary; 0 = outside",
            "boundary_source": "U.S. Census Bureau TIGERweb, 2026 vintage",
            "boundary_file": boundary_path.name,
            "note": "Includes state waters; not a land-only mask",
        },
    )

    processed_dir = PROJECT_DIR / "data/processed"
    figure_dir = PROJECT_DIR / "results/figures"
    processed_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)

    mask_path = processed_dir / "california_mask.nc"
    mask.to_netcdf(mask_path, engine="netcdf4")

    fig, ax = plt.subplots(figsize=(7, 8))
    ax.scatter(
        lon_grid, lat_grid, color="lightgray",
        s=8, label="All grid centers",
    )
    ax.scatter(
        lon_grid[inside], lat_grid[inside],
        color="tab:blue", s=10, label="Selected grid centers",
    )

    polygons = (
        list(california.geoms)
        if california.geom_type == "MultiPolygon"
        else [california]
    )
    for polygon in polygons:
        x, y = polygon.exterior.xy
        ax.plot(x, y, color="black", linewidth=0.8)

    ax.set_aspect(1 / np.cos(np.deg2rad(37)))
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title("California boundary and ERA5 grid centers")
    ax.legend()
    fig.tight_layout()

    map_path = figure_dir / "california_era5_grid_mask.png"
    fig.savefig(map_path, dpi=300, bbox_inches="tight")

    print("Selected grid centers:", int(mask.sum().item()))
    print("Mask saved to:", mask_path)
    print("Map saved to:", map_path)
    plt.show()


if __name__ == "__main__":
    main()