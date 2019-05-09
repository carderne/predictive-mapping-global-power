#!/usr/bin/env python

"""
Script to control running all energy-infra algorithms.
"""

import os
import sys
import argparse
import shutil
from pathlib import Path
from multiprocessing import Pool

import numpy as np
import yaml

import geopandas as gpd
import rasterio
import accessestimator as ea
import gridfinder as gf

script_dir = Path(os.path.dirname(__file__))
with open(script_dir / "config.yml", "r") as ymlfile:
    cfg = yaml.safe_load(ymlfile)

admin_in = Path(cfg["inputs"]["admin"]).expanduser()
code = cfg["inputs"]["admin_code"]
ntl_in = Path(cfg["inputs"]["ntl_monthly"]).expanduser()
ntl_ann_in = Path(cfg["inputs"]["ntl_annual"]).expanduser()
pop_in = Path(cfg["inputs"]["pop"]).expanduser()
urban_in = Path(cfg["inputs"]["urban"]).expanduser()
pop_in = Path(cfg["inputs"]["pop"]).expanduser()

data = Path(cfg["outputs"]["base"]).expanduser()
scratch = Path(cfg["outputs"]["scratch"]).expanduser()

targets_dir = cfg["outputs"]["targets"]
costs_dir = cfg["outputs"]["costs"]
guess_dir = cfg["outputs"]["guess"]
vector_dir = cfg["outputs"]["vector"]
pop_elec_dir = cfg["outputs"]["pop_elec"]
local_dir = cfg["outputs"]["local"]

percentile = cfg["options"]["percentile"]
ntl_threshold = cfg["options"]["ntl_threshold"]
threads = cfg["options"]["threads"]
raise_errors = False

admin = gpd.read_file(admin_in)


def get_dirname(tool):
    if tool == targets:
        return targets_dir
    elif tool == costs:
        return costs_dir
    elif tool == dijk:
        return guess_dir
    elif tool == vector:
        return vector_dir
    elif tool == pop_elec:
        return pop_elec_dir
    elif tool == local:
        return local_dir
    else:
        return ValueError(f"{tool} not supported")


def get_filename(dirname, country, ext="tif"):
    return data / dirname / f"{country}.{ext}"


def get_filename_auto(tool, country):
    dirname = get_dirname(tool)
    ext = "tif"
    if tool == vector:
        ext = "gpkg"
    return get_filename(dirname, country, ext)


def spawn(tool, countries):
    if countries is None:
        countries = admin[code].tolist()

    countries[:] = [c for c in countries if not get_filename_auto(tool, c).is_file()]
    print("Will process", len(countries), "countries")

    with Pool(processes=threads) as pool:
        pool.map(tool, countries)


def targets(country):
    this_scratch = scratch / f"targets_{country}"
    ntl_out = this_scratch / "ntl"
    ntl_merged_out = this_scratch / "ntl_merged.tif"
    ntl_thresh_out = this_scratch / "ntl_thresh.tif"
    targets_out = get_filename(targets_dir, country)

    try:
        print(f"Targets\tstart\t{country}")
        this_scratch.mkdir(parents=True, exist_ok=True)
        aoi = admin.loc[admin[code] == country]
        buff = aoi.copy()
        buff.geometry = buff.buffer(0.1)

        # Clip NTL rasters and calculate nth percentile values
        gf.clip_rasters(ntl_in, ntl_out, buff)
        raster_merged, affine = gf.merge_rasters(ntl_out, percentile=percentile)
        gf.save_raster(ntl_merged_out, raster_merged, affine)

        # Apply filter to NTL
        ntl_filter = gf.create_filter()
        ntl_thresh, affine = gf.prepare_ntl(
            ntl_merged_out,
            buff,
            ntl_filter=ntl_filter,
            upsample_by=1,
            threshold=ntl_threshold,
        )
        gf.save_raster(ntl_thresh_out, ntl_thresh, affine)

        # Clip to actual AOI
        targets, affine, _ = gf.clip_raster(ntl_thresh_out, aoi)
        gf.save_raster(targets_out, targets, affine)
        msg = f"Targets\tDONE\t{country}"

    except Exception as e:
        msg = f"Targets\tFAILED\t{country}\t{e}"
        if raise_errors:
            raise
    finally:
        shutil.rmtree(this_scratch)
        print(msg)
        if log:
            with open(log, "a") as f:
                print(msg, file=f)


def costs(country):
    targets_in = get_filename(targets_dir, country)
    costs_in = get_filename("costs_vec", country, ext="gpkg")
    costs_out = get_filename(costs_dir, country)

    try:
        print(f"Costs\tstart\t{country}")
        aoi = admin.loc[admin[code] == country]
        roads_raster, affine = gf.prepare_roads(costs_in, aoi, targets_in)
        gf.save_raster(costs_out, roads_raster, affine, nodata=-1)

        msg = f"Costs\tDONE\t{country}"
    except Exception as e:
        msg = f"Costs\tFAILED\t{country}\t{e}"
        if raise_errors:
            raise
    finally:
        print(msg)
        if log:
            with open(log, "a") as f:
                print(msg, file=f)


def dijk(country):
    this_scratch = scratch / f"dijk_{country}"
    dist_out = this_scratch / "dist.tif"
    targets_in = get_filename(targets_dir, country)
    costs_in = get_filename(costs_dir, country)
    guess_out = get_filename(guess_dir, country)

    try:
        print(f"Dijk\tstart\t{country}")
        this_scratch.mkdir(parents=True, exist_ok=True)

        targets, costs, start, affine = gf.get_targets_costs(targets_in, costs_in)
        dist = gf.optimise(targets, costs, start, silent=True)
        gf.save_raster(dist_out, dist, affine)
        guess, affine = gf.threshold(dist_out)
        guess_skel = gf.thin(guess)
        gf.save_raster(guess_out, guess_skel, affine)

        msg = f"Dijk\tDONE\t{country}"
    except Exception as e:
        msg = f"Dijk\tFAILED\t{country}\t{e}"
        if raise_errors:
            raise
    finally:
        shutil.rmtree(this_scratch)
        print(msg)
        if log:
            with open(log, "a") as f:
                print(msg, file=f)


def vector(country):
    guess_in = get_filename(guess_dir, country)
    guess_vec_out = get_filename(vector_dir, country, ext="gpkg")

    try:
        print(f"Vector\tstart\t{country}")
        guess_gdf = gf.raster_to_lines(guess_in)
        guess_gdf.to_file(guess_vec_out, driver="GPKG")

        msg = f"Vector\tDONE\t{country}"
    except Exception as e:
        msg = f"Vector\tFAILED\t{country}\t{e}"
        if raise_errors:
            raise
    finally:
        print(msg)
        if log:
            with open(log, "a") as f:
                print(msg, file=f)


def pop_elec(country):
    targets_in = get_filename(targets_dir, country)
    pop_elec_out = get_filename(pop_elec_dir, country)
    weight_out = pop_elec_out.split(".")[0] + "_W.tif"

    try:
        print(f"PopElec\tstart\t{country}")
        aoi = admin.loc[admin[code] == country]
        access = aoi[["total", "urban", "rural"]].iloc[0].to_dict()

        pop, urban, ntl, targets, affine, crs = ea.regularise(
            country, aoi, pop_in, urban_in, ntl_ann_in, targets_in
        )
        pop_elec, access_model_total, weights = ea.estimate(
            pop, urban, ntl, targets, access
        )
        gf.save_raster(pop_elec_out, pop_elec, affine, crs)
        gf.save_raster(weight_out, weights, affine, crs)

        msg = f"PopElec\tDONE\t{country}\t\treal: {access['total']:.2f}\tmodel: {access_model_total:.2f}"
    except Exception as e:
        msg = f"PopElec\tFAILED\t{country}\t{e}"
        if raise_errors:
            raise
    finally:
        print(msg)
        if log:
            with open(log, "a") as f:
                print(msg, file=f)


def local(country):
    pop_elec_in = get_filename(pop_elec_dir, country)
    lv_out = get_filename(local_dir, country)

    try:
        print(f"Local\tstart\t{country}")

        pop_elec_rd = rasterio.open(pop_elec_in)
        pop_elec = pop_elec_rd.read(1)
        affine = pop_elec_rd.transform
        crs = pop_elec_rd.crs

        aoi = admin.loc[admin[code] == country]
        access = aoi[["total", "urban", "rural"]].iloc[0].to_dict()
        peak_kw_pp = 0.1
        people_per_hh = 5
        if access["total"] >= 0.95:
            peak_kw_pp = 2
            people_per_hh = 3

        lengths = ea.apply_lv_length(
            pop_elec, peak_kw_pp=peak_kw_pp, people_per_hh=people_per_hh
        )
        gf.save_raster(lv_out, lengths, affine, crs)
        total_length = np.sum(lengths)
        msg = f"Local\tDONE\t{country}\tTot length: {total_length} km"
    except Exception as e:
        msg = f"Local\tFAILED\t{country}\t{e}"
        if raise_errors:
            raise
    finally:
        print(msg)
        if log:
            with open(log, "a") as f:
                print(msg, file=f)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "tool", help="One of targets, cost, dijk, vector, pop_elec, local"
    )
    parser.add_argument("--countries")
    parser.add_argument("--targets_dir", default=targets_dir)
    parser.add_argument("--costs_dir", default=costs_dir)
    parser.add_argument("--guess_dir", default=guess_dir)
    parser.add_argument("--vector_dir", default=vector_dir)
    parser.add_argument("--pop_elec_dir", default=pop_elec_dir)
    parser.add_argument("--local_dir", default=local_dir)
    parser.add_argument("--percentile", default=percentile, type=int)
    parser.add_argument("--ntl_threshold", default=ntl_threshold, type=float)
    parser.add_argument(
        "-r",
        "--raise_errors",
        action="store_true",
        default=False,
        help="Whether to raise errors",
    )
    parser.add_argument(
        "-l",
        "--log",
        default=None,
        help="If supplied, logs will be written to this file",
    )
    args = parser.parse_args()

    switch = {
        "targets": targets,
        "costs": costs,
        "dijk": dijk,
        "vector": vector,
        "pop_elec": pop_elec,
        "local": local,
    }

    func = switch.get(args.tool)
    if func is None:
        sys.exit(f"Option {args.tool} not supported")

    countries = None
    if args.countries:
        if "," in args.countries:
            countries = args.countries.split(",")
        else:
            countries = [args.countries]

    targets_dir = args.targets_dir
    costs_dir = args.costs_dir
    guess_dir = args.guess_dir
    vector_dir = args.vector_dir
    pop_elec_dir = args.pop_elec_dir
    local_dir = args.local_dir
    percentile = args.percentile
    ntl_threshold = args.ntl_threshold
    raise_errors = args.raise_errors
    log = args.log

    spawn(func, countries)
