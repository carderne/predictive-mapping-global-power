#!/bin/bash
# First arg: directory containing .gpkg's to merge

mkdir $1/partial
mkdir $1/_merged
for i in {1..5}; do
	mkdir $1/$i;
	mv `ls $1/*.gpkg | head -50` $1/$i/;
	ogrmerge.py -f GPKG -o $1/partial/$i.gpkg $1/$i/*.gpkg -single;
	echo $i;
done

ogrmerge.py -f GPKG -o $1/_merged/merged.gpkg $1/partial/*.gpkg -single
echo 'Merged'

for i in {1..5}; do
	mv $1/$i/*.gpkg $1/;
	rm -r $1/$i/;
done
rm -r $1/partial/
echo 'Cleaned'
