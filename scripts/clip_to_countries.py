#!/usr/bin/env python

"""
Clip a supplied raster to match the admin boundaries supplied,
and then warp it to match another set of rasters.
"""

import sys
from pathlib import Path
from argparse import ArgumentParser

import geopandas as gpd
import rasterio

sys.path.append("gridfinder")
sys.path.append("access-estimator")
from gridfinder import clip_raster, save_raster
from access_estimator.access_rates import make_same_as

def clip_all(raster_in, admin_in, raster_shape_dir, dir_out, code="ADM0_A3"):
    raster_in = Path(raster_in).expanduser()
    admin_in = Path(admin_in).expanduser()
    raster_shape_dir = Path(raster_shape_dir).expanduser()
    dir_out = Path(dir_out).expanduser()

    admin = gpd.read_file(admin_in)
    countries = admin[code].tolist()

    for c in countries:
        print(f"Doing {c}")
        c_out = dir_out / f"{c}.tif"

        aoi = admin[admin[code] == c]
        arr, aff, crs = clip_raster(raster_in, aoi)

        targets_in = raster_shape_dir / f"{c}.tif"
        targets_rd = rasterio.open(targets_in)
        dest_arr_like = targets_rd.read(1)
        dest_affine = targets_rd.transform
        dest_crs = targets_rd.crs

        new_arr = make_same_as(arr, aff, crs, dest_arr_like, dest_affine, dest_crs)

        save_raster(c_out, new_arr, dest_affine, dest_crs)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("raster_in")
    parser.add_argument("admin_in")
    parser.add_argument("raster_shape_dir")
    parser.add_argument("dir_out")
    parser.add_argument("--code", default="ADM0_A3")
    args = parser.parse_args()

    clip_all(raster_in=args.raster_in,
            admin_in=args.admin_in,
            raster_shape_dir=args.raster_shape_dir,
             dir_out=args.dir_out,
             code=args.code)
