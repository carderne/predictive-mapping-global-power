import os
import sys

o5m_dir = sys.argv[1]
gpkg_dir = sys.argv[2]

for file in os.listdir(o5m_dir):
    name = file.split('.')[0]
    o5m_in = f'{o5m_dir}/{name}.o5m'
    gpkg_out = f'{gpkg_dir}/{name}.gpkg'

    cmd = f'osmfilter {o5m_in} --keep="highway=motorway =trunk =primary =secondary =tertiary power=line" | ogr2ogr -select highway,power,voltage -f GPKG {gpkg_out} /vsistdin/ lines'
    os.system(cmd)

    print(f'Done {name}')

