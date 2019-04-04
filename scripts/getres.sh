#!/bin/bash
# Prints tiff output in width, height
# First arg: file name

gdalinfo $1 | sed -n -e 's/Size is \(.\)/\1/p' | sed 's/,//g'
