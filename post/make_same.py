import sys
import os
import gdal
from gdalconst import GA_ReadOnly

f_mask = sys.argv[1]
f_in = sys.argv[2]
f_out = sys.argv[3]

data = gdal.Open(f_mask, GA_ReadOnly)
geoTransform = data.GetGeoTransform()
minx, maxy = geoTransform[0], geoTransform[3]
maxx = minx + geoTransform[1] * data.RasterXSize
miny = maxy + geoTransform[5] * data.RasterYSize
coords = ' '.join([str(x) for x in [minx, maxy, maxx, miny]])

command = 'gdal_translate -projwin {} -of GTiff {} {}'.format(coords, f_in, f_out)
os.system(command)

