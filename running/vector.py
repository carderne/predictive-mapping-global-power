from pathlib import Path
import time

import geopandas as gpd

from gridfinder._util import save_raster
from gridfinder.gridfinder import get_targets_costs, optimise
from gridfinder.post import threshold, thin, raster_to_lines

# Set file paths and clip AOI
data = Path('big')
guess_skeletonized_out = data / 'scratch' / 'dist.tif'
log = 'vector.txt'

aoi_in = data / 'admin' / 'combined.gpkg'
aoi_all = gpd.read_file(aoi_in)
countries = aoi_all['code'].tolist()

loop = 0
while True:
    loop += 1
    # print(f'loop {loop}\trem {len(countries)}')

    for c in countries:
        country = c.replace(' ', '_')
        guess_in = data / 'guess' / f'{country}.tif'
        guess_vec_out = data / 'vec' / f'{country}.gpkg'

        if guess_in.is_file() and not guess_vec_out.is_file():
            countries.remove(c)
            try:
                print(f'{country}')
                guess_skel, affine = thin(guess_in)
                save_raster(guess_skeletonized_out, guess_skel, affine)
                guess_gdf = raster_to_lines(guess_skeletonized_out)
                guess_gdf.to_file(guess_vec_out, driver='GPKG')

                print(f'\t\tDone')
                with open(log, 'a') as f:
                    print(f'{country}', file=f)

            except MemoryError:
                print(f'-- Failed {country}')
                with open(log, 'a') as f:
                    print(f'-- Failed {country}', file=f)

    time.sleep(300)

