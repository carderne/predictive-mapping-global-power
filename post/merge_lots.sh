#!/bin/bash

mkdir $1/partial
for i in {1..5}; do
	mkdir $1/$i;
	mv `ls $1/*.gpkg | head -50` $1/$i/;
	ogrmerge.py -f GPKG -o $1/partial/$i.gpkg $1/$i/*.gpkg -single;
	echo $i;
done

ogrmerge.py -f GPKG -o $1/merged.gpkg $1/partial/*.gpkg -single
echo 'Merged'

mkdir $1/sep
for i in {1..5}; do
	mv $1/$i/*.gpkg $1/sep/;
	rm -r $1/$i/;
done
rm -r $1/partial/
echo 'Cleaned'
