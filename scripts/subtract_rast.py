
# Arg 1: input raster
# Arg 2: raster to subtract
# Arg 3: output raster

import sys
import rasterio
sys.path.append("gridfinder") 
from gridfinder import save_raster

rast_in = sys.argv[1]
sub_in = sys.argv[2]
subbed_out = sys.argv[3]

rast_rd = rasterio.open(rast_in)
rast = rast_rd.read(1)
affine = rast_rd.transform
crs = rast_rd.crs

sub = rasterio.open(sub_in).read(1)

subbed = rast - sub
subbed[subbed <= 0] = 0
subbed[subbed > 0] = 1

save_raster(subbed_out, subbed, affine, crs)

