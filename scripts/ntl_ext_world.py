import os
for file in os.listdir():
    cmd = f"tar -xvzf {file} --wildcards --no-anchored '*vcm-orm-ntl*'"
    print(cmd)
    os.system(cmd)
    print('Done')
