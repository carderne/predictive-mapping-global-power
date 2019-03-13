# Issues
- overlay HV
- Isolated networks
- Artifacts on borders (fix by clip with gadm)
- Use country codes
- Use GADM instead of simplified (keep simplified road network)
- Optimise (numba, what else?)
- Get beefier instance (thanks Ben)
- Parallelize
- Pre-burn OSM
- Use pre-cooked NTL?
- Skip drop-sites?

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
6. Simple admin from: http://naturalearthdata.com/

## VIIRS
1. Use dl.sh to download
2. Use ext.sh (and ext.py) to extract into monthly directories
3. Use merge.sh to merge each month into global rasters
4. Similar for single annual raster

## Roads
NB: Rather than merge into global roads, rather just clip the rough-clipped roads using GADM before rasterize.

1. ogr2poly.py to convert simple admin to separate poly files
2. osm2gpkg.py to convert to o5m and roads gpkg
3. Use merge_lots.sh

## Grid
1. Use o5m output from step (2) in [Roads](Roads)
2. Use extract_osm_grid.py
3. Use merge_lots.sh

# Modelling
## Gridfinder

## Access-Estimator
1. Run access.py (based on access_rates.py)
2. Run local.py (based on lv_length.py)
2. modify LV formula to return length, then static multiply to get cost

# Processing results
## HV
### For HV infra
- QGIS: Rasterize high-res (same cell size and extent as mv, burn 1, nodata 0, pre-init 0, COMPRESS=LZW, TILED=YES)
- Multiply by 0.49*USD/km

### For buffer zone
All QGIS.
1. project to EPSG:54002
2. buffer 100km
3. dissolve
4. reproject EPSG:4326
5. rasterize same as above

## MV
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

5. Multiply by 0.49*USD/km
    ```
    gdal_calc.py --co "COMPRESS=LZW" --co "TILED=YES" -A mv_binary.tif --outfile=mv_km.tif --calc="0.49*COST*A"
    ```

# GDAL/OGR/OSM stuff

Cheat sheet: https://github.com/dwtkns/gdal-cheat-sheet

- Convert: `osmconvert swaziland.pbf -B=eSwatini.poly -o=swaziland.o5m`
- Filter: `osmfilter swaziland.o5m --keep="highway=motorway =trunk =primary =secondary =tertiary"`
- ogr2ogr: `ogr2ogr -f GPKG streets3.gpkg /vsistdin/ lines`
- mosaic: `gdal_merge.py -co "COMPRESS=LZW" -co "TILED=YES" -o mv_binary.tif nulled/*.tif`
- merge: `ogrmerge.py -f GPKG -o ../merged1.gpkg *.gpkg`
- compress: `gdal_translate -of GTiff -co "COMPRESS=LZW" -co "TILED=YES" Kenya.tif kcomp.tif`

# Merge lots of vectors
