#!/bin/bash
# Subtract rasters in one dir from those in another, output to a third
# Must activate python venv before use

# Arg1: Dir of original rasters
# Arg2: Dir of rasters to use for subtracting
# Arg3: Output dir (should exist)

dir=$(dirname $0)
echo $dir
temp=$3/temp.tif

for f in $1/*.tif; do
	name=$(echo $f | sed -r "s/.+\/(.+)\..+/\1/");
	subtract=$2/$name.tif
	out=$3/$name.tif
	# gdal_calc.py -A $f -B $subtract --outfile=$out --calc="A-B"
	if [ ! -f $out ]; then
		echo "Doing $name";
		python $dir/subtract_rast.py $f $subtract $temp
		gdal_translate -ot Int16 -of GTiff -a_nodata 0 $temp $out
	fi
done

rm $temp
