#!/usr/bin/env python

import sys
from pathlib import Path
from argparse import ArgumentParser

import rasterio
from gridfinder import save_raster


def subtract_rast(rast_in, sub_in, subbed_out):
    rast_rd = rasterio.open(rast_in)
    rast = rast_rd.read(1)
    affine = rast_rd.transform
    crs = rast_rd.crs
    sub = rasterio.open(sub_in).read(1)

    subbed = rast - sub
    subbed[subbed <= 0] = 0
    subbed[subbed > 0] = 1

    subbed = subbed.astype(np.int16)
    save_raster(path=subbed_out, raster=subbed, affine=affine, crs=crs, nodata=0)


def subtract_all(rast_dir, sub_dir, subbed_dir):
    for rast_in in rast_dir.iterdir():
        name = rast_in.name
        sub_in = sub_dir / name
        subbed_out = subbed_dir / name
        if not outfile.is_file():
            subtract_rast(rast_in, sub_in, subbed_out)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("orig", help="Dir of original rasters")
    parser.add_argument("sub", help="Dir of rasters to subtract")
    parser.add_argument("out", help="Dir for subbed output rasters")
    args = parser.parse_args()

    rast_dir = Path(args.orig)
    sub_dir = Path(args.sub)
    subbed_dir = Path(args.out)
    subtract_all(rast_dir, sub_dir, subbed_dir)
