from pathlib import Path
import time

import geopandas as gpd

from gridfinder._util import save_raster
from gridfinder.prepare import prepare_roads

data = Path('big')
log = 'costs.txt'

aoi_in = data / 'admin' / 'combined.gpkg'
aoi_all = gpd.read_file(aoi_in)
countries = aoi_all['code'].tolist()

loop = 0
while len(countries) > 0:
    loop += 1
    # print(f'loop {loop}\trem {len(countries)}')
    for c in countries:
        country = c.replace(' ', '_')
        aoi = aoi_all.loc[aoi_all['code'] == c]
        official = aoi['official'].tolist()[0]
        targets_out = data / 'targets' / f'{country}.tif'
        roads_in = data / 'roads/gpkg' / f'{official}.gpkg'
        roads_out = data / 'costs' / f'{country}.tif'

        if targets_out.is_file() and roads_in.is_file() and not roads_out.is_file():
            aoi = aoi_all.loc[aoi_all['code'] == c]
            countries.remove(c)
            try:
                print(f'{country}')
                roads_raster, affine = prepare_roads(roads_in, aoi, targets_out)
                save_raster(roads_out, roads_raster, affine)

                print(f'\t\tdone')
                with open(log, 'a') as f:
                    print(f'{country}', file=f)

            except MemoryError:
                print(f'-- Failed {country}')
                with open(log, 'a') as f:
                    print(f'-- Failed {country}', file=f)

    time.sleep(300)

