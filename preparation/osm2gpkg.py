import os

poly_dir = 'poly'
for file in os.listdir(poly_dir):
    name = file.split('.poly')[0]
    o5m_out = f'o5m/{name}.o5m'
    gpkg_out = f'gpkg/{name}.gpkg'

    cmd = f'osmconvert osm/planet.pbf -B={poly_dir}/{file} -o={o5m_out}'
    print(cmd)
    os.system(cmd)

    cmd = f'osmfilter {o5m_out} --keep="highway=motorway =trunk =primary =secondary =tertiary" | ogr2ogr -f GPKG {gpkg_out} /vsistdin/ lines'
    print(cmd)
    os.system(cmd)

    print(f'Done {name}')

