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
import yaml

import geopandas as gpd
import rasterio

script_dir = Path(os.path.dirname(__file__))
with open(script_dir / "config.yml", "r") as ymlfile:
    cfg = yaml.safe_load(ymlfile)

sys.path.append(str(Path(cfg["libraries"]["gridfinder"]).expanduser()))
sys.path.append(str(Path(cfg["libraries"]["access"]).expanduser()))

import access_estimator as ea
import gridfinder as gf

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
debug = False

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
    log = "targets.txt"

    # Setup
    this_scratch = scratch / f"targets_{country}"
    ntl_out = this_scratch / "ntl"
    ntl_merged_out = this_scratch / "ntl_merged.tif"
    ntl_thresh_out = this_scratch / "ntl_thresh.tif"
    targets_out = get_filename(targets_dir, country)

    try:
        print("Targets start", country)
        this_scratch.mkdir(parents=True, exist_ok=True)
        aoi = admin.loc[admin[code] == country]
        buff = aoi.copy()
        buff.geometry = buff.buffer(0.1)

        # Clip NTL rasters and calculate nth percentile values
        gf.clip_rasters(ntl_in, ntl_out, buff)
        if debug:
            print("Rasters clipped")
        raster_merged, affine = gf.merge_rasters(ntl_out, percentile=percentile)
        if debug:
            print("Merged")
        gf.save_raster(ntl_merged_out, raster_merged, affine)
        if debug:
            print("Saved")

        # Apply filter to NTL
        ntl_filter = gf.create_filter()
        ntl_thresh, affine = gf.prepare_ntl(
            ntl_merged_out,
            buff,
            ntl_filter=ntl_filter,
            upsample_by=1,
            threshold=ntl_threshold,
        )
        if debug:
            print("Prepared")
        gf.save_raster(ntl_thresh_out, ntl_thresh, affine)
        if debug:
            print("Saved")

        # Clip to actual AOI
        targets, affine, _ = gf.clip_raster(ntl_thresh_out, aoi)
        if debug:
            print("Clipped again")
        gf.save_raster(targets_out, targets, affine)

        msg = f"Done {country}"
    except Exception as e:
        msg = f"Failed {country} -- {e}"
        if raise_errors:
            raise
    finally:
        # Clean up
        shutil.rmtree(this_scratch)
        print(msg)
        with open(log, "a") as f:
            print(msg, file=f)


def costs(country):
    log = "costs.txt"

    # Setup
    targets_in = get_filename(targets_dir, country)
    costs_in = get_filename("costs_vec", country, ext="gpkg")
    costs_out = get_filename(costs_dir, country)

    try:
        print("Costs start", country)
        aoi = admin.loc[admin[code] == country]

        roads_raster, affine = gf.prepare_roads(costs_in, aoi, targets_in)
        gf.save_raster(costs_out, roads_raster, affine)
        msg = f"Done {country}"
    except Exception as e:
        msg = f"Failed {country} -- {e}"
        if raise_errors:
            raise
    finally:
        # Clean up
        print(msg)
        with open(log, "a") as f:
            print(msg, file=f)


def dijk(country):
    log = "dijk.txt"

    # Setup
    this_scratch = scratch / f"dijk_{country}"
    dist_out = this_scratch / "dist.tif"
    targets_in = get_filename(targets_dir, country)
    costs_in = get_filename(costs_dir, country)
    guess_out = get_filename(guess_dir, country)

    try:
        print("Dijk start", country)
        this_scratch.mkdir(parents=True, exist_ok=True)

        targets, costs, start, affine = gf.get_targets_costs(targets_in, costs_in)
        dist = gf.optimise(targets, costs, start, silent=True)
        gf.save_raster(dist_out, dist, affine)
        guess, affine = gf.threshold(dist_out)
        guess_skel = gf.thin(guess)
        gf.save_raster(guess_out, guess_skel, affine)
        msg = f"Done {country}"
    except Exception as e:
        msg = f"Failed {country} -- {e}"
        if raise_errors:
            raise
    finally:
        # Clean up
        shutil.rmtree(this_scratch)
        print(msg)
        with open(log, "a") as f:
            print(msg, file=f)


def vector(country):
    log = "vector.txt"

    # Setup
    guess_in = get_filename(guess_dir, country)
    guess_vec_out = get_filename(vector_dir, country, ext="gpkg")

    try:
        print("Vec start", country)

        guess_gdf = gf.raster_to_lines(guess_in)
        guess_gdf.to_file(guess_vec_out, driver="GPKG")
        msg = f"Done {country}"
    except Exception as e:
        msg = f"Failed {country} -- {e}"
        if raise_errors:
            raise
    finally:
        # Clean up
        print(msg)
        with open(log, "a") as f:
            print(msg, file=f)


def pop_elec(country):
    log = "access.txt"

    # Setup
    targets_in = get_filename(targets_dir, country)
    pop_elec_out = get_filename(pop_elec_dir, country)

    try:
        print("Access start", country)

        aoi = admin.loc[admin[code] == country]
        access = aoi[["total", "urban", "rural"]].iloc[0].to_dict()

        pop, urban, ntl, targets, affine, crs = ea.regularise(
            country, aoi, pop_in, urban_in, ntl_ann_in, targets_in
        )
        pop_elec, access_model_total = ea.estimate(pop, urban, ntl, targets, access)
        gf.save_raster(pop_elec_out, pop_elec, affine, crs)

        msg = f"{country},real: {access['total']:.2f},model: {access_model_total:.2f}"
    except Exception as e:
        msg = f"Failed {country} -- {e}"
        if raise_errors:
            raise
    finally:
        print(msg)
        with open(log, "a") as f:
            print(msg, file=f)


def local(country):
    log = "local.txt"

    # Setup
    pop_elec_in = get_filename(pop_elec_dir, country)
    lv_out = get_filename(local_dir, country)

    try:
        print("Local start", country)

        pop_elec_rd = rasterio.open(pop_elec_in)
        pop_elec = pop_elec_rd.read(1)
        affine = pop_elec_rd.transform
        crs = pop_elec_rd.crs

        costs = ea.apply_lv_length(pop_elec)
        gf.save_raster(lv_out, costs, affine, crs)

        msg = f"Done {country}"
    except Exception as e:
        msg = f"Failed {country} -- {e}"
        if raise_errors:
            raise
    finally:
        print(msg)
        with open(log, "a") as f:
            print(msg, file=f)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("tool")
    parser.add_argument("--countries")
    parser.add_argument("-r", action="store_true")  # Whether to raise errors
    parser.add_argument("-d", action="store_true")  # Whether to print debug messages
    parser.add_argument("--targets_dir")
    parser.add_argument("--costs_dir")
    parser.add_argument("--guess_dir")
    parser.add_argument("--vector_dir")
    parser.add_argument("--pop_elec_dir")
    parser.add_argument("--local_dir")
    parser.add_argument("--percentile")
    parser.add_argument("--ntl_threshold")
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

    if args.countries:
        if "," in args.countries:
            countries = args.countries.split(",")
        else:
            countries = [args.countries]
    else:
        countries = None

    if args.r:
        raise_errors = True

    if args.d:
        debug = True

    if args.targets_dir:
        targets_dir = args.targets_dir

    if args.costs_dir:
        costs_dir = args.costs_dir

    if args.guess_dir:
        guess_dir = args.guess_dir

    if args.vector_dir:
        vector_dir = args.vector_dir

    if args.pop_elec_dir:
        pop_elec_dir = args.pop_elec_dir

    if args.local_dir:
        local_dir = args.local_dir

    if args.percentile:
        percentile = int(args.percentile)

    if args.ntl_threshold:
        ntl_threshold = float(args.ntl_threshold)

    spawn(func, countries)
