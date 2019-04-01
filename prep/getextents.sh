#!/bin/bash
# Get raster extents in Xmin Ymin Xmax Ymax
# First arg: raster name

gdalinfo $1 | grep 'Lower Left\|Upper Right' | sed -E 's/[^\(]+\(([^,]+),([^\)]+)\).+/\1,\2/' | paste --serial --delimiter ',' - | tr ' ' '\0' | sed 's/,/ /g'
