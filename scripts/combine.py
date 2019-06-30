#!/usr/bin/env python

import os
from pathlib import Path
from argparse import ArgumentParser

import geopandas as gpd

code = "ADM0_A3"


def combine(mvh, mvl, out, admin_in):
    admin = gpd.read_file(admin_in)
    countries = admin[code].tolist()
    for c in countries:
        try:
            print(c)
            access = float(admin.loc[admin[code] == c, "total"])
            r1 = mvh / f"{c}.tif"
            r2 = mvl / f"{c}.tif"
            rout = out / f"{c}.tif"
            if access >= 0.9:
                cmd = f"gdal_translate -a_nodata none {r1} temp1.tif; "
                cmd += f"gdal_translate -a_nodata none {r2} temp2.tif; "
                cmd += f"gdal_calc.py -A temp1.tif -B temp2.tif --calc='(A+B)>=1' --NoDataValue=0 --outfile={rout}"
            else:
                cmd = f"cp {r1} {rout}"
            os.system(cmd)
        except ValueError as e:
            print(f"Failed {c}", e)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("mvh", help="Dir of mv-high rasters")
    parser.add_argument("mvl", help="Dir of mv-low rasters")
    parser.add_argument("out", help="Dir for combined output rasters")
    parser.add_argument("--admin", help="Admin geopackage to use")
    args = parser.parse_args()

    admin = Path("~/energy-infra/data/ne_50m_admin0.gpkg").expanduser()
    if args.admin:
        admin = Path(args.admin)

    combine(mvh=Path(args.mvh), mvl=Path(args.mvl), out=Path(args.out), admin_in=admin)
