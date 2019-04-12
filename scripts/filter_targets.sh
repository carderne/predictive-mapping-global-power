#!/bin/bash

# Arg 1: Raster dir to be filtered
# Arg 2: Raster dir to use as filters
# Arg 3: Dir to save output
# Arg 4: Value from filter raster to use as filter

# e.g. pass r1 r2 rOut 10 to filter r1 where r2==10 and save in rOut

for f in $1/*; do
    name=$(echo $f | sed -r "s/.+\/(.+)\..+/\1/");
    filt=$2/$name.tif
    out=$3/$name.tif
    if [ ! -f $out ]; then
        gdal_calc.py -A $f -B $filt --calc="A*(B!=$3)" --outfile=$out
    fi
done
