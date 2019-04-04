#!/bin/bash
# Combine guess output with costs to make costs_with_mv
# Arg 1: directory containing original guesses
# Arg 2: directory containing costs
# Arg 3: output directory

for f in $1/*; do
	name=$(echo $f | sed -r "s/.+\/(.+)\..+/\1/");
	costs=$2/$name.tif;
    noned=$3/noned.tif
    flipped=$3/flipped.tif
	out=$3/$name.tif

	if [ ! -f $out ]; then
		echo "Doing $name"
        gdal_translate -a_nodata none $f $noned
        gdal_calc.py -A $noned --calc="(A==0)*1+(A==1)*0" --outfile=$flipped
        gdal_calc.py -A $flipped -B $costs --calc="minimum(A,B)" --outfile=$out
        rm $noned $flipped
	fi
done

