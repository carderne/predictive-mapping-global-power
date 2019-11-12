# Methods for: Predictive mapping of the global power system using open data (in review)
This repository contains preparatory scripts, data inputs and instructions to reproduce results found in this forthcoming paper. (The paper and the resultant data and visualizations will be linked here once published.)

## 1. Requirements for reproduction
A machine with a minimum of 32 GB of memory is recommended, along with at least 500 GB of available hard drive space and preferably at least four physical cores. All processing was done using Ubuntu 18.04 with the following software:
- Python 3.7
- GDAL 2.4.2
- QGIS 3.4.10

With these installed (QGIS only for preparing data if needed, post-processing and visualizing), this repository along with [gridfinder](https://github.com/carderne/gridfinder) and [access-estimator](https://github.com/carderne/access-estimator) should be cloned to a directory:

    git clone https://github.com/carderne/predictive-mapping-global-power.git
    git clone https://github.com/carderne/gridfinder.git
    git clone https://github.com/carderne/access-estimator.git

And their respective requirements should be installed into a virtual environment:

    mkdir env
    python3 -m venv env
    source env/bin/activate
    pip install -r predictive-mapping-global-power/requirements.txt
    pip install -r gridfinder/requirements.txt
    pip install -r access-estimator/requirements.txt

Subsequently, `gridfinder` and `access-estimator` can be added to the venv:

    pip install gridfinder/
    pip install access-estimator/

If this fails, you may need to run the following first: `sudo apt install libspatialindex-dev`.

With this complete, recommended is to make a subdirectory called `data` where input and output data will live. This can be configured to something else in `config.yml`. Then you can continue to data preparation.

## 2. Data preparation
The data sources used in this paper are follows. Note that the tools are source-agnostic and similar sources can be used instead of these. These files should be placed in the `data/` subfolder, and the file names can be configured in `config.yml`.
1. [Streets and grids (OSM)](https://wiki.openstreetmap.org/wiki/Planet.osm#Downloading)
2. [Population raster (GHSL-POP)](https://ghsl.jrc.ec.europa.eu/)
3. [Urban extents raster (GHS-SMOD)](https://ghsl.jrc.ec.europa.eu/ghs_smod.php)
4. [Night-time lights rasters (NOAA VIIRS)](https://ngdc.noaa.gov/eog/viirs/download_dnb_composites.html)
5. [Admin boundaries (Natural Earth)](https://www.naturalearthdata.com/http//www.naturalearthdata.com/download/10m/cultural/ne_10m_admin_0_countries.zip)
6. [Ocean (Natural Earth)](https://www.naturalearthdata.com/http//www.naturalearthdata.com/download/10m/physical/ne_10m_ocean.zip)
7. [DEM (NASA SRTM)](https://hydrosheds.org/)
8. [Land cover (ESA)](http://maps.elie.ucl.ac.be/CCI/viewer/index.php)
9. [Shorelines (NOAA)](https://www.ngdc.noaa.gov/mgg/shorelines/gshhs.html)

### Modifications to admin boundaries
Coast lines are buffered outwards to ensure all night-time lights and population pixels are captured, and to avoid edge-effects from the filtering process. This is a rough process that can be follows:
1. Buffer all admin boundaries by 0.05 degrees
2. Intersection with ocean layer
3. Buffer another 0.05 degrees
4. Merge result with original admin layer
5. Dissolve by field ADM0_A3 (or whatever unique ID is for each admin boundary)

In addition to this, several countries were either dropped, trimmed or split to simplify processing.

**Dropped (because too small or too spread-out for model assumptions to hold)**

    KIR FJI ATC PCN HMD SGS KAS ATF FSM PYF IOT IOA MDV PLW SHN GRL NIU VAT ALD BMU CPV MUS SYC

**Trimmed (geospatial issues or too spread out)**

    USA (W of date line, Hawaii, islands)
    RUS (E of date line, islands)
    CAN (northern islands)
    ECU (Galapagos)
    CHL (Easter Island)
    MEX (outlying islands)
    ESP (Canary)
    PRT (Madeira, Azores)
    NOR (outlying islands)
    IND (outlying islands)
    FRA (outlying islands)
    NLD (outlying islands)
    AUS (outlying islands)
    NZL (outlying islands)

**Split (to overcome memory limitations)**

    USA (USA, ALK)
    FRA (FRA, GUI)
    RUS (RUS, PRU, RNW, RUE, SAK, RUN, RUW, CRM)
    AUS (AUW, AUE, TAS)
    CAN (CNF, CNN, CAQ, CAB, CAS, CAX, CAY, CAZ)
    BRA (BRA, BAN)

## 3. Preparing targets from night-time lights
**Note:** in all instructions below, scripts other than `runner.py` are in the `scripts/` directory within this repository. This has been excluded in instructions for brevtiy.

Use the following process to download monthly global VIIRS night-time lights rasters for a specified year:
1. Use `./noaa_scrape.py > ntl_links.txt` to get a list of NTL URLs.
2. Use `wget -i ntl_links.txt` to download all to the current directory.
3. Use `for f in *; do tar -xvzf {file} --wildcards --no-anchored '*rade*'; done`
4. Organize into monthly folders 01-12
5. Use `for f in {01..12}; do gdal_merge.py -o $f.tif $f/*.tif; done`

Then the  following to download the pre-averaged annual global raster:
1. Use `./noaa_scrap.py > ntl_links.txt` but with different target links (need to edit script).
2. Use `wget -i ntl_links.txt` as above.
3. Use `tar -xvzf {file} --wildcards --no-anchored '*vcm-orm-ntl*'`
4. Use `gdal_merge.py -o ntl_annual.tif *.tif`

Once these are prepared, you can run use the `runner.py` script as follows to convert these night-time lights rasters into a single 'targets' raster for each country, defining the electrification targets that are defined as having electricity access. Before doing so, ensure that `config.yml` has been appropriately edited.

    cd predictive-mapping-global-power  # if not already in that directory
    ./runner.py --help (to see an overview of optional command-line parameters)
    ./runner.py targets

Depending on the number and size of countries, this can take several hours.

In order to filter these results even further, we can incorporate land-cover, slope, altitude and population. In this paper, all of these were applied, using the data sources described above. First, for each of these, run the following:
1. Repeat for each raster to clip to country outline:
    ```
    ./clip_to_countries.py land.tif land -a=ne_50m_admin0.gpkg -s=targets
    # replace 'land.tif' with appropriate global input file
    # replace 'land' with appropriate output directory (within data subdirectory)
    
    ./nonan.sh data/land
    # replace with appropriate directory
    ```

Once this is completed, the targets rasters can be filtered using these new rasters. An example is shown below with filter thresholds for each raster created above:

    ./filter.py targets targets_filt -f data/land '<210' -f data/slope '<25' -f data/landscan '>2'
    # targets is the input directory and targets_filt is the output

## 4. Costs preparation
The costs rasters are rasters that define the 'cost' of traversing a particular pixel. Please see the [gridfinder](https://github.com/carderne/gridfinder) repository and the paper for more information. To create these vectors from the OpenStreetMap source data, do the following:
1. Convert admin to poly files (buffer by 100km) `ogr2poly.py -b 100000 -f ADM0_A3 ne_50m_admin0.gpkg`
2. Clip into individual country o5m files: `clip_osm.sh planet.pbf poly o5m`
3. Edit `/usr/share/gdal/2.2/osmconf.ini` as follows:
    ```
    [lines]
    ...
    attributes=...,power,voltage
    ```
4. Convert to costs gpkg: `o5m2gpkg.sh o5m costs_vec roads`
5. Once these costs vectors are prepared, the `runner.py` script can be used to convert them into costs rasters that can be used in the model. Note that the targets rasters must already be created for this to work, as these rasters are matched to be exactly the same size as those.
    ```
    ./runner.py costs
    ```

## 5. Creating HV grid map
If you would like to create a single grid map of all OSM grid lines, follow this procedure:
1. Use o5m output from step (2) in Costs preparation
2. Convert to grid gpkg: `o5m2gpkg.sh o5m hv_vec`
3. Combine into a single gpkg: `merge_gpkg.sh hv`

## 6. Modelling with gridfinder
Now you're ready to run the model!
1. Run gridfinder algorithm on each country:
    ```
    runner.py dijk --targets_dir targets_filt
    ## if you didn't filter the targets, then the targets_dir option is not needed
    ```
2. An additional optional step is to subtract the OSM lines from the created lines so that they only show new non-OSM lines:
    ```
    ./rasterize.sh data/hv_vec data/hv
    ./subtract_rast.py mv hv mv_sub
    ```
3. If wanted, the results can be merged into a single raster for all countries:
    ```
    cd data/mv
    gdal_merge.py -co "COMPRESS=LZW" -co "TILED=YES" -ot Byte -n 0 -a_nodata 0 -o mv_merged.tif *.tif
    gdal_edit.py -a_srs EPSG:4326 mv_merged.tif
    ```

This merged raster can also be filtered to remove lines that are too far (100 km in this case) from OSM grid lines, and that cross oceans. This process is done partially in QGIS, using the HV lines generated in Section 5:
1. Reproject to EPSG:54002
2. Buffer by 100 km
3. Dissolve
4. Reproject to EPSG:4326
5. Get intersection with NOAA shorelines (data source 9)
6. Clip the `mv_merged.tif` raster using this new layer:
    ```
    gdalwarp -s_srs EPSG:4326 -t_srs EPSG:4326 -ot Byte -of GTiff -tr 0.004166666699998 -0.004166666699999 -tap -cutline hv_and_ocean.gpkg -dstnodata 0.0 -wo NUM_THREADS=2 -multi -co COMPRESS=LZW mv_thin.tif mv_thin_clipped.tif
    # where 'hv_and_ocean.gpkg' can be replaced with the file produced in step 5
    ```

## 7. Calculate local access levels
This process will create rasters showing the population with electricity access, and subsequently the amount (in km) of LV infrastructure in each pixel, based on national statistics and other heuristics. These depend on the [access-estimator](https://github.com/carderne/access-estimator) repository.

    ./runner.py pop_elec
    ./runner.py local

Much as for the MV lines, these can be merged into a single global layer if desired.
    
In addition, a mask can be created to determine which MV/LV lines are overground and which underground:
1. Filter the admin boundaries layer to only include countries with 100% electricity access.
2. Use these boundaries to clip the urban extents raster (global):
    ```
    gdalwarp -cutline admin_only100.gpkg urb.tif urb_only100.tif
    ```
3. Use raster calculator to keep only those with the desired urban level (will depend on data used):
    ```
    gdal_calc.py -A urb_only100.tif --outfile=underground_mask.tif --calc="A>=20" --NoDataValue=0
    ```


## 8. Web-map
To create a web map of targets, HV and MV and display using MapBox studio. Targets can be used as a raster layer. HV lines should already be in vector format. MV lines can be converted to vector as follows (using QGIS):
1. r.thin
2. r.to.vect

Then (again in QGIS) install the 'Tiles XYZ' Plugin and all three layers can be converted to MBTiles using the following settings:
- Min zooom: 2
- Max zoom: 9
- DPI: 96

## 9. Other
Please get in touch with the authors (or with me directly via GitHub) for any other questions.
