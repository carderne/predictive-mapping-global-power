# runner.py

"""
Script to control running all energy-infra algorithms.
"""

import sys
import argparse
import shutil
from pathlib import Path
from multiprocessing import Pool

import pandas as pd
import geopandas as gpd

sys.path.append('gridfinder')
sys.path.append('access-estimator')
from gridfinder import *
from access_estimator import *

data = Path('data')
code = 'ADM0_A3'
admin_in = data / 'admin' / 'ne_50m_admin0.gpkg'
ntl_in = data / 'ntl' / 'monthly'
pop_in = data / 'pop' / 'ghs.tif'
urban_in = data / 'pop' / 'urb.tif'
access_in = data / 'pop' / 'countries.csv'
ntl_ann_in = data / 'ntl' / 'annual' / 'world.tif'

admin = gpd.read_file(admin_in)
access_rates = pd.read_csv(access_in)
scratch = data / 'scratch'

exclude = ['KIR', 'FJI', 'ATC', 'PCN', 'HMD', 'SGS', 'KAS', 'ATF']


def spawn(tool, country):
    if country is not None:
        countries = [country]
    else:
        countries = admin[code].tolist()
        countries = list(set(countries) - set(exclude))

    p = Pool(processes=32)
    p.map(tool, countries)


def targets(country):
    log = 'targets.txt'

    # Setup
    this_scratch = scratch / f'targets_{country}'
    ntl_out = this_scratch / 'ntl'
    ntl_merged_out = this_scratch / 'ntl_merged.tif'
    ntl_thresh_out = this_scratch / 'ntl_thresh.tif'
    targets_out = data / 'targets' / f'{country}.tif'

    if not targets_out.is_file():
        try:
            print('Targets start', country)
            this_scratch.mkdir(parents=True, exist_ok=True)
            aoi = admin.loc[admin[code] == country]
            buff = aoi.copy()
            buff.geometry = buff.buffer(0.1)

            # Clip NTL rasters and calculate nth percentile values
            clip_rasters(ntl_in, ntl_out, buff)
            raster_merged, affine = merge_rasters(ntl_out)
            save_raster(ntl_merged_out, raster_merged, affine)

            # Apply filter to NTL
            ntl_filter = create_filter()
            ntl_thresh, affine = prepare_ntl(ntl_merged_out, buff, ntl_filter=ntl_filter, upsample_by=1)
            save_raster(ntl_thresh_out, ntl_thresh, affine)

            # Clip to actual AOI
            targets, affine, _ = clip_raster(ntl_thresh_out, aoi)
            save_raster(targets_out, targets, affine)

            msg = f'Done {country}'
        except Exception as e:
            msg = f'Failed {country} -- {e}'
        finally:
            # Clean up
            shutil.rmtree(this_scratch)
            print(msg)
            with open(log, 'a') as f:
                print(msg, file=f)


def costs(country):
    log = "costs.txt"
    
    # Setup
    targets_in = data / "targets" / f"{country}.tif"
    costs_in = data / "costs_vec" / f"{country}.gpkg"
    costs_out = data / "costs" / f"{country}.tif"

    if targets_in.is_file() and costs_in.is_file() and not costs_out.is_file():
        try:
            print("Costs start", country)
            aoi = admin.loc[admin[code] == country]

            roads_raster, affine = prepare_roads(costs_in, aoi, targets_in)
            save_raster(costs_out, roads_raster, affine)
            msg = f"Done {country}"
        except Exception as e:
            msg = f"Failed {country} -- {e}"
        finally:
            # Clean up
            print(msg)
            with open(log, 'a') as f:
                print(msg, file=f)


def dijk(country):
    log = 'dijk.txt'

    # Setup
    this_scratch = scratch / f"dijk_{country}"
    dist_out = this_scratch / 'dist.tif'
    targets_in = data / "targets" / f"{country}.tif"
    costs_in = data / "costs" / f"{country}.tif"
    guess_out = data / "guess" / f"{country}.tif"

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
        finally:
            # Clean up
            shutil.rmtree(this_scratch)
            print(msg)
            with open(log, 'a') as f:
                print(msg, file=f)


def vector(country):
    log = "vector.txt"

    # Setup
    guess_in = data / "guess" / f"{country}.tif"
    guess_vec_out = data / "guess_vec" / f"{country}.gpkg"

    if guess_in.is_file() and not guess_vec_out.is_file():
        try:
            print("Vec start", country)

            guess_gdf = raster_to_lines(guess_in)
            guess_gdf.to_file(guess_vec_out, driver='GPKG')
            msg = f"Done {country}"
        except Exception as e:
            msg = f"Failed {country} -- {e}"
        finally:
            # Clean up
            print(msg)
            with open(log, "a") as f:
                print(msg, file=f)


def pop_elec(country):
    log = "access.txt"

    # Setup
    targets_in = data / "targets" / f"{country}.tif"
    pop_elec_out = data / "pop_elec" / f"{country}.tif"

    if targets_in.is_file() and not pop_elec_out.is_file():
        try:
            print("Access start", country)
            
            access = access_rates.loc[access_rates[code] == country][["total", "urban", "rural"]].iloc[0].to_dict()
            aoi = admin.loc[admin[code] == country]
            
            pop, urban, ntl, targets, affine, crs = regularise(country, aoi, pop_in, urban_in, ntl_ann_in, targets_in)
            pop_elec, access_model_total = estimate(pop, urban, ntl, targets, access)
            save_raster(pop_elec_out, pop_elec, affine, crs)
            
            msg = f"{country},real: {access['total']:.2f},model: {access_model_total:.2f}"
        except Exception as e:
            msg = f"Failed {country} -- {e}"
        finally:
            print(msg)
            with open(log, "a") as f:
                print(msg, file=f)


def local(country):
    log = "local.txt"

    pop_elec_in = data / "pop_elec" / f"{country}.tif"
    lv_out = data / "lv" / f"{country}.tif"

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
        finally:
            print(msg)
            with open(log, "a") as f:
                print(msg, file=f)
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("tool")
    parser.add_argument("--country")
    args = parser.parse_args()

    switch = {
            'targets': targets,
            'costs': costs,
            'dijk': dijk,
            'vector': vector,
            'pop_elec': pop_elec,
            'local': local
    }

    func = switch.get(args.tool)
    if func is None:
        sys.exit(f"Option {args.tool} not supported")

    spawn(func, args.country)
