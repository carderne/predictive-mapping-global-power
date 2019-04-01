#!/bin/bash

for f in COL
do
	targ=~/data/targets/$f.tif
	gdal_rasterize -at -burn 1 -a_nodata 0 -init 0 -ts $(./getres.sh $targ) -te $(./getextents.sh $targ)  ~/data/grid_vec/$f.gpkg ~/data/grid/$f.tif
done

