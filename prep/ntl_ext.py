import os
for file in os.listdir():
    cmd = f"tar -xzf {file} --wildcards --no-anchored '*rade*'"
    print(cmd)
    os.system(cmd)
    print('Done')
