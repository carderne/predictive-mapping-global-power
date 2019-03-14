from pathlib import Path

import geopandas as gpd
import pandas as pd

from gridfinder._util import save_raster, clip_raster
from access_rates import regularise, estimate

# Set file paths and clip AOI
data = Path('data')
log = 'access.txt'

pop_in = data / 'pop/ghs.tif'
urban_in = data / 'pop/urb.tif'
ntl_in = data / 'ntl/annual/world.tif'
access_in = data / 'pop/access.csv'
aoi_in = data / 'admin' / 'countries.gpkg'

access_all = pd.read_csv(access_in)
aoi_all = gpd.read_file(aoi_in)
countries = aoi_all['ADMIN'].tolist()

#skip = ['Falkland Islands', 'Indonesia']

for c in countries:
    country = c.replace(' ', '_')
    #if c in skip:
    #    continue
    targets_in = data / 'targets' / f'{country}.tif'
    pop_elec_out = data / 'pop_elec' / f'{country}.tif'
    aoi = aoi_all.loc[aoi_all['ADMIN'] == c]

    if targets_in.is_file() and not pop_elec_out.is_file():
        try:
      #      print(f'{country}')
      #      access = access_all.loc[access_all['Official'] == c]  # Official has capital for access
      #      access = {'total': float(access['access_total'].tolist()[0])/100,
      #        'urban': float(access['access_urban'].tolist()[0])/100,
      #        'rural':float(access['access_rural'].tolist()[0])/100}

      #      pop, urban, ntl, targets, affine, crs = regularise(country, aoi, pop_in, urban_in, ntl_in, targets_in)
      #      pop_elec, access_model_total = estimate(pop, urban, ntl, targets, access)
      #      save_raster(pop_elec_out, pop_elec, affine, crs)
      #      print(f'\t\tDone')
      #      with open(log, 'a') as f:
      #          print(f'{country}\t\treal: {access["total"]:.2f}\t\tmodel: {access_model_total:.2f}', file=f)
      #  
      #  except (MemoryError, ValueError, IndexError) as e:
            clipped, affine, crs = clip_raster(pop_in, aoi)
            save_raster(pop_elec_out, clipped[0], affine, crs)
            msg = f' -- Failed {country} --'
            print(msg)
            with open(log, 'a') as f:
                print(msg, file=f)

        except ValueError:
            pass
