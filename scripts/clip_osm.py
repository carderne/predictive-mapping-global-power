import os
import sys

planet_file = sys.argv[1]
poly_dir = sys.argv[2]
o5m_dir = sys.argv[3]
for file in os.listdir(poly_dir):
    name = file.split('.poly')[0]
    o5m_out = f'{o5m_dir}/{name}.o5m'

    cmd = f'osmconvert {planet_file} -B={poly_dir}/{file} -o={o5m_out}'
    os.system(cmd)

    print(f'Done {name}')

