#!/usr/bin/env python

import sys

import pandas as pd
import geopandas as gpd

grid_in = sys.argv[1]
grid_out = sys.argv[2]

gdf = gpd.read_file(grid_in)
gdf["voltage_fixed"] = pd.to_numeric(gdf.voltage, errors="coerce").fillna(
    0, downcast="infer"
)

gdf.to_file(grid_out, driver="GPKG")
