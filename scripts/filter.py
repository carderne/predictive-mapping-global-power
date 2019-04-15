#!/usr/bin/env python

import os
from pathlib import Path
from argparse import ArgumentParser


def calc(input_dir, output_dir, filters, overwrite=False):
    input_dir = Path(input_dir).expanduser()
    output_dir = Path(output_dir).expanduser()

    for f in input_dir.iterdir():
        name = f.stem
        outfile = output_dir / name
        if not outfile.is_file() or overwrite:
            file_list = calc = ""
            letter = "B"
            for filt in filters:
                filt_file = Path(filt[0]) / name
                if filt_file.is_file():
                    file_list += f"-{letter} {filt_file} "
                    calc += f" + A*({letter}{filt[1]})"
                    letter = chr(ord(letter) + 1)
            
            if calc == "":
                calc = "A"

            command = (
                f"gdal_calc.py -A {f} {file_list} --calc='0{calc}' --outfile {outfile}"
            )
            print(name, command)
            os.system(command)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("input_dir")
    parser.add_argument("output_dir")
    parser.add_argument(
        "-f", "--filter", action="append", nargs=2, metavar=("dir", "calc"), help=""
    )
    args = parser.parse_args()

    calc(args.input_dir, args.output_dir, args.filter)
