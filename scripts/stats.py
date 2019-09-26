#!/usr/bin/env python

import numpy as np
import pandas as pd

import rasterio
from rasterio.warp import reproject, Resampling
import geopandas as gpd
from rasterstats import zonal_stats
import click

from gridfinder import clip_raster, save_raster, clip_line_poly

admin_in = "global_countries.gpkg"
targets_in = "targets.tif"
mv_gpkg_in = "mv.gpkg"
mv_tif_in = "mv_thin_clipped.tif"
lv_in = "lv.tif"
ghs_in = "ghs.tif"


admin = gpd.read_file(admin_in)
code = "GID_0"
countries = admin[code].tolist()

def make_same_as(curr_arr, curr_aff, curr_crs, dest_arr_like, dest_affine, dest_crs):
    dest_arr = np.empty_like(dest_arr_like)

    with rasterio.Env():
        reproject(
            source=curr_arr,
            destination=dest_arr,
            src_transform=curr_aff,
            dst_transform=dest_affine,
            src_crs=curr_crs,
            dst_crs=dest_crs,
            resampling=Resampling.nearest,
        )

    return dest_arr


@click.group()
def cli():
    pass


@cli.command()
@click.option("--start", help="Start from this country")
def access(start=None):
    """
    Calculated pop within targets/access locations.

    1. Clip targets to country
    2. Clip GHS to country
    3. Conform to same bounds etc
    4. Raster calc find overlap
    5. Get overlap pop and total pop
    """

    go = False
    if start is None:
        go = True

    for c in countries:
        if c == start:
            go = True
        if not go:
            print(f"Access skip {c}")
            continue
        print(f"Access: {c}")
        country = admin.loc[admin[code] == c]
        targets, targets_aff, targets_crs = clip_raster(targets_in, country)
        ghs, ghs_aff, ghs_crs = clip_raster(ghs_in, country)

        ghs[ghs <= 0] = 0
        tot = np.sum(ghs)

        targets = make_same_as(
            curr_arr=targets,
            curr_aff=targets_aff,
            curr_crs=targets_crs,
            dest_arr_like=ghs,
            dest_affine=ghs_aff,
            dest_crs=ghs_crs,
        )

        ghs[targets != 1] = 0
        acc = np.sum(ghs)
        msg = f"{c},{tot:.0f},{acc:.0f}"
        print(msg)
        with open("access.csv", "a") as f:
            print(msg, file=f)


@cli.command()
@click.option("--start", help="Start from this country")
def near(start=None):
    """
    Calculated pop within 10km of MV lines.

    1. clip mv.gpkg
    2. buffer 10km
    3. clip ghs
    4. do zonal stats
    """

    go = False
    if start is None:
        go = True

    mv = gpd.read_file(mv_gpkg_in)
    for c in countries:
        if c == start:
            go = True
        if not go:
            print(f"Near skip {c}")
            continue
        
        print(f"Near: {c}")
        country = admin.loc[admin[code] == c]
        mv_c = clip_line_poly(mv, country)
        try:
            mv_c = mv_c.geometry.buffer(0.1)
        except AttributeError as e:
            print(e)
            with open("near.csv", "a") as f:
                print(e, file=f)
            continue
        try:
            ghs, ghs_aff, ghs_crs = clip_raster(ghs_in, mv_c)
        except ValueError as e:
            print(e)
            with open("near.csv", "a") as f:
                print(e, file=f)
            continue

        ghs[ghs <= 0] = 0
        tot = np.sum(ghs)

        msg = f"{c},{tot:.0f}"
        print(msg)
        with open("near.csv", "a") as f:
            print(msg, file=f)


@cli.command()
def invest():
    """
    Calculate length of mv lines.

    1. Clip mv.tif to country
    2. zonal stats
    """

    for c in countries:
        print(f"Invest: {c}")
        country = admin.loc[admin[code] == c]
        mv, mv_aff, mv_crs = clip_raster(mv_tif_in, country)

        tot_mv = np.sum(mv)
        msg = f"{c},{tot_mv:.0f}"
        print(msg)
        with open("invest.csv", "a") as f:
            print(msg, file=f)


@cli.command()
def lv():
    """
    Calculated length of LV lines.

    1. clip lv to country
    2. zonal stats
    3. also get area and pop
    """

    for c in countries:
        print(f"LV: {c}")
        country = admin.loc[admin[code] == c]
        try:
            lv, lv_aff, lv_crs = clip_raster(lv_in, country)
        except ValueError as e:
            print(e)
            with open("lv.csv", "a") as f:
                print(e, file=f)
            continue
        tot_lv = np.sum(lv)
        msg = f"{c},{tot_lv:.0f}"
        print(msg)
        with open("lv.csv", "a") as f:
            print(msg, file=f)


if __name__ == "__main__":
    cli()
