from pathlib import Path
import time

import geopandas as gpd

from gridfinder._util import save_raster
from gridfinder.gridfinder import get_targets_costs, optimise
from gridfinder.post import threshold

# Set file paths and clip AOI
data = Path('big')
dist_out = data / 'scratch' / 'dist.tif'
log = 'model.txt'

aoi_in = data / 'admin' / 'combined.gpkg'
aoi_all = gpd.read_file(aoi_in)
countries = aoi_all['code'].tolist()

# skip = ['Fiji', 'French_Southern_and_Antarctic_Lands', 'Brazil', 'Australia']

loop = 0
while True:
    loop += 1
    # print(f'loop {loop}\trem {len(countries)}')

    for c in countries:
        country = c.replace(' ', '_')

        targets_in = data / 'targets' / f'{country}.tif'
        costs_in = data / 'costs' / f'{country}.tif'
        guess_out = data / 'guess' / f'{country}.tif'

        if targets_in.is_file() and costs_in.is_file() and not guess_out.is_file():
            countries.remove(c)
            try:
                print(f'{country}')
                targets, costs, start, affine = get_targets_costs(targets_in, costs_in)
                dist = optimise(targets, costs, start, silent=True)
                save_raster(dist_out, dist, affine)
                guess, affine = threshold(dist_out)
                save_raster(guess_out, guess, affine)

                print(f'\t\tDone')
                with open(log, 'a') as f:
                    print(f'{country}', file=f)

            except MemoryError:
                print(f'-- Failed {country}')
                with open(log, 'a') as f:
                    print(f'-- Failed {country}', file=f)

    time.sleep(300)

