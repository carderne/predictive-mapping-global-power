#!/bin/bash

# Arg 1: Raster dir to be filtered (A)
# Arg 2: Raster dir to use as filters (B)
# Arg 3: Dir to save output
# Arg 4: Calculation to apply to A and B

# e.g. pass r1 r2 rOut A*(B!=220) to filter/remove r1 where r2==220 and save in rOut
# e.g. A*(B<25) to get where B is below 25

for f in $1/*; do
    name=$(echo $f | sed -r "s/.+\/(.+)\..+/\1/");
    filt=$2/$name.tif
    out=$3/$name.tif
    if [ ! -f $filt ]; then
        echo "$filt doesn't exist - copying directly!"
        cp $f $out
    elif [ ! -f $out ]; then
        gdal_calc.py -A $f -B $filt --calc="$4" --outfile=$out
    fi
done
