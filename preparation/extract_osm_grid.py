import os

dir = '../roads/o5m'
for file in os.listdir(dir):
    name = file.split('.o5m')[0]
    o5m_out = f'../roads/o5m/{name}.o5m'
    gpkg_out = f'gpkg/{name}.gpkg'

    cmd = f'osmfilter {o5m_out} --keep="power=line" | ogr2ogr -f GPKG {gpkg_out} /vsistdin/ lines'
    print(cmd)
    os.system(cmd)

    print(f'Done {name}')

