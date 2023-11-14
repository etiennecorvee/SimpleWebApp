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
    for item in input.day_parts:
        output += item
    return output
    
def GetTempsString(input: Stamp) -> str:
    output = ""
    for item in input.temps_parts:
        output += item
    return output

def GetTimestamp(input: Stamp) -> str:
    return input.prefix + GetDayString(input) + "T" + GetTempsString(input) + ".txt"

def parse_stamped_filename(filename: str, ext_with_dot: str, res_type: str, debug: bool = False) -> Stamp:
    stem = filename # os.path.basename(filepath)
    day_temps = stem.split("T")
    if debug is True:
        print(" ... day_temps", day_temps)
    if len(day_temps) == 2:
        day = day_temps[0]
        temps = day_temps[1]
        if debug is True:
            print(" ... len 2 ok: day, temps", day, temps, "chute_d-" in day, res_type in temps)
        if res_type in temps:
        
            if debug is True:
                print(" ... day, temps", day, temps, "chute_d-" in day, res_type in temps)
            if "chute_d-" in day and ext_with_dot in temps:
                day = day.strip("chute_d-")
                temps = temps.strip(ext_with_dot)
                day_parts = day.split("-")
                
                # temps_parts = temps.split(":")
                temps_parts = temps.split("-")
                
                if debug is True:
                    print(" ... chute, day, temps", day_parts, temps_parts)
                if len(day_parts) == 3 and len(temps_parts) == 3:
                    # foundOne = True
                    
                    if debug is True:
                        print(" ... FOUND", day_parts, temps_parts)

                    return Stamp(day_parts=day_parts, temps_parts=temps_parts)

    raise Warning("parse_stamped_filename could not parse stamp for '{}'".format(filename))

def get_3_filenames_from_colour_name(colour_filename: str, debug: bool=False) -> Union[None, Tuple[str, str, str]]:
    
    try:
        stamp = parse_stamped_filename(filename=colour_filename, ext_with_dot=".png", res_type="colour", debug=debug)
    except Exception as warn:
        raise Exception("[ERROR]get_3_filenames_from_colour_name: {}".format(warn))
    
    depth_filename = colour_filename.replace("colour", "depth")
    try:
        parse_stamped_filename(filename=depth_filename, ext_with_dot=".png", res_type="colour", debug=debug)
    except Exception as warn:
        raise Exception("[ERROR]get_3_filenames_from_colour_name: {}".format(warn))
    
    # for stamp file get rid of -nbpX (nb persons) in filename
    stamp_filename = GetTimestamp(stamp)
    # just for checking
    try:
        parse_stamped_filename(filename=stamp_filename, ext_with_dot=".txt", res_type="", debug=debug)
    except Exception as warn:
        raise Exception("[ERROR]get_3_filenames_from_colour_name: {}".format(warn))
    
    return (stamp_filename, depth_filename, colour_filename)

def move_file(src: str, dst: str):
    if os.path.isfile(dst) is True:
        raise Exception("[ERROR] mmdetection ok but moving file dst already existing: {} -> {}".format(src, dst))
    if os.path.isfile(src) is False:
        raise Exception("[ERROR] mmdetection ok but moving file src does not exist: {} -> {}".format(src, dst))
    shutil.move(src=src, dst=dst)
    if os.path.isfile(dst) is False:
        raise Exception("[ERROR] mmdetection ok but moving file failed: {} -> {}".format(src, dst))
    if os.path.isfile(src) is True:
        raise Exception("[ERROR] mmdetection ok but moving file failed: {} -> {}".format(src, dst))

