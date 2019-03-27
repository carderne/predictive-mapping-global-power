# runner.py

"""
Script to control running all energy-infra algorithms.
"""

import sys
import argparse
import shutil
from pathlib import Path
from multiprocessing import Pool

import geopandas as gpd

sys.path.append('gridfinder')
sys.path.append('../access-estimator')
from gridfinder import *
from access_estimator import *

data = Path.home() / 'data'
admin_in = Path.home() / 'Code/energy-infra/data' / 'ne_50m_admin0.gpkg'
admin = gpd.read_file(admin_in)

code = 'ADM0_A3'
ntl_in = data / 'ntl'
pop_in = data / 'pop' / 'ghs.tif'
scratch = data / 'scratch'


def spawn(tool):
    countries = admin[code].tolist()

    p = Pool(processes=4)
    p.map(tool, countries)


def targets(country):
    # Setup
    this_scratch = scratch / f'targets_{country}'
    ntl_out = this_scratch / 'ntl'
    ntl_merged_out = this_scratch / 'ntl_merged.tif'
    ntl_thresh_out = this_scratch / 'ntl_thresh.tif'
    targets_out = data / 'targets' / f'{country.tif}'

    if not targets_out.is_file():
        print('Targets start', country)
        this_scratch.mkdir(parents=True, exist_ok=True)
        aoi = admin.loc[admin[code] == country]
        buff = aoi.buffer(0.1)

        # Clip NTL rasters and calculate nth percentile values
        clip_rasters(ntl_in, ntl_out, buff)
        raster_merged, affine = merge_rasters(ntl_out)
        save_raster(ntl_merged_out, raster_merged, affine)

        # Apply filter to NTL
        ntl_filter = create_filter()
        ntl_thresh, affine = prepare_ntl(ntl_merged_out, aoi, ntl_filter=ntl_filter, upsample_by=1)
        save_raster(ntl_thresh_out, ntl_thresh, affine)

        # Clip to actual AOI
        targets, affine, _ = clip_raster(ntl_thresh_out, aoi)
        save_raster(targets_out, targets, affine)

    # Clean up
    shutil.rmtree(this_scratch)
    print('\t\tDone', country)


def costs(country):
    print('costs', country)


def dijk(country):
    print('dijk', country)


def vector(country):
    print('vector', country)


def access(country):
    print('access', country)


def local(country):
    print('local', country)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("tool")
    args = parser.parse_args()

    switch = {
            'targets': targets,
            'costs': costs,
            'dijk': dijk,
            'vector': vector,
            'access': access,
            'local': local
    }

    func = switch.get(args.tool)
    if func is None:
        sys.exit(f"Option {args.tool} not supported")

    spawn(func)
