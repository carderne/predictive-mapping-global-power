mkdir ../extracted
for i in *; do
    name=${i%.*}
    unzip -j $i dist.tif -d ./$name;
    mv $name/dist.tif ../extracted/$name.tif;
done

mkdir ../processed
mkdir ../converted
for i in *; do
    gdal_calc.py -A ../extracted/$name.tif --outfile=../processed/$name.tif --calc="A==0";
    gdal_translate -ot Int32 -of GTiff ../processed/$name.tif ../converted/$name.tif;
done

mkdir ../nulled
for i in *; do
    gdal_translate -of GTiff -a_nodata 0 $i ../nulled/$i;
done
