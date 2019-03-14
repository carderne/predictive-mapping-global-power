from pathlib import Path

import geopandas as gpd
import pandas as pd
import rasterio

from gridfinder._util import save_raster, clip_raster
from lv_length import apply

# Set file paths and clip AOI
data = Path('data')
log = 'local.txt'

aoi_in = data / 'admin' / 'combined.gpkg'

aoi_all = gpd.read_file(aoi_in)
countries = aoi_all['code'].tolist()
only = ['Canada', 'Russia', 'United_States_of_America']
for c in countries:
    country = c.replace(' ', '_')

    aoi = aoi_all.loc[aoi_all['code'] == c]
    official = aoi['official'].tolist()[0]

    pop_elec_in = data / 'pop_elec' / f'{official}.tif'
    costs_out = data / 'lv' / f'{country}.tif'
    
    if pop_elec_in.is_file() and not costs_out.is_file() and official in only:
        try:
            print(f'{country}')

            
            #pop_elec_rd = rasterio.open(pop_elec_in)
            #pop_elec = pop_elec_rd.read(1)

            clipped, affine, crs = clip_raster(pop_elec_in, aoi)
            if len(clipped.shape) >= 3: clipped = clipped[0]
            costs = apply(clipped)
            save_raster(costs_out, costs, affine, crs)
            print(f'\t\tDone')
            with open(log, 'a') as f:
                print(f'{country}', file=f)
        except MemoryError:
            print(f'-- Failed {country}')
            with open(log, 'a') as f:
                print(f'-- Failed {country}', file=f)

