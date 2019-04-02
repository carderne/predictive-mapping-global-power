# Issues
- Need to see if works okay with pre-merged raster
- Isolated networks
- LV calc should take into account demand
- Separate OSM HV and MV
- Add 'debug?' parameter to noisy functions
- Handle Alaska, Hawaii, Prussia, French Guiana, islands

## Difficult countries
India
France
Russia (lost stuff over date line)
Canada (lost the islands)
United States of America (lost some AK islands)
Brazil
Australia
China
Fiji
French Southern and Antarctic Lands
Greenland
Antarctica

# Preparation
## Sources
1. planet.pbf from https://wiki.openstreetmap.org/wiki/Planet.osm#Downloading
2. GHS from: https://ghsl.jrc.ec.europa.eu/
3. GHS URB/RUR from: https://ghsl.jrc.ec.europa.eu/ghs_smod.php
4. VIIRS from: https://ngdc.noaa.gov/eog/viirs/download_dnb_composites.html (use noaa_scrape.py to get all monthly files)
5. GADM from: https://gadm.org/
6. Simple admin (NE_50m_admin0) from: http://naturalearthdata.com/

## VIIRS
1. Use dl.sh to download
2. Use ext.sh (and ext.py) to extract into monthly directories
3. Use merge.sh to merge each month into global rasters
4. Similar for single annual raster

## Roads
1. ogr2poly.py to convert simple admin to separate poly files (and buffer by 100km)
    ```
    python ogr2poly.py -b 100000 -f ADM0_A3 ne_50m_admin0.gpkg
    ```

2. clip_osm.py to clip into individual country o5m files:
    ```
    python3 clip_osm.py planet.pbf poly o5m
    ```

3. Edit /usr/share/gdal/2.2/osmconf.ini:
    ```
    [lines]
    ...
    attributes=...,power,voltage
    ```

3. osm2gpkg.py to convert to roads gpkg
3. Use merge_lots.sh

## Grid
1. Use o5m output from step (2) in [Roads](Roads)
2. Use extract_osm_grid.py
3. Use merge_lots.sh

# Modelling
## Gridfinder
1. Run `runner.py targets`
2. Run `runner.py costs`
3. Run `runner.py dijk`
4. Create grid raster mask: `rasterize.sh data/grid_vec data/grid`
5. Subtract mask from guess:
    ```

    ```
6. Run `runner.py vector`

## Access-Estimator
1. Run `runner.py pop_elec`
2. Run `runner.py local`

# Processing results
## HV
### For HV infra
- QGIS: Rasterize high-res (same cell size and extent as mv, burn 1, nodata 0, pre-init 0, COMPRESS=LZW, TILED=YES)
- Multiply by 0.49*USD/km (cost = 200k USD/km)

### For buffer zone
All QGIS.
1. project to EPSG:54002
2. buffer 100km
3. dissolve
4. reproject EPSG:4326
5. rasterize same as above

## MV
### Underground/overground mask
1. Filter `ne_50m_admin0_access.gpkg` with `total==1` to get only countries with 100% access.
2. Use to clip urb.tif:
    ```
    gdalwarp -cutline ~/data/admin/ne_50m_admin0_access100.gpkg ~/data/pop/urb.tif ~/data/pop/urb_only100.tif
    ```
3. Raster calculator result keeping only >=3:
    ```
    gdal_calc.py -A ~/data/pop/urb_only100.tif --outfile=~/data/pop/underground_mask.tif --calc="A>=3" --NoDataValue=0
    ```

### To get single gpkg
1. Use merge_lots.sh

### To get infra costs
1. Null guess rasters
    ```
    for i in *; do gdal_translate -of GTiff -a_nodata 0 $i ../nulled/$i; done
    ```

2. Merge
    ```
    gdal_merge.py -co "COMPRESS=LZW" -co "TILED=YES" -o mv_binary.tif nulled/*.tif
    ```

3. Use HV buffer and filter outside
    ```
    gdal_calc.py --co "COMPRESS=LZW" --co "TILED=YES" -A mv_km.tif -B hv_buffer_50km.tif --outfile=mv_km_filt.tif --calc="A*B"
    ```

4. Null again
    ```
    gdal_translate -co "COMPRESS=LZW" -co "TILED=YES" -of GTiff -a_nodata 0 mv_binary_filt.tif mv_binary_filt_null.tif
    ```

5. Multiply by 0.49*USD/km (cost = 40k USD/km)
    ```
    gdal_calc.py --co "COMPRESS=LZW" --co "TILED=YES" -A mv_binary.tif --outfile=mv_km.tif --calc="0.49*40000*A"
    ```

## LV
Output from model is km per cell.
1. Same as 1-2 of MV infra costs
2. Calculate cost: RES * COST * lv_km
    ```
    gdal_calc.py --co "COMPRESS=LZW" --co "TILED=YES" -A lv_km.tif --outfile=lv_cost.tif --calc="0.25*15000*A"
    ```

# GDAL/OGR/OSM stuff

Cheat sheet: https://github.com/dwtkns/gdal-cheat-sheet

- Convert: `osmconvert swaziland.pbf -B=eSwatini.poly -o=swaziland.o5m`
- Filter: `osmfilter swaziland.o5m --keep="highway=motorway =trunk =primary =secondary =tertiary"`
- ogr2ogr: `ogr2ogr -f GPKG streets3.gpkg /vsistdin/ lines`
- mosaic: `gdal_merge.py -co "COMPRESS=LZW" -co "TILED=YES" -o mv_binary.tif nulled/*.tif`
- merge: `ogrmerge.py -f GPKG -o ../merged1.gpkg *.gpkg`
- compress: `gdal_translate -of GTiff -co "COMPRESS=LZW" -co "TILED=YES" Kenya.tif kcomp.tif`
- tiling: `for i in *; do gdal_retile.py -ps 10000 10000 -targetDir ../tiled $i; done`
