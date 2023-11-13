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

from utils import parse_stamped_filename

# loop to launch mmdetectio  or triggered by request ?
# can i easily add a manager here ... yes deamon ?

logger = getLogger(__name__)

app = Flask(__name__)

upload_folder = "/home/ubuntu/SimpleWebApp/uploads"
# process_cmd = ["python3", "simul_mmdetection.py"]
process_output_dir = "/home/ubuntu/SimpleWebApp"

app.config['UPLOAD'] = upload_folder

# def get_process_cmd(inputImagePath: str):
#     # process_cmd = ["conda", "run", "-n", "openmmlab",
#     #            "python", "/home/ubuntu/mmdetection/demo/image_demo.py", "/home/ubuntu/mmdetection/demo/demo.jpg",
#     #            "/home/ubuntu/mmdetection/rtmdet_tiny_8xb32-300e_coco.py",
#     #            "--weights", "/home/ubuntu/mmdetection/rtmdet_tiny_8xb32-300e_coco_20220902_112414-78e30dcc.pth", "--device", "cpu"]
    
#     process_cmd = ["/home/ubuntu/miniconda3/bin/conda", "run", "-n", "openmmlab",
#                "python", "/home/ubuntu/mmdetection/demo/image_demo.py", 
#                inputImagePath,
#                "/home/ubuntu/mmdetection/rtmdet_tiny_8xb32-300e_coco.py",
#                "--weights", "/home/ubuntu/mmdetection/rtmdet_tiny_8xb32-300e_coco_20220902_112414-78e30dcc.pth", "--device", "cpu"]
    
#     print("command line:")
#     for i in process_cmd:
#         print(i, end=" ")
#     print("\n")
    
#     return process_cmd

# get_process_cmd(inputImagePath="<inputImagePath>")

def create_dir(dirpath: str):
    if os.path.isdir(dirpath) is False:
        os.mkdir(dirpath)
    if os.path.isdir(dirpath) is False:
        return "dirpath does not exist: {}".format(dirpath)
    return None

if create_dir(dirpath=upload_folder) is not None:
    logger.error("[ERROR] create dir upload folder failed")
    print("[ERROR] create dir upload folder failed")
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

@app.route("/process/<colour_filename>", methods=["POST"])
def process(colour_filename: str):
    colourPath = os.path.join(upload_folder, colour_filename)
    if os.path.isfile(colourPath) is False:
        return {"details": "colour image path does not exist: {}".format(colourPath)}, 400
    
    # cmd_line = '''python -c "import sys; print(sys.executable)"
    #               source /home/ubuntu/miniconda3/etc/profile.d/conda.sh
    #               conda activate openmmlab
    #               python /home/ubuntu/mmdetection/demo/image_demo.py /home/ubuntu/SimpleWebApp/uploads/chute_d-2023-11-01T13:04:39.014000-nbp1-colour.png /home/ubuntu/mmdetection/rtmdet_tiny_8xb32-300e_coco.py --weights /home/ubuntu/mmdetection/rtmdet_tiny_8xb32-300e_coco_20220902_112414-78e30dcc.pth --device cpu'''
    
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
        return { "details": json.dumps(data) }, 200  
        # return {"details": "process success"}, 200
    return {"details": "failure"}, 400
    
    # try:
    #     process_cmd = get_process_cmd(inputImagePath = colourPath)
    # except Exception as err:
    #     # raise FileExistsError("colour image filename does not exist: {}: error={}".format(colourPath, err))
    #     return {"details": "colour image filename does not exist: {}: error={}".format(colourPath, err)}, 400
    
    # print(" ... cmdline", process_cmd)
    # proc = subprocess.Popen(process_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    # (out, err) = proc.communicate(timeout=5)
    # out = out.decode("utf-8") # bytes to string
    # err = err.decode("utf-8") # bytes to string
    
    # if out != "":
    #     print("[INFO] process: out", out)
    
    # print(" ... proc.returncode", type(proc.returncode), proc.returncode)
    # if proc.returncode != 0:
    #     return {"details": "process failed: returned code {} error={}".format(proc.returncode, err)}, 400
    
    # if err != "":
    #     print("[ERROR] process: err", err)
    #     return {"details": "process failed"}, 400
    # else:
        
    #     output_dir = os.path.join(process_output_dir, "outputs", "preds")
    #     outputfilename = colour_filename.strip(".png") + ".json"
    #     jsonPredPath = os.path.join(output_dir, outputfilename)
    #     if os.path.isfile(jsonPredPath) is False:
    #         # raise FileNotFoundError("mmdetee result predition file does not exist: {}".format())
    #         return {"details": "mmdetee result predition file does not exist: {}".format(jsonPredPath)}, 400
        
    #     # see TODO.py
        
    #     return {"details": "process success"}, 200

@app.route("/stamp", methods=["POST"])
def stamp():
    content_type = request.headers.get('Content-Type')
    nb_bytes = len(request.data) # request.data is of type "bytes"
    text = request.data.decode("utf-8")
    print("[INFO] received stamp: ", content_type, nb_bytes, request.data, text)
    
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

@app.route('/result/<string:camId>', methods=['GET'])
def result_api(camId: str):
    
    # print(" ... result")
    
    max_st_mtime = 0.0
    corr_filename = None
    for filename in os.listdir(upload_folder):
        # print(filename)
        st_mtime = parse_stamped_filename(upload_folder=upload_folder, 
                                          filename=filename, 
                                          ext_with_dot=".png", 
                                          res_type="depth", 
                                          debug=False)
        # if st_mtime is None:
        #     return _get_image_content_b64("error.png")
        if st_mtime is not None:
            # print(" ... st_mtime", st_mtime, max_st_mtime)
            if st_mtime > max_st_mtime:
                max_st_mtime = st_mtime
                corr_filename = filename
    
    if corr_filename is not None:
        
        mmfile = corr_filename.strip( pathlib.Path(corr_filename).suffix)
        print(" ... mmfile", mmfile)
        mmfile = mmfile.strip("-depth")
        print(" ... mmfile", mmfile)
        mmfile += "-colour.mm"
        mmfile = os.path.join(upload_folder, mmfile)
        
        
        displayImagPath = os.path.join(upload_folder, corr_filename)
        
        print(" .. mmfile", mmfile)
        if os.path.isfile(mmfile) is True:
            displayImg = cv2.imread(displayImagPath)
            print(" .. exist")
            with open(mmfile, "r") as fjson:
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
                            cv2.putText(img = displayImg, text = obj['class'],
                                org = (left, top),
                                fontFace = cv2.FONT_HERSHEY_DUPLEX,
                                fontScale = 1.0,
                                color = (125, 246, 55),
                                thickness = 2)
                        # TODO use a specific name
                    cv2.imwrite(filename="temp.png", img=displayImg)
                    displayImagPath = "temp.png"
                except Exception as err:
                    print("[ERROR] {}".format(err))
                    return _get_image_content_b64("error.png")
        
        return _get_image_content_b64(displayImagPath)
    else:
        return _get_image_content_b64("empty.png")
    # imagepath = "/home/ubuntu/SimpleWebApp/uploads/chute_d-2023-11-01T13:04:39.014000-nbp1-depth.png"
    # with open(imagepath, "rb") as fin:
    #     content = fin.read() # bytes
    #     image_b = base64.b64encode(content) # image_b.read())
    #     image_b64 = image_b.decode('utf-8')
    #     print(" ... content", type(content), type(image_b), type(image_b64))
    #     return image_b64
    #     # BytesIO

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001)
