#!/bin/bash
# Clip the supplied vector to countries

# Arg 1: The vector to clip
# Arg 2: The folder with country outlines
# Arg 3: Output folder

for f in $2/*; do
    name=$(echo $f | sed -r "s/.+\/(.+)\..+/\1/");
    ogr2ogr -clipsrc $f $3/$name.gpkg $1 -f "GPKG"
done
