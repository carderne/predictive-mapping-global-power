# Preparation
## Sources
1. planet.pbf from https://wiki.openstreetmap.org/wiki/Planet.osm#Downloading
2. GHS from: https://ghsl.jrc.ec.europa.eu/
3. GHS URB/RUR from: https://ghsl.jrc.ec.europa.eu/ghs_smod.php
4. VIIRS from: https://ngdc.noaa.gov/eog/viirs/download_dnb_composites.html (use noaa_scrape.py to get all monthly files)
5. Simple admin (NE_50m_admin0) from: http://naturalearthdata.com/
6. LandScan population raster
7. DEM from HydroSheds
8. Land cover from http://maps.elie.ucl.ac.be/CCI/viewer/index.php
9. Shorelines https://www.ngdc.noaa.gov/mgg/shorelines/gshhs.html

## Admin
### Buffer coastal places
1. Buffer admin 0.05 degrees
2. Intersection with ocean layer
3. Buffer another 0.05 degrees
4. Merge with admin layer
5. Dissolve by field ADM0_A3

### Modifications
1. Dropped
    ```
    KIR FJI ATC PCN HMD SGS KAS ATF FSM PYF IOT IOA MDV PLW SHN GRL NIU VAT ALD BMU CPV MUS SYC
    ```

2. Trimmed

    ```
    USA (W of date line, Hawaii, islands)
    RUS (E of date line, islands)
    CAN (northern islands)
    ECU (Galapagos)
    CHL (Easter Island)
    MEX (islands)
    ESP (Canary)
    PRT (Madeira, Azores)
    NOR (islands)
    IND (islands)
    FRA (islands)
    NLD (islands)
    AUS (islands)
    NZL (islands)
    ```

3. Split
    ```
    USA (USA, ALK)
    FRA (FRA, GUI)
    RUS (RUS, PRU, RNW, RUE, SAK, RUN, RUW, CRM)
    AUS (AUW, AUE, TAS)
    CAN (CNF, CNN, CAQ, CAB, CAS, CAX, CAY, CAZ)
    BRA (BRA, BAN)
    ```

## VIIRS
### VIIRS monthly
1. Use `noaa_scrape.py > ntl_links.txt` to get a list of NTL URLs.
2. Use `wget -i ntl_links.txt` to download all to the current directory.
3. Use `for f in *; do tar -xvzf {file} --wildcards --no-anchored '*rade*'; done`
4. Organize into monthly folders 01-12
5. Use `for f in {01..12}; do gdal_merge.py -o $f.tif $f/*.tif; done`

### VIIRS annual
1. Use `noaa_scrap.py` but with different target links.
2. Use `wget` as above.
3. Use `tar -xvzf {file} --wildcards --no-anchored '*vcm-orm-ntl*'`
4. Use `gdal_merge.py -o ntl_annual.tif *.tif`

## Costs
1. Convert admin to poly files (buffer by 100km) `ogr2poly.py -b 100000 -f ADM0_A3 ne_50m_admin0.gpkg`
2. Clip into individual country o5m files: `clip_osm.sh planet.pbf poly o5m`

3. Edit `/usr/share/gdal/2.2/osmconf.ini`:
    ```
    [lines]
    ...
    attributes=...,power,voltage
    ```

3. Convert to costs gpkg: `o5m2gpkg.sh o5m costs_vec roads`

## Grid
1. Use o5m output from step (2) in [Costs](Costs)
2. Convert to grid gpkg: `o5m2gpkg.sh o5m hv_vec`
3. Combine into a single gpkg: `merge_gpkg.sh hv`

## Filtering on land cover and slope
1. Repeat for each raster to clip to country outline:
    ```
    clip_to_countries.py land.tif land -a=ne_50m_admin0.gpkg -s=targets
    ```
2. Use `nonan.sh` on `slope` folder (and others?) to change NaN to 0.
3. Filter targets using these layers:
    ```
    filter.py targets targets_filt -f data/land '<210' -f data/slope '<25' -f data/landscan '>2'
    ```

# Modelling
## Gridfinder
### High-MV
1. Create targets rasters: `runner.py targets`
2. Create costs rasters: `runner.py costs`
3. Run model: `runner.py dijk`
4. Create grid raster mask: `rasterize.sh data/hv_vec data/hv`
5. Subtract mask from guess:
    ```
    subtract_rast.py mv hv mv_sub
    ```

### Low-MV
1. Create targets05 with `--ntl_threshold=0.05`
2. Create new costs rasters with: `make_costs_with_mv.sh mv costs costs_with_mv`
3. Rerun model and subtract `mv` from `mv05` to create `mv05_sub`

# Access-Estimator
1. Run `runner.py pop_elec` using targets05 (allow more electrified places).
2. Run `runner.py local`

# Processing results
## HV
### For HV infra
- Multiply by 0.49*USD/km (cost = 200k USD/km)

## MV
### Combine mv and mv05 and merge
1. Use `combine.py` to use mv+mv05 for countries with access >= 0.9, and only mv in all other countries.
2. Merge
    ```
    gdal_merge.py -co "COMPRESS=LZW" -co "TILED=YES" -ot Byte -n 0 -a_nodata 0 -o mv.tif *.tif
    ```
3. Convert CRS: `gdal_edit.py -a_srs EPSG:4326 mv_comb.tif`

### Filtering remote and oceans
1. Buffer HV by 100km (use EPSG:54002), dissolve, reproject EPSG:4326
3. Get intersection of GHSSG_I_L1 with HV buf.
4. Clip raster:
    ```
    gdalwarp -s_srs EPSG:4326 -t_srs EPSG:4326 -ot Byte -of GTiff -tr 0.004166666699998 -0.004166666699999 -tap -cutline hv_gshhg.gpkg -dstnodata 0.0 -wo NUM_THREADS=2 -multi -co COMPRESS=LZW mv_thin.tif mv_thin_clipped.tif
    ```

### Underground/overground mask
1. Filter `ne_50m_admin0_access.gpkg` with `total==1` to get only countries with 100% access.
2. Use to clip urb.tif:
    ```
    gdalwarp -cutline ne_50m_admin0_access100.gpkg urb.tif urb_only100.tif
    ```
3. Raster calculator result keeping only >=3:
    ```
    gdal_calc.py -A urb_only100.tif --outfile=underground_mask.tif --calc="A>=3" --NoDataValue=0
    ```

## LV
Output from model is km per cell.
1. Same as 1 of MV infra costs (except use `-ot Float32`)
2. Calculate cost: RES * COST * lv_km

# Web-map
## HV
1. Create MBTiles with min zoom 2 max 9 dpi 96?

## MV
1. r.thin
2. r.to.vect
3. MBtiles same values
