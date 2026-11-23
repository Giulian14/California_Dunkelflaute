"""Strict decoding and point checks for static terrain references."""

import numpy as np
from numcodecs import get_codec


def decode_single_chunk(raw, spec):
    if (spec.get("zarr_format") != 2 or spec.get("filters") is not None
            or spec.get("shape") != spec.get("chunks") or spec.get("order") != "C"
            or spec.get("dtype") != "<f4" or len(spec["shape"]) not in {1, 2}
            or spec.get("compressor", {}).get("id") != "blosc"):
        raise ValueError("Expected the documented single-chunk float32 Blosc Zarr v2 layout.")
    data = get_codec(spec["compressor"]).decode(raw)
    expected = int(np.prod(spec["shape"])) * np.dtype(spec["dtype"]).itemsize
    if len(data) != expected:
        raise ValueError("Decoded chunk byte count differs from its declared shape.")
    return np.frombuffer(data, dtype=spec["dtype"]).reshape(spec["shape"])


def exact_grid_values(field, latitude, longitude, target_lat, target_lon):
    lat, lon = np.asarray(latitude), np.asarray(longitude)
    y, x = np.asarray(target_lat, dtype=float), np.mod(np.asarray(target_lon, dtype=float), 360)
    if (np.asarray(field).shape != (len(lat),len(lon)) or y.shape != x.shape
            or not np.isfinite(y).all() or not np.isfinite(x).all()
            or len(np.unique(lat)) != len(lat) or len(np.unique(lon)) != len(lon)):
        raise ValueError("Invalid field, point or coordinate layout.")
    iy = np.abs(y[:,None]-lat[None,:]).argmin(axis=1)
    ix = np.abs(x[:,None]-lon[None,:]).argmin(axis=1)
    if not np.allclose(lat[iy], y, rtol=0, atol=1e-6) or not np.allclose(lon[ix],x,rtol=0,atol=1e-6):
        raise ValueError("Static-reference centers must exactly match selected wind-grid centers.")
    result = field[iy,ix].astype(float)
    if not np.isfinite(result).all():
        raise ValueError("Missing static values at selected centers.")
    return result


def usgs_elevation(response, latitude, longitude):
    location = response["location"]
    if (location["spatialReference"].get("wkid") != 4326
            or not np.isclose(location["x"],longitude,rtol=0,atol=1e-7)
            or not np.isclose(location["y"],latitude,rtol=0,atol=1e-7)):
        raise ValueError("USGS response does not match the requested EPSG:4326 point.")
    value = float(response["value"])
    if not np.isfinite(value) or value == -1000000:
        raise ValueError("USGS response contains no usable elevation.")
    return value
