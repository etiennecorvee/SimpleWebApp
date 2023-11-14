import os
import json
from flask import Flask
from flask import Response, request, jsonify, render_template, make_response
from werkzeug.utils import secure_filename
from logging import getLogger
import base64
from io import BytesIO
from dataclasses import dataclass
from uuid import uuid1
import subprocess
import pathlib
import requests
import cv2
from utils import parse_stamped_filename, get_stat_time, get_3_filenames_from_colour_name, move_file, clean_dir_and_copy_file

'''
/stamp POST
  => /uploads/stamp.txt
  
/colour POST
  => /uploads/stamp-colour.png
  
/depth POST
  => /uploads/stamp-depth.png

if colour sent from RGBD
/process/<stamped_colour>
 /uploads/stamp-colour.png => mmdetection => /uploads/stamp-colour.mm
   ok: move /uploads/stamp + colour + depth + mm => /processed
   ko: move /uploads/stamp + colour + depth => failed_mm
 
if no colour sent from RGBD
/nocolour/<stamp>
  move /uploads/stamp + colour + depth => /processed

/result GET  <=  html page request every N sec
  TODO display latest from timestamp filename not stat

TODO night case : no object detected at all in mm => <=> nocolour

TODO purge: if filename too old => moved to /backup_results

'''

logger = getLogger(__name__)

app = Flask(__name__)

DEBUG = True

upload_folder = "/home/ubuntu/SimpleWebApp/uploads"
last_folder = "/home/ubuntu/SimpleWebApp/last"
processed_folder = "/home/ubuntu/SimpleWebApp/processed"
failed_mm_folder = "/home/ubuntu/SimpleWebApp/failed_mm"

# process_cmd = ["python3", "simul_mmdetection.py"]
process_output_dir = "/home/ubuntu/SimpleWebApp"

app.config['UPLOAD'] = upload_folder
app.config['PROCESSED'] = processed_folder
app.config['FAILED_MM'] = failed_mm_folder
app.config['LAST'] = last_folder

def create_dir(dirpath: str):
    if os.path.isdir(dirpath) is False:
        os.mkdir(dirpath)
    if os.path.isdir(dirpath) is False:
        return "dirpath does not exist: {}".format(dirpath)
    return None

for folder in [app.config['UPLOAD'], app.config['PROCESSED'], app.config['FAILED_MM'], app.config['LAST']]:
    if create_dir(dirpath=folder) is not None:
        logger.error("[ERROR] create dir {} failed".format(folder))
        print("[ERROR] create dir {} failed".format(folder))
        exit(1)

@dataclass
class File:
    name: str
    buffer: BytesIO 
    extension: str

def save_file(upload_folder: str, im_file: File):
    content=im_file.buffer
    filename=im_file.name
    folder_path = upload_folder
    file_path = os.path.join(folder_path, filename)
    try:
        with open(file_path, 'wb') as f:
            f.write(content.read())
    except Exception as err:
        raise Exception("failed writing file: error={}".format(err))

def _get_doc(base64mode=False):
    
    """ returns the request image content """
    
    strInfo = "information"
    strIdentifier = "identifier"
    strNone = "none"

    dict_out = {
        strInfo: "start upload",
        strIdentifier: strNone
    }
    content_file = None

    content_type = request.headers.get('Content-Type')
    # print("[INFO] received doc: content_type: ", content_type)
    logger.info("/documents content_type received: " + str(content_type))
    accepted_content_type = ["application/octet-stream", "image/jpeg", "image/png"]
    if content_type not in accepted_content_type:
        dict_out["information"] = "the input request has header of content type " + str(content_type)  + \
            " which is not among the accepted ones: "+str(accepted_content_type)
        dict_out["content_type"] = str(content_type)
        return (dict_out, 400, content_file)

    nb_bytes = len(request.data) # request.data is of type "bytes"
    # print("[INFO] received doc: nb_bytes: ", nb_bytes)
    if nb_bytes == 0:
        dict_out["information"] = "cannot upload an empty (" + str(nb_bytes) +  " bytes) input content"
        dict_out["received_bytes"] = nb_bytes
        return (dict_out, 400, content_file)

    if type(request.data) != bytes:
        dict_out["information"] = "cannot upload an object wich is a non byte type object:" + str(type(request.data))
        dict_out["type_input_data"] = str(type(request.data))
        return (dict_out, 400, content_file)

    if base64mode is True:
        base64_decoded = base64.b64decode(request.data)
        nb_bytes64 = len(base64_decoded)
        if nb_bytes64 == 0:
            dict_out["information"] = "cannot upload an empty " + str(nb_bytes64) + " object (base64 decoded from an non empty " + str(nb_bytes) + " bytes input): "
            dict_out["received_bytes"] = nb_bytes
            dict_out["decoded_base64_bytes"] = nb_bytes64
            return (dict_out, 400, content_file)
        content_file = base64_decoded
    else:
        content_file = request.data
    
    return (dict_out, 200, content_file)

@app.route("/hello")
def hello():
    return "<h1 style='color:blue'>Hello There!</h1>"

@app.route("/")
def upload_file():
    return render_template('img_render.html')

@app.route("/nocolour/<colour_filename>", methods=["POST"])
def nocolour(colour_filename: str):
    try:
        threefiles = get_3_filenames_from_colour_name(colour_filename=colour_filename, debug=DEBUG)
    except Exception as err:
        return {"details": "nocolour case: getting the 3 filenames failed with error: {}".format(err)}, 400
    
    # move only the stamp and depth
    for index in range(2):
        src = os.path.join(app.config['UPLOAD'], threefiles[index])
        dst = os.path.join(app.config['PROCESSED'], threefiles[index])
        try:
            move_file(src=src, dst=dst)
        except Exception as err:
            return {"details": "noclour case: ok but moving file failed: {}".format(err)}, 400
        
        try:
            clean_dir_and_copy_file(info="nocolour", srcdir=app.config['PROCESSED'], threeFiles=threefiles, dstdir=app.config['LAST'])
        except Exception as err:
            return {"details": "noclour case: ok but copy to last file failed: {}".format(err)}, 400

@app.route("/process/<colour_filename>", methods=["POST"])
def process(colour_filename: str):
    colourPath = os.path.join(upload_folder, colour_filename)
    if os.path.isfile(colourPath) is False:
        return {"details": "colour image path does not exist: {}".format(colourPath)}, 400
    
    try:
        threefiles = get_3_filenames_from_colour_name(colour_filename=colour_filename, debug=DEBUG)
    except Exception as err:
        # colour image to be moved to failed folder ?
        return {"details": "process: getting the 3 filenames failed with error: {}".format(err)}, 400
    
    cmd_line = '''python -c "import sys; print(sys.executable)"
                  source /home/ubuntu/miniconda3/etc/profile.d/conda.sh
                  conda activate openmmlab
                  python /home/ubuntu/mmdetection/demo/image_demo.py {} /home/ubuntu/mmdetection/rtmdet_tiny_8xb32-300e_coco.py --weights /home/ubuntu/mmdetection/rtmdet_tiny_8xb32-300e_coco_20220902_112414-78e30dcc.pth --device cpu'''.format(colourPath)
    
    print(" ... cmd_line => ", cmd_line)
    
    output = subprocess.run(cmd_line, executable='/bin/bash', shell=True, capture_output=True)

    # print(" ... stdout")
    # print(bytes.decode(output.stdout))
    # print(" ... stderr")
    # print(bytes.decode(output.stderr))
    # print(" ... return code", output.returncode)
    if output.returncode != 0:
        print(" ... stdout")
        print(bytes.decode(output.stdout))
        print(" ... stderr")
        print(bytes.decode(output.stderr))
        
        # print("[DEBUG] threefiles: {}".format(threefiles))
        # for filename in threefiles:
        #     src = os.path.join(app.config['UPLOAD'], filename)
        #     dst = os.path.join(app.config['FAILED_MM'], filename)
        #     print(os.path.isfile(src), src, dst)
        # exit(1)
        
        for filename in threefiles:
            src = os.path.join(app.config['UPLOAD'], filename)
            dst = os.path.join(app.config['FAILED_MM'], filename)
            try:
                move_file(src=src, dst=dst)
            except Exception as err:
                return {"details": "mmdetection ok but moving file failed: {}".format(err)}, 400
        
            try:
                clean_dir_and_copy_file(info="failed_mm", srcdir=app.config['PROCESSED'], threeFiles=threefiles, dstdir=app.config['LAST'])
            except Exception as err:
                return {"details": "noclour case: ok but copy to last file failed: {}".format(err)}, 400
        
        return {"details": "process failed: returned code {} error={}".format(output.returncode, bytes.decode(output.stderr))}, 400
    else:
        output_dir = os.path.join(process_output_dir, "outputs", "preds")
        outputfilename = colour_filename.strip(".png") + ".json"
        jsonPredPath = os.path.join(output_dir, outputfilename)
        if os.path.isfile(jsonPredPath) is False:
            # raise FileNotFoundError("mmdetee result predition file does not exist: {}".format())
            return {"details": "mmdetee result predition file does not exist: {}".format(jsonPredPath)}, 400
        
        # see TODO.py
        
        inputPath = os.path.abspath(colourPath)
        outputPath = inputPath.replace(pathlib.Path(inputPath).suffix, ".mm")
        try:
            with open(outputPath, "r") as fin:
                data = json.loads(fin.read())
        except Exception as err:
            msg = "[ERROR] could not parse json file: {}: error={}".format(outputPath, err)
            return {"details": "mmedetection failed: {}".format(msg)}, 400
        
        print(" ... data", data)
        
        for filename in threefiles:
            src = os.path.join(app.config['UPLOAD'], filename)
            dst = os.path.join(app.config['PROCESSED'], filename)
            try:
                move_file(src=src, dst=dst)
            except Exception as err:
                return {"details": "mmdetection ok but moving file failed: {}".format(err)}, 400
                
            src = os.path.join(app.config['PROCESSED'], filename)
            dst = os.path.join(app.config['LAST'], filename)
            try:
                clean_dir_and_copy_file(info="processed", srcdir=app.config['PROCESSED'], threeFiles=threefiles, dstdir=app.config['LAST'])
            except Exception as err:
                return {"details": "noclour case: ok but copy to last file failed: {}".format(err)}, 400
        
        return { "details": json.dumps(data) }, 200  
        # return {"details": "process success"}, 200
    return {"details": "failure"}, 400

@app.route("/stamp", methods=["POST"])
def stamp():
    content_type = request.headers.get('Content-Type')
    nb_bytes = len(request.data) # request.data is of type "bytes"
    textData = request.data.decode("utf-8")
    print("[INFO] received stamp: ", content_type, nb_bytes, request.data, " => '{}'".format(textData))
    
    filename = os.path.join(upload_folder, textData + ".txt")
    try:
        with open(filename, "w") as fout:
            print("[INFO] creating simple stamp file ", filename)
    except Exception as err:
        msg = "[ERROR] could not create output file {} error={}".format(filename, err)
        return {"details": msg}, 400
    
    return {"details": "stamp upload success"}, 200

@app.route("/colour/<colourstem>", methods=["POST"])
def colour(colourstem: str):
    base64mode = False
    (json_content, status_code, content_file) = _get_doc(base64mode=base64mode)

    if status_code != 200:
        return jsonify(json_content), status_code
    
    if request.content_length == 0:
        return {"information": "empty binary message"}, 400

    if request.content_type == "application/octet-stream":
        file_extension = "bin"
    elif request.content_type in ["image/jpeg", "image/jpg"]:
        file_extension = "jpeg"
    elif request.content_type == "image/png":
        file_extension = "png"
    else:
        return {"details": "{} not handled".format(request.content_type)}, 400

    # filename = stamp + "-colour." + file_extension
    filename = colourstem + "." + file_extension
    buffer = BytesIO(content_file) # (content)
    file = File(filename, buffer, file_extension)
    try:
        save_file(upload_folder=upload_folder, im_file=file)
    except Exception as err:
        return {"details" : "failed to save file"}, 400

    return {"details": "colour upload success"}, 200

@app.route("/depth/<depthstem>", methods=["POST"])
def depth(depthstem: str):
    base64mode = False
    (json_content, status_code, content_file) = _get_doc(base64mode=base64mode)
    
    if status_code != 200:
        return jsonify(json_content), status_code
    
    if request.content_length == 0:
        return {"information": "empty binary message"}, 400

    if request.content_type == "application/octet-stream":
        file_extension = "bin"
    elif request.content_type in ["image/jpeg", "image/jpg"]:
        file_extension = "jpeg"
    elif request.content_type == "image/png":
        file_extension = "png"
    else:
        return {"details": "{} not handled".format(request.content_type)}, 400

    # filename = stamp + "-depth." + file_extension
    filename = depthstem + "." + file_extension
    buffer = BytesIO(content_file) # (content)
    file = File(filename, buffer, file_extension)
    try:
        save_file(upload_folder=upload_folder, im_file=file)
    except Exception as err:
        return {"details" : "failed to save file"}, 400

    # print(" ... filename", filename)
    # filename = secure_filename(filename)
    # print(" ... filename", filename)
    # img = os.path.join(app.config['UPLOAD'], filename)
    # print(" ... img", img)
    # return render_template('img_render.html', img=img)

    return {"details": "depth upload success"}, 200

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
    cv2.putText(img=displayImg, text=infoProcess, org=(10, height-10), 
                fontFace=cv2.FONT_HERSHEY_DUPLEX, fontScale=3.0, color=(54, 212, 204), thickness=3)
    cv2.imwrite(filename=outputPath, img=displayImg)

@app.route('/result/<string:camId>', methods=['GET'])
def result_api(camId: str):
    
    infoPath = os.path.join(app.config['LAST'], "info.txt")
    if os.path.isfile(infoPath) is False:
        return _get_image_content_b64("images/empty.png")
    
    with open(infoPath, "r") as fin:
        lines = fin.readlines()
        if len(lines) < 3 : # info, stamp.png, depth.png + colour.png + colour.mm
            # TODO draw on image or message on html
            return _get_image_content_b64("images/error.png")

        infoProcess = None
        stampFilename = None
        depthFilename = None
        colourFilename = None
        mmFilename = None
        
        for index in range(len(lines)):
            if index==0: # info
                infoProcess = lines[index]
            elif index==1: # stamp.png
                stampFilename = lines[index]
                if ".txt" not in stampFilename:
                    draw_text(displayImagPath="images/error.png", 
                        infoProcess=infoProcess, outputPath="temp.png")
                    return _get_image_content_b64("temp.png")
            elif index==2: # depth.png
                depthFilename = lines[index]
                if "depth" not in depthFilename or ".png" not in depthFilename:
                    draw_text(displayImagPath="images/error.png", 
                        infoProcess=infoProcess+" depth png not found in {}".format(depthFilename), outputPath="temp.png")
                    return _get_image_content_b64("temp.png")
            elif index==3: # colour.png
                colourFilename = lines[index]
                if "colour" not in colourFilename or ".png" not in colourFilename:
                    draw_text(displayImagPath="images/error.png", 
                        infoProcess=infoProcess+" colour png not found in {}".format(colourFilename), outputPath="temp.png")
                    return _get_image_content_b64("temp.png")
            elif index==4: # colour.mm
                mmFilename = lines[index]
                if "colour" not in mmFilename or ".mm" not in mmFilename:
                    draw_text(displayImagPath="images/error.png", 
                        infoProcess=infoProcess+" colour mm not found in {}".format(colourFilename), outputPath="temp.png")
                    return _get_image_content_b64("temp.png")

        if os.path.isfile(os.path.join(app.config['LAST'], stampFilename)) is False:
            draw_text(displayImagPath="images/error.png", 
                infoProcess=infoProcess+" stamp file not found {}".format(stampFilename), outputPath="temp.png")
            return _get_image_content_b64("images/error.png")
        if os.path.isfile(os.path.join(app.config['LAST'], depthFilename)) is False:
            draw_text(displayImagPath="images/error.png", 
                infoProcess=infoProcess+" depth file not found {}".format(depthFilename), outputPath="temp.png")
            return _get_image_content_b64("images/error.png")
        
        displayImagPath = os.path.join(app.config['LAST'], depthFilename)
        displayImg = cv2.imread(displayImagPath)
        height = displayImg.shape[0]
        # width = displayImg.shape[1]
        cv2.putText(img=displayImg, text=infoProcess, org=(10, height-10), fontFace=cv2.FONT_HERSHEY_DUPLEX, fontScale=3.0, color=(54, 212, 204), thickness=3)
        # if os.path.isfile(os.path.join(app.config['LAST'], colourFilename)) is True:
        if os.path.isfile(os.path.join(app.config['LAST'], mmFilename)) is True:
            with open(os.path.join(app.config['LAST'], mmFilename), "r") as fjson:
                data = json.loads(fjson.read())
                print(" ... mmdetection data", data)
                try:
                    for obj in data['predictions']:
                        if obj['class'] == 'person':
                            left = int(obj['bbox'][0])
                            top = int(obj['bbox'][1])  
                            right = int(obj['bbox'][2])
                            bottom = int(obj['bbox'][3])
                            cv2.rectangle(displayImg, (left, top), (right, bottom), (25,50,200), 2)
                            cv2.putText(img=displayImg, text=obj['class'],
                                org=(left, top), fontFace=cv2.FONT_HERSHEY_DUPLEX, fontScale=1.0, color=(125, 246, 55), thickness=2)
                        # TODO use a specific name
                    cv2.imwrite(filename="temp.png", img=displayImg)
                    _get_image_content_b64("temp.png")
                except Exception as err:
                    print("[ERROR] {}".format(err))
                    draw_text(displayImagPath="images/error.png", 
                        infoProcess=infoProcess+" draw mm res failed", outputPath="temp.png")
                    return _get_image_content_b64("temp.png")
        else:
            draw_text(displayImagPath=displayImagPath, 
                infoProcess=infoProcess+" no mm res", outputPath="temp.png")
            _get_image_content_b64("temp.png")

        return _get_image_content_b64("images/error.png")
            
    #             displayImagPath = os.path.join(app.config['LAST'], line)
    #             if os.path.isfile(displayImagPath) is False:
    #                 errorMsg.append(line)

                
                
                
    #     displayImagPath = cv2.imread("images/empty.png")
        
        
    #     cv2.putText(img = displayImg, text = obj['class'],
    #                             org = (left, top),
    #                             fontFace = cv2.FONT_HERSHEY_DUPLEX,
    #                             fontScale = 1.0,
    #                             color = (125, 246, 55),
    #                             thickness = 2)
    
    
    # clean_dir_and_copy_file(info="nocolour", srcfile=src, dstdir=os.path.join(app.config['LAST'], dstfile=dst))
    
    
    
    
    
    # # print(" ... result")
    # max_st_mtime = 0.0
    # corr_filename = None
    # for filename in os.listdir(upload_folder):
    #     # print(filename)
    #     try:
    #         parse_stamped_filename(filename=filename, ext_with_dot=".png", res_type="depth", debug=False)
    #         st_mtime = get_stat_time(filepath = os.path.join(upload_folder, filename))
    #         if st_mtime > max_st_mtime:
    #             max_st_mtime = st_mtime
    #             corr_filename = filename
    #     except Exception as warn:
    #         print("[INFO]{}".format(warn))
    
    # if corr_filename is not None:
        
    #     mmfile = corr_filename.strip( pathlib.Path(corr_filename).suffix)
    #     print(" ... mmfile", mmfile)
    #     mmfile = mmfile.strip("-depth")
    #     print(" ... mmfile", mmfile)
    #     mmfile += "-colour.mm"
    #     mmfile = os.path.join(upload_folder, mmfile)
        
    #     displayImagPath = os.path.join(upload_folder, corr_filename)
        
    #     print(" .. mmfile", mmfile)
    #     if os.path.isfile(mmfile) is True:
    #         displayImg = cv2.imread(displayImagPath)
    #         print(" .. exist")
    #         with open(mmfile, "r") as fjson:
    #             data = json.loads(fjson.read())
    #             print(" ... mmdetection data", data)
    #             try:
    #                 for obj in data['predictions']:
    #                     if obj['class'] == 'person':
    #                         left = int(obj['bbox'][0])
    #                         top = int(obj['bbox'][1])  
    #                         right = int(obj['bbox'][2])
    #                         bottom = int(obj['bbox'][3])
    #                         cv2.rectangle(displayImg, (left, top), (right, bottom), (25,50,200), 2)
    #                         cv2.putText(img = displayImg, text = obj['class'],
    #                             org = (left, top),
    #                             fontFace = cv2.FONT_HERSHEY_DUPLEX,
    #                             fontScale = 1.0,
    #                             color = (125, 246, 55),
    #                             thickness = 2)
    #                     # TODO use a specific name
    #                 cv2.imwrite(filename="temp.png", img=displayImg)
    #                 displayImagPath = "temp.png"
    #             except Exception as err:
    #                 print("[ERROR] {}".format(err))
    #                 return _get_image_content_b64("images/error.png")
        
    #     return _get_image_content_b64(displayImagPath)
    # else:
    #     return _get_image_content_b64("images/empty.png")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001)
