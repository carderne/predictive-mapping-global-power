from pathlib import Path

import geopandas as gpd

from gridfinder._util import save_raster
from gridfinder.prepare import clip_rasters, merge_rasters, create_filter, prepare_ntl, drop_zero_pop

data = Path('big')

ntl_folder_in = data / 'ntl'
pop_in = data / 'pop' / 'ghs.tif'
aoi_in = data / 'admin' / 'combined.gpkg'
aoi_all = gpd.read_file(aoi_in)

scratch = data / 'scratch'
ntl_folder_out = scratch / 'ntl_clipped'
ntl_merged_out = scratch / 'ntl_merged.tif'
ntl_thresh_out = scratch / 'ntl_thresh.tif'

countries = aoi_all['code'].tolist()

for c in countries:
    country = c.replace(' ', '_')
    targets_out = data / 'targets' / f'{country}.tif'
    aoi = aoi_all.loc[aoi_all['code'] == c]

    if targets_out.is_file():
        pass
        # print(f'Already done {c}')
#    elif country in skip:
#        print(f'Skip {country}')

    else:
        try:
            print(f'{country}')
            # Clip NTL rasters and calculate nth percentile values
            clip_rasters(ntl_folder_in, ntl_folder_out, aoi)
            raster_merged, affine = merge_rasters(ntl_folder_out)
            save_raster(ntl_merged_out, raster_merged, affine)

             # Apply filter to NTL
            ntl_filter = create_filter()
            ntl_thresh, affine = prepare_ntl(ntl_merged_out, aoi, ntl_filter=ntl_filter, upsample_by=1)
            save_raster(ntl_thresh_out, ntl_thresh, affine)


            # Drop zero pop
            targets_clean = drop_zero_pop(ntl_thresh_out, pop_in, aoi)
            save_raster(targets_out, targets_clean, affine)

            print(f'\t\tdone')
            with open('targets.txt', 'a') as f:
                print(f'{country}', file=f)

        except MemoryError:
            print(f'-- Failed {country}')
            with open('targets.txt', 'a') as f:
                print(f'-- Failed {country}', file=f)

