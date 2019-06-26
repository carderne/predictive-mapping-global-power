#!/bin/bash
# Set NO NaN value on files that will be used in filter.py

# Arg 1: directory to nonan

for f in $1/*; do
    gdal_translate -a_nodata none $f temp.tif
    mv temp.tif $f
done
