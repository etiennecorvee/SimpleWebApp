import os
import shutil
from typing import Union, Tuple, List
from dataclasses import dataclass

def get_stat_time(filepath: str) -> float:
    stat = os.stat(filepath)
    print(" ... stat", type(stat.st_mtime), stat.st_mtime)
    return stat.st_mtime

@dataclass
class Stamp:
    day_parts: List[str]
    temps_parts: List[str]
    prefix: str

def GetDayString(input: Stamp) -> str:
    output = ""
    for index in range(len(input.day_parts)):
        output += input.day_parts[index]
        if index != len(input.day_parts)-1:
            output += "-"
    return output
    
def GetTempsString(input: Stamp) -> str:
    output = ""
    for index in range(len(input.temps_parts)):
        output += input.temps_parts[index]
        if index != len(input.temps_parts)-1:
            output += ":"
    return output

def GetTimestamp(input: Stamp, debug: bool=False) -> str:
    day = GetDayString(input)
    temps = GetTempsString(input)
    if debug is True:
        print("[DEBUG] GetTimestamp from {} -> {} + {}".format(input, day, temps))
    return input.prefix + day + "T" + temps + ".txt"

def parse_stamped_filename(filename: str, ext_with_dot: str, res_type: str, prefix: str="chute_d-", debug: bool = False) -> Stamp:
    stem = filename # os.path.basename(filepath)
    day_temps = stem.split("T")
    if debug is True:
        print(" ... day_temps", day_temps)
    if len(day_temps) == 2:
        day = day_temps[0]
        temps = day_temps[1]
        if debug is True:
            print(" ... len 2 ok: day, temps", day, temps, "prefix:", prefix, prefix in day, "res_type:", res_type, res_type in temps)
        if res_type in temps:
            if debug is True:
                print(" ... day, temps", day, temps, prefix in day, res_type in temps)
            if prefix in day and ext_with_dot in temps:
                day = day.strip(prefix)
                temps = temps.strip(ext_with_dot)
                day_parts = day.split("-")
                
                temps_part = temps.split("-")
                
                if debug is True:
                    print(" ... chute, day, temps", day_parts, temps_part)
                if len(day_parts) == 3 and len(temps_part) > 0:
                    # foundOne = True
                    
                    temps_parts = temps_part[0].split(":")
                    
                    output = Stamp(day_parts=day_parts, temps_parts=temps_parts, prefix=prefix)
                    if debug is True:
                        print(" ... FOUND", day_parts, temps_parts, " => output {}".format(output))

                    return output

    raise Warning("parse_stamped_filename could not parse stamp for '{}'".format(filename))

def get_3_filenames_from_colour_name(colour_filename: str, debug: bool=False) -> Union[None, Tuple[str, str, str]]:
    
    try:
        if debug is True:
            print("[DEBUG]get_3_filenames_from_colour_name '{}'".format(colour_filename))
        stamp = parse_stamped_filename(filename=colour_filename, ext_with_dot=".png", res_type="colour", debug=debug)
    except Exception as warn:
        msg = "[ERROR]get_3_filenames_from_colour_name: {}".format(warn)
        if debug is True:
            print(msg)
        raise Exception(msg)
    
    depth_filename = colour_filename.replace("colour", "depth")
    try:
        if debug is True:
            print("[DEBUG]get_3_filenames_from_colour_name '{}', depth: {}".format(colour_filename, depth_filename))
        parse_stamped_filename(filename=depth_filename, ext_with_dot=".png", res_type="depth", debug=debug)
    except Exception as warn:
        if debug is True:
            print(msg)
        msg = "[ERROR]get_3_filenames_from_colour_name: {}".format(warn)
        raise Exception()
    
    # for stamp file get rid of -nbpX (nb persons) in filename
    stamp_filename = GetTimestamp(stamp, debug=debug)
    # just for checking
    try:
        if debug is True:
            print("[DEBUG]get_3_filenames_from_colour_name '{}', stamp: {}".format(colour_filename, stamp_filename))
        parse_stamped_filename(filename=stamp_filename, ext_with_dot=".txt", res_type="", debug=debug)
    except Exception as warn:
        msg = "[ERROR]get_3_filenames_from_colour_name: {}".format(warn)
        if debug is True:
            print(msg)
        raise Exception(msg)
    
    return (stamp_filename, depth_filename, colour_filename)

def copy_file(src: str, dst: str):
    if os.path.isfile(dst) is True:
        raise Exception("[ERROR] copy file dst already existing: {} -> {}".format(src, dst))
    if os.path.isfile(src) is False:
        raise Exception("[ERROR] copy file src does not exist: {} -> {}".format(src, dst))
    shutil.copyfile(src=src, dst=dst)
    if os.path.isfile(dst) is False:
        raise Exception("[ERROR] copy file failed: {} -> {}".format(src, dst))

def clean_dir_and_copy_file(info: str, srcdir: str, threeFiles: List[str], dstdir: str):
    shutil.rmtree(path=dstdir)
    if os.path.isdir(dstdir) is True:
        raise Exception("[ERROR]failed to erase dest folder {}".format(dstdir))
    os.mkdir(dstdir)
    if os.path.isdir(dstdir) is False:
        raise Exception("[ERROR]failed to create dest folder {}".format(dstdir))
    for filename in threeFiles:
        if filename is not None:
            try:
                copy_file(src=os.path.join(srcdir, filename), dst=os.path.join(dstdir, filename))
            except Exception as err:
                raise Exception("[ERROR] clean_dir_and_copy_file failed: {}".format(err))
    
    with open(os.path.join(dstdir, "info.txt"), "w") as fout:
        fout.write(info)

def move_file(src: str, dst: str):
    if os.path.isfile(dst) is True:
        raise Exception("[ERROR] moving file dst already existing: {} -> {}".format(src, dst))
    if os.path.isfile(src) is False:
        raise Exception("[ERROR] moving file src does not exist: {} -> {}".format(src, dst))
    shutil.move(src=src, dst=dst)
    if os.path.isfile(dst) is False:
        raise Exception("[ERROR] moving file failed: {} -> {}".format(src, dst))
    if os.path.isfile(src) is True:
        raise Exception("[ERROR] moving file failed: {} -> {}".format(src, dst))

