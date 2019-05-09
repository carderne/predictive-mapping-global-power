#!/bin/bash
# Split planet OSM file using POLY boundaries
# Output is separate o5m files

# Arg 1: planet file
# Arg 2: poly dir
# Arg 3: output o5m dir

for f in $2/*; do
    name=$(echo $f | sed -r "s/.+\/(.+)\..+/\1/");
    o5m=$3/$name.o5m
    osmconvert $1 -B=$f -o=$o5m
done
