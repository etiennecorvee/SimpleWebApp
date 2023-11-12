import os
from typing import Union

def parse_stamped_filename(upload_folder: str, filename: str, ext_with_dot: str, res_type: str, debug: bool = False) -> Union[None, float]:
    stem = filename # os.path.basename(filepath)
    day_temps = stem.split("T")
    if debug is True:
        print(" ... day_temps", day_temps)
    if len(day_temps) == 2:
        day = day_temps[0]
        temps = day_temps[1]
        if debug is True:
            print(" ... len 2 ok: day, temps", day, temps, "chute_d-" in day, ".txt" in temps)
        if res_type in temps:
        
            if debug is True:
                print(" ... day, temps", day, temps, "chute_d-" in day, ".txt" in temps)
            if "chute_d-" in day and ext_with_dot in temps:
                day = day.strip("chute_d-")
                temps = temps.strip(ext_with_dot)
                day_parts = day.split("-")
                temps_parts = temps.split(":")
                if debug is True:
                    print(" ... chute, day, temps", day_parts, temps_parts)
                if len(day_parts) == 3 and len(temps_parts) == 3:
                    # foundOne = True
                    
                    if debug is True:
                        print(" ... FOUND", day_parts, temps_parts)

                    filepath = os.path.join(upload_folder, filename)
                    stat = os.stat(filepath)
                    print(" ... stat", type(stat.st_mtime), stat.st_mtime)
                    return stat.st_mtime
                
                # for scan in os.listdir(upload_folder):
                #     if "chute_d-" in scan and ".ppm" in scan:
                #         if debug is True:
                #             print(" ... candidate ppm", scan)
                #         if day in scan and temps in scan:
                #             if "-colour" in scan:
                #                 foundColour = scan
                #             if "-depth" in scan:
                #                 foundDepth = scan
                
    return None