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

script_dir = Path(os.path.dirname(__file__))
with open(script_dir / "config.yml", "r") as ymlfile:
    cfg = yaml.safe_load(ymlfile)

sys.path.append(str(Path(cfg["libraries"]["gridfinder"]).expanduser()))
sys.path.append(str(Path(cfg["libraries"]["access"]).expanduser()))

from access_estimator import *
from gridfinder import *

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


def spawn(tool, countries):
    if countries is None:
        countries = admin[code].tolist()

    p = Pool(processes=threads)
    p.map(tool, countries)


def targets(country):
    log = "targets.txt"

    # Setup
    this_scratch = scratch / f"targets_{country}"
    ntl_out = this_scratch / "ntl"
    ntl_merged_out = this_scratch / "ntl_merged.tif"
    ntl_thresh_out = this_scratch / "ntl_thresh.tif"
    targets_out = data / targets_dir / f"{country}.tif"

    if not targets_out.is_file():
        try:
            print("Targets start", country)
            this_scratch.mkdir(parents=True, exist_ok=True)
            aoi = admin.loc[admin[code] == country]
            buff = aoi.copy()
            buff.geometry = buff.buffer(0.1)

            # Clip NTL rasters and calculate nth percentile values
            clip_rasters(ntl_in, ntl_out, buff)
            if debug:
                print("Rasters clipped")
            raster_merged, affine = merge_rasters(ntl_out, percentile=percentile)
            if debug:
                print("Merged")
            save_raster(ntl_merged_out, raster_merged, affine)
            if debug:
                print("Saved")

            # Apply filter to NTL
            ntl_filter = create_filter()
            ntl_thresh, affine = prepare_ntl(
                ntl_merged_out,
                buff,
                ntl_filter=ntl_filter,
                upsample_by=1,
                threshold=ntl_threshold,
            )
            if debug:
                print("Prepared")
            save_raster(ntl_thresh_out, ntl_thresh, affine)
            if debug:
                print("Saved")

            # Clip to actual AOI
            targets, affine, _ = clip_raster(ntl_thresh_out, aoi)
            if debug:
                print("Clipped again")
            save_raster(targets_out, targets, affine)

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
    targets_in = data / targets_dir / f"{country}.tif"
    costs_in = data / "costs_vec" / f"{country}.gpkg"
    costs_out = data / costs_dir / f"{country}.tif"

    if targets_in.is_file() and costs_in.is_file() and not costs_out.is_file():
        try:
            print("Costs start", country)
            aoi = admin.loc[admin[code] == country]

            roads_raster, affine = prepare_roads(costs_in, aoi, targets_in)
            save_raster(costs_out, roads_raster, affine)
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
    targets_in = data / targets_dir / f"{country}.tif"
    costs_in = data / costs_dir / f"{country}.tif"
    guess_out = data / guess_dir / f"{country}.tif"

    if targets_in.is_file() and costs_in.is_file() and not guess_out.is_file():
        try:
            print("Dijk start", country)
            this_scratch.mkdir(parents=True, exist_ok=True)

            targets, costs, start, affine = get_targets_costs(targets_in, costs_in)
            dist = optimise(targets, costs, start, silent=True)
            save_raster(dist_out, dist, affine)
            guess, affine = threshold(dist_out)
            guess_skel = thin(guess)
            save_raster(guess_out, guess_skel, affine)
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
    guess_in = data / guess_dir / f"{country}.tif"
    guess_vec_out = data / vector_dir / f"{country}.gpkg"

    if guess_in.is_file() and not guess_vec_out.is_file():
        try:
            print("Vec start", country)

            guess_gdf = raster_to_lines(guess_in)
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
    targets_in = data / targets_dir / f"{country}.tif"
    pop_elec_out = data / pop_elec_dir / f"{country}.tif"

    if targets_in.is_file() and not pop_elec_out.is_file():
        try:
            print("Access start", country)

            aoi = admin.loc[admin[code] == country]
            access = aoi[["total", "urban", "rural"]].iloc[0].to_dict()

            pop, urban, ntl, targets, affine, crs = regularise(
                country, aoi, pop_in, urban_in, ntl_ann_in, targets_in
            )
            pop_elec, access_model_total = estimate(pop, urban, ntl, targets, access)
            save_raster(pop_elec_out, pop_elec, affine, crs)

            msg = (
                f"{country},real: {access['total']:.2f},model: {access_model_total:.2f}"
            )
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

    pop_elec_in = data / pop_elec_dir / f"{country}.tif"
    lv_out = data / local_dir / f"{country}.tif"

    if pop_elec_in.is_file() and not lv_out.is_file():
        try:
            print("Local start", country)

            pop_elec_rd = rasterio.open(pop_elec_in)
            pop_elec = pop_elec_rd.read(1)
            affine = pop_elec_rd.transform
            crs = pop_elec_rd.crs

            costs = apply_lv_length(pop_elec)
            save_raster(lv_out, costs, affine, crs)

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
