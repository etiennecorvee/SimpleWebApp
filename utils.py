import os
import shutil
import base64
import json
from io import BytesIO
from typing import Union, Tuple, List
# from flask import jsonify
from dataclasses import dataclass
from werkzeug.datastructures.headers import Headers
import cv2

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
            # output += ":"
            output += "-"
    return output

def GetTimestamp(input: Stamp, debug: bool=False) -> str:
    day = GetDayString(input)
    # temps = GetTempsString(input) with -
    temps = input.temps_parts[0] # with :
    
    print(" ... ... GetTimestamp({}) => day={}".format(input, day))
    print(" ... ... GetTimestamp({}) => temps={}".format(input, temps))
    
    if debug is True:
        print("[DEBUG] GetTimestamp from {} -> {} + {}".format(input, day, temps))
    return input.prefix + day + "T" + temps + ".txt"

def parse_stamped_filename(filename: str, ext_with_dot: str, res_type: str, prefix: str="chute_d-", debug: bool = False) -> Stamp:

    debug = True
     
    if debug is True:
        print(" ... input", filename)
        
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
                print(" ... day, temps", day, temps, prefix in day, res_type in temps, "ext_with_dot", ext_with_dot)
            if prefix in day and ext_with_dot in temps:
                day = day.strip(prefix)
                temps = temps.strip(ext_with_dot)
                day_parts = day.split("-")
                
                temps_part = temps.split("-")
                
                if debug is True:
                    print(" ... chute, day, temps", day_parts, " <>", temps_part)
                # if len(day_parts) == 3 and len(temps_part) > 0:
                if len(day_parts) == 3 and len(temps_part) >= 3:
                    # foundOne = True
                    
                    # TODO add var separator in time part
                    # temps_parts = temps_part[0].split(":")
                    temps_parts = temps_part[:3]
                    
                    output = Stamp(day_parts=day_parts, temps_parts=temps_parts, prefix=prefix)
                    if debug is True:
                        print(" ... FOUND", day_parts, temps_parts, " => output {}".format(output))

                    return output

    raise Warning("parse_stamped_filename could not parse stamp for '{}'".format(filename))

def get_4_filenames_from_colour_name(colour_filename: str, debug: bool=False) -> Union[None, Tuple[str, str, str, str]]:
    
    try:
        if debug is True:
            print("[DEBUG]get_4_filenames_from_colour_name '{}'".format(colour_filename))
        stamp = parse_stamped_filename(filename=colour_filename, ext_with_dot=".png", res_type="colour", debug=False)
        print(" ... get_4_filenames_from_colour_name: stamp", stamp)
    except Exception as warn:
        msg = "[ERROR]get_4_filenames_from_colour_name: {}".format(warn)
        if debug is True:
            print(msg)
        raise Exception(msg)
    
    depth_filename = colour_filename.replace("colour", "depth")
    try:
        if debug is True:
            print("[DEBUG]get_4_filenames_from_colour_name '{}', depth: {}".format(colour_filename, depth_filename))
        parse_stamped_filename(filename=depth_filename, ext_with_dot=".png", res_type="depth", debug=False)
    except Exception as warn:
        if debug is True:
            print(msg)
        msg = "[ERROR]get_4_filenames_from_colour_name: {}".format(warn)
        raise Exception()
    
    mm_filename = colour_filename.replace(".png", ".mm")
    try:
        if debug is True:
            print("[DEBUG]get_4_filenames_from_colour_name '{}', mm: {}".format(colour_filename, mm_filename))
        parse_stamped_filename(filename=mm_filename, ext_with_dot=".mm", res_type="colour", debug=False)
    except Exception as warn:
        if debug is True:
            print(msg)
        msg = "[ERROR]get_4_filenames_from_colour_name: {}".format(warn)
        raise Exception()

    # for stamp file get rid of -nbpX (nb persons) in filename
    stamp_filename = GetTimestamp(stamp, debug=debug)
    # just for checking
    try:
        if debug is True:
            print("[DEBUG]get_4_filenames_from_colour_name '{}', stamp: {}".format(colour_filename, stamp_filename))
        # parse_stamped_filename(filename=stamp_filename, ext_with_dot=".txt", res_type="", debug=False)
    except Exception as warn:
        msg = "[ERROR]get_4_filenames_from_colour_name: {}".format(warn)
        if debug is True:
            print(msg)
        raise Exception(msg)
    
    return (stamp_filename, depth_filename, colour_filename, mm_filename)

def copy_file(src: str, dst: str):
    if os.path.isfile(dst) is True:
        raise Exception("[ERROR] copy file dst already existing: {} -> {}".format(src, dst))
    if os.path.isfile(src) is False:
        raise Exception("[ERROR] copy file src does not exist: {} -> {}".format(src, dst))
    shutil.copyfile(src=src, dst=dst)
    if os.path.isfile(dst) is False:
        raise Exception("[ERROR] copy file failed: {} -> {}".format(src, dst))

def clean_dir_and_copy_file(info: str, srcdir: str, nbFiles: int, fourFiles: List[str], dstdir: str):
    shutil.rmtree(path=dstdir)
    if os.path.isdir(dstdir) is True:
        raise Exception("[ERROR]failed to erase dest folder {}".format(dstdir))
    os.mkdir(dstdir)
    if os.path.isdir(dstdir) is False:
        raise Exception("[ERROR]failed to create dest folder {}".format(dstdir))
    for index in range(nbFiles):
        filename = fourFiles[index]
        if filename is not None:
            try:
                copy_file(src=os.path.join(srcdir, filename), dst=os.path.join(dstdir, filename))
            except Exception as err:
                raise Exception("[ERROR] clean_dir_and_copy_file failed: {}".format(err))
    
    with open(os.path.join(dstdir, "info.txt"), "w") as fout:
        print(" ... writing info file: ", os.path.join(dstdir, "info.txt"), info, fourFiles)
        fout.write(info+"\n")
        for index in range(nbFiles):
            filename = fourFiles[index]
            if filename is not None:
                fout.write(filename+"\n")

    print(" ... clean_dir_and_copy_file done")

def printd(debug: bool, msg: str):
    if debug is True:
        print(msg)

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

def move_files_and_update_last(MOVE: bool, info: str, nbFiles: int, fourfiles: List[str], srcDir: str, dstDir: str, lastDir: str, debug: bool=False):
    
    for index in range(nbFiles):
        src = os.path.join(srcDir, fourfiles[index])
        dst = os.path.join(dstDir, fourfiles[index])
        try:
            if MOVE is True:
                printd(debug, "[DEBUG]'{}' moving file '{}' -> '{}'".format(info, src, dst))
                move_file(src=src, dst=dst)
            else:
                printd(debug, "[DEBUG]'{}' copying file '{}' -> '{}'".format(info, src, dst))
                copy_file(src=src, dst=dst)
        except Exception as err:
            raise Exception("[ERROR]move_files_and_update_last: error={}".format(err))
        
    try:
        clean_dir_and_copy_file(info=info, srcdir=dstDir, nbFiles=nbFiles, fourFiles=fourfiles, dstdir=lastDir)
    except Exception as err:
        raise Exception("[ERROR]move_files_and_update_last: error={}".format(err))


def create_dir(dirpath: str):
    if os.path.isdir(dirpath) is False:
        os.mkdir(dirpath)
    if os.path.isdir(dirpath) is False:
        return "dirpath does not exist: {}".format(dirpath)
    return None

def create_dirs(folders: List[str]):
    for folder in folders:
        if create_dir(dirpath=folder) is not None:
            print("[ERROR] create dir {} failed".format(folder))
            raise FileNotFoundError("[ERROR]create_dirs: could not create folder {}".format(folder))

@dataclass
class File:
    name: str
    buffer: BytesIO 
    extension: str

def save_file(upload_folder: str, im_file: File):
    print(" ... save_file 1")
    content=im_file.buffer
    filename=im_file.name
    folder_path = upload_folder
    file_path = os.path.join(folder_path, filename)
    try:
        print(" ... save_file 2")
        with open(file_path, 'wb') as f:
            print(" ... save_file 3")
            f.write(content.read())
    except Exception as err:
        print(" ... save_file error")
        raise Exception("failed writing file: error={}".format(err))

    print(" ... save_file end")
    
def save_file2(upload_folder: str, im_file: File):
    print(" ... save_file 1")
    content=im_file.buffer
    filename=im_file.name
    folder_path = upload_folder
    file_path = os.path.join(folder_path, filename)
    try:
        print(" ... save_file 2")
        with open(file_path, 'wb') as f:
            print(" ... save_file 3")
            f.write(content)
    except Exception as err:
        print(" ... save_file error")
        raise Exception("failed writing file: error={}".format(err))

    print(" ... save_file end")

# before login we could send differnt type of content, now only application/json since we need to add user and password
'''def _get_doc(request_headers: Headers, request_data: bytes, base64mode=False):
    
    # returns the request image content
    
    strInfo = "information"
    strIdentifier = "identifier"
    strNone = "none"

    # dict_out = {
    #     strInfo: "start upload",
    #     strIdentifier: strNone
    # }
    content_file = None

    content_type = request_headers.get('Content-Type')
    # print("[INFO] received doc: content_type: ", content_type)
    print("[INFO] documents content_type received: " + str(content_type))
    accepted_content_type = ["application/octet-stream", "image/jpeg", "image/png"]
    if content_type not in accepted_content_type:
        # dict_out["information"] = "the input request has header of content type " + str(content_type)  + \
        #     " which is not among the accepted ones: "+str(accepted_content_type)
        # dict_out["content_type"] = str(content_type)
        raise Exception("[ERROR] the input request has header of content type: {}".format(str(content_type)))
        # return (dict_out, 400, content_file)

    nb_bytes = len(request_data) # request.data is of type "bytes"
    # print("[INFO] received doc: nb_bytes: ", nb_bytes)
    if nb_bytes == 0:
        raise Exception("[ERROR] cannot upload an empty content")
        # dict_out["information"] = "cannot upload an empty (" + str(nb_bytes) +  " bytes) input content"
        # dict_out["received_bytes"] = nb_bytes
        # return (dict_out, 400, content_file)

    if type(request_data) != bytes:
        # dict_out["information"] = "cannot upload an object wich is a non byte type object:" + str(type(request_data))
        # dict_out["type_input_data"] = str(type(request_data))
        # return (dict_out, 400, content_file)
        raise Exception("[ERROR] cannot upload an object wich is a non byte type object: {}".format(str(type(request_data))))

    if base64mode is True:
        base64_decoded = base64.b64decode(request_data)
        nb_bytes64 = len(base64_decoded)
        if nb_bytes64 == 0:
            # dict_out["information"] = "cannot upload an empty " + str(nb_bytes64) + " object (base64 decoded from an non empty " + str(nb_bytes) + " bytes input): "
            # dict_out["received_bytes"] = nb_bytes
            # dict_out["decoded_base64_bytes"] = nb_bytes64
            # return (dict_out, 400, content_file)
            raise Exception("[ERROR] cannot upload an empty b64 content")
        content_file = base64_decoded
    else:
        content_file = request_data
    
    # return (dict_out, 200, content_file)
    return content_file
'''

# request_headers: Headers, 
def _get_doc(request_data: bytes, base64mode=False):
    
    """ returns the request image content """
    content_file = None

    print(" ... => _get_doc")
    # content_type = request_headers.get('Content-Type')
    # print("[INFO] documents content_type received: " + str(content_type))
    # if content_type != "application/json":
    #     raise Exception("[ERROR] the input request has header of content type: {}".format(str(content_type)))

    print(" ... _get_doc, check data")
    if request_data is None:
        raise Exception("[ERROR] the input request does not have any json data")

    # print(" ... _get_doc, check type:", type(request_data))
    # if isinstance(request_data, bytes) is False:
    #     raise Exception("[ERROR] the input request data is not of type bytes: {}".format(type(request_data)))

    # print(" ... _get_doc, load data")
    # request_data = json.loads(request_data.decode('utf-8'))
    
    print(" ... _get_doc, check load data")
    if isinstance(request_data, dict) is False:
        raise Exception("[ERROR] the converted input request data is not of type dict: {}".format(type(request_data)))
    
    print(" ... _get_doc, check content")
    if "username" not in request_data:
        raise Exception("[ERROR] the input request data does not contain username")
    if "password" not in request_data:
        raise Exception("[ERROR] the input request data does not contain password")
    if "data" not in request_data:
        raise Exception("[ERROR] the input request data does not contain data")
    request_data = request_data["data"]
    
    
    request_data = request_data.encode("iso-8859-1") #  b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x01@\x00\x00\x00\xf0\x08\x02\x00\x00\x00\xfeO*<\x00\x01\x00\x00I
    # print(" ... typer", type(request_data), request_data)
    print(" ... typer", type(request_data))
    
    # base64.b64decode(request_data['data'])
    
    nb_bytes = len(request_data) # request.data is of type "bytes"
    if nb_bytes == 0:
        raise Exception("[ERROR] cannot upload an empty content")


    print(" ... request_data", type(request_data))

    # if type(request_data) != bytes:
    #     raise Exception("[ERROR] cannot upload an object wich is a non byte type object: {}".format(str(type(request_data))))

    if base64mode is True:
        base64_decoded = base64.b64decode(request_data)
        nb_bytes64 = len(base64_decoded)
        if nb_bytes64 == 0:
            raise Exception("[ERROR] cannot upload an empty b64 content")
        content_file = base64_decoded
    else:
        content_file = request_data
    
    return content_file

def save_doc(request_content_length: int, request_content_type: str, 
             filenamestem: str, content_file, dstDir: str):
    # if status_code != 200:
    #     raise ValueError
    #     return jsonify(json_content), status_code
    print(" ... save_doc")
    if request_content_length == 0:
        print(" ... save_doc, request_content_length 0")
        raise FileExistsError("[ERROR] empty binary message")
        # return {"information": "empty binary message"}, 400

    # print(" ... save_doc, request_content_type", request_content_type)

    file_extension = "png"

    # before login auth
    # if request_content_type == "application/octet-stream":
    #     file_extension = "bin"
    # elif request_content_type in ["image/jpeg", "image/jpg"]:
    #     file_extension = "jpeg"
    # elif request_content_type == "image/png":
    #     file_extension = "png"
    # else:
    #     raise FileExistsError("[ERROR] {} not handled".format(request_content_type))

    # filename = stamp + "-depth." + file_extension
    filename = filenamestem + "." + file_extension
    print(" ... save_doc, filename", filename)
    # try:
    #     buffer = BytesIO(content_file) # (content)
    # except Exception as err:
    #     msgerr = "failed to convert {} to ByesIO".format(type(content_file))
    #     print("[ERROR]", msgerr)
    #     raise Exception(msgerr)
    
    buffer = content_file
    
    file = File(filename, buffer, file_extension)
    try:
        print(" ... save_doc: save to file")
        save_file2(upload_folder=dstDir, im_file=file)
    except Exception as err:
        print(" ... save_doc: failed to save")
        raise FileExistsError("[ERROR] save_doc: failed to save file: {}".format(err))

    print(" ... save_doc done")
    # print(" ... filename", filename)
    # filename = secure_filename(filename)
    # print(" ... filename", filename)
    # img = os.path.join(app.config['UPLOAD'], filename)
    # print(" ... img", img)
    # return render_template('img_render.html', img=img)

def get_stamp_from_request_stamp_data_and_create_empty_file(textData: str, dstDir: str):

    # why 'stamp=' added ?
    if "stamp=" not in textData:
        raise ValueError("get_stamp_from_request_stamp_data: 'stam=' not found in received request dat content of stamp filename: {}".format(textData))
    textData = textData.strip("stamp=")
    
    # re establish : instead of - in temps
    textData_parts = textData.split("T")
    if len(textData_parts) != 2:
        raise ValueError("get_stamp_from_request_stamp_data: request dat content of stamp filename: {} not have 2 parts".format(textData))
    # textData_parts[1] = textData_parts[1].replace("-", ":")
    textData = textData_parts[0] + "T" + textData_parts[1]

    filename = os.path.join(dstDir, textData + ".txt")
    try:
        with open(filename, "w") as fout:
            print("[INFO] get_stamp_from_request_stamp_data_and_create_empty_file: creating simple stamp file ", filename)
    except Exception as err:
        msg = "[ERROR] could not create output file {} error={}".format(filename, err)
        print(msg)
        raise FileExistsError(msg)

def _get_image_content_b64(imagepath: str) -> str:
    with open(imagepath, "rb") as fin:
        content = fin.read() # bytes
        image_b = base64.b64encode(content) # image_b.read())
        image_b64 = image_b.decode('utf-8')
        # print(" ... content", type(content), type(image_b), type(image_b64)) #  <class 'bytes'> <class 'bytes'> <class 'str'>
        return image_b64

def draw_text(displayImagPath: str, infoProcess: str, outputPath: str="temp.png"):
    displayImg = cv2.imread(displayImagPath)
    height = displayImg.shape[0]
    displayImg = cv2.putText(img=displayImg, text=infoProcess, org=(10, int(height/2)), 
                fontFace=cv2.FONT_HERSHEY_DUPLEX, fontScale=0.5, color=(54, 212, 204), thickness=1)
    cv2.imwrite(filename=outputPath, img=displayImg)
    