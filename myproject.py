import os
import time
import json
from flask import Flask
from flask import request, render_template
from logging import getLogger
import subprocess
import pathlib
import cv2
from utils import get_4_filenames_from_colour_name, get_stamp_from_request_stamp_data_and_create_empty_file, create_dirs
from utils import _get_doc, move_files_and_update_last, save_doc, draw_text, _get_image_content_b64

# too big proces in image put etxt plus timestamp shall be displayed
# mm empty !!!
# duplicated between procssed and last ... why ?

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


PROJ_PATH = os.path.dirname(os.path.realpath(__file__))
RESULTS_PATH = os.path.join(PROJ_PATH, "results")

app.config['UPLOAD'] = os.path.join(RESULTS_PATH, "uploads")
app.config['PROCESSED'] = os.path.join(RESULTS_PATH, "processed")
app.config['FAILED_MM'] = os.path.join(RESULTS_PATH, "failed_mm")
app.config['LAST'] = os.path.join(RESULTS_PATH, "last")
app.config['MM_OUTPUT_DIR'] = os.path.join(PROJ_PATH, "outputs", "preds")

try:
    create_dirs(folders=[RESULTS_PATH, app.config['UPLOAD'], app.config['PROCESSED'], app.config['FAILED_MM'], app.config['LAST'], "outputs"])
except Exception as err:
    raise Exception(err)

@app.route("/hello")
def hello():
    return "<h1 style='color:blue'>Hello There!</h1>"

@app.route("/")
def upload_file():
    return render_template('img_render.html')

@app.route("/nocolour/<colour_filename>", methods=["POST"])
def nocolour(colour_filename: str):
    try:
        fourfiles = get_4_filenames_from_colour_name(colour_filename=colour_filename, debug=DEBUG)
    except Exception as err:
        errMsg = "[ERROR] /nocolour/{}: failed with error: {}".format(colour_filename, err)
        print(errMsg)
        return {"details": errMsg}, 400
    
    try:
        move_files_and_update_last(info="nocolour", nbFiles=2, fourfiles=fourfiles,
            srcDir=app.config['UPLOAD'], dstDir=app.config['PROCESSED'], lastDir=app.config['LAST'])
    except Exception as err:
        msgErr = "[ERROR] /nolour/{} failed with error={}".format(colour_filename, err)
        print(msgErr)
        return {"details": err}, 400

@app.route("/process/<colour_filename>", methods=["POST"])
def process(colour_filename: str):
    colourPath = os.path.join(app.config['UPLOAD'], colour_filename)
    if os.path.isfile(colourPath) is False:
        return {"details": "colour image path does not exist: {}".format(colourPath)}, 400
    
    try:
        fourfiles = get_4_filenames_from_colour_name(colour_filename=colour_filename, debug=DEBUG)
    except Exception as err:
        # colour image to be moved to failed folder ?
        errMsg = "[ERROR]/process/{} getting the 3 filenames failed with error: {}".format(colour_filename, err)
        print(errMsg)
        return {"details": errMsg}, 400
    
    cmd_line = '''python -c "import sys; print(sys.executable)"
                  source /home/ubuntu/miniconda3/etc/profile.d/conda.sh
                  conda activate openmmlab
                  python /home/ubuntu/mmdetection/demo/image_demo.py {} /home/ubuntu/mmdetection/rtmdet_tiny_8xb32-300e_coco.py --weights /home/ubuntu/mmdetection/rtmdet_tiny_8xb32-300e_coco_20220902_112414-78e30dcc.pth --device cpu'''.format(colourPath)
    
    print("[INFO] /process/{}: cmd_line: {}".format(colour_filename, cmd_line))
    output = subprocess.run(cmd_line, executable='/bin/bash', shell=True, capture_output=True)
    time.sleep(1)
    if output.returncode != 0:
        print("[INFO] stdout: ", bytes.decode(output.stdout))
        try:
            move_files_and_update_last(info="failed_mm", nbFiles=3, fourfiles=fourfiles,
                srcDir=app.config['UPLOAD'], dstDir=app.config['FAILED_MM'], lastDir=app.config['LAST'], debug=True)
        except Exception as err:
            msgErr = "[ERROR] /process/{} failed, returned code {} error={}, additional error={}".format(
                output.returncode, bytes.decode(output.stderr), colour_filename, err)
            print(msgErr)
            return {"details": err}, 400
    else:
        outputfilename = colour_filename.strip(".png") + ".json"
        jsonPredPath = os.path.join(app.config['MM_OUTPUT_DIR'], outputfilename)
        if os.path.isfile(jsonPredPath) is False:
            errMsg = "[ERROR] mmdetection result predition file does not exist: {}".format(jsonPredPath)
            print(errMsg)
            return {"details": errMsg}, 400
        
        # see TODO.py
        inputPath = os.path.abspath(colourPath)
        outputPath = inputPath.replace(pathlib.Path(inputPath).suffix, ".mm")
        try:
            with open(outputPath, "r") as fin:
                data = json.loads(fin.read())
        except Exception as err:
            msg = "[ERROR] could not parse json file: {}: error={}".format(outputPath, err)
            print(msg)
            return {"details": "mmedetection failed: {}".format(msg)}, 400
        
        print("[INFO] mmdetection results data: ", data)
        
        try:
            move_files_and_update_last(info="failed_mm", nbFiles=4, fourfiles=fourfiles,
                srcDir=app.config['UPLOAD'], dstDir=app.config['PROCESSED'], lastDir=app.config['LAST'])
        except Exception as err:
            msgErr = "[ERROR] /process/{} mmdetection ok but moving file update failed with error={}".format(colour_filename, err)
            print(msgErr)
            return {"details": err}, 400
        
        return { "details": json.dumps(data) }, 200
    
    return {"details": "failure"}, 400

@app.route("/stamp", methods=["POST"])
def stamp():
    content_type = request.headers.get('Content-Type')
    nb_bytes = len(request.data) # request.data is of type "bytes"
    textData = request.data.decode("utf-8")
    print("[INFO]/stamp: received stamp: ", content_type, nb_bytes, request.data, " => '{}'".format(textData))
    
    try:
        textData = get_stamp_from_request_stamp_data_and_create_empty_file(textData=textData, dstDir=app.config['UPLOAD'])
    except Exception as err:
        errMsg = "[ERROR]/stamp failed get_stamp_from_request_stamp_data: {}".format(err)
        print(errMsg)
        return {"details": errMsg}, 400
    return {"details": "stamp upload success"}, 200

@app.route("/colour/<colourstem>", methods=["POST"])
def colour(colourstem: str):
    try:
        # (json_content, status_code, content_file) = _get_doc(request_headers=request.headers, request_data=request.data, base64mode=False)
        content_file = _get_doc(request_headers=request.headers, request_data=request.data, base64mode=False)
    except Exception as err:
        return {"details": "/colour/{} get doc image failed: {}".format(colourstem, err)}, 400
        # return (dict_out, 400, content_file)

    try:
        save_doc(request_content_length=request.content_length, request_content_type=request.content_type, 
             filenamestem=colourstem, content_file=content_file, dstDir=app.config['UPLOAD'])
    except Exception as err:
        return {"details": "/colour/{} save doc image failed: {}".format(colourstem, err)}, 400

    return {"details": "colour upload success"}, 200

@app.route("/depth/<depthstem>", methods=["POST"])
def depth(depthstem: str):
    
    try:
        content_file = _get_doc(request_headers=request.headers, request_data=request.data, base64mode=False)
    except Exception as err:
        return {"details": "/depth/{} get doc image failed: {}".format(depthstem, err)}, 400
        
    try:
        save_doc(request_content_length=request.content_length, request_content_type=request.content_type, 
             filenamestem=depthstem, content_file=content_file, dstDir=app.config['UPLOAD'])
    except Exception as err:
        return {"details": "/depth/{} save doc image failed: {}".format(depthstem, err)}, 400

    return {"details": "colour upload success"}, 200

@app.route('/result/<string:camId>', methods=['GET'])
def result_api(camId: str):
    
    infoPath = os.path.join(app.config['LAST'], "info.txt")
    if os.path.isfile(infoPath) is False:
        return _get_image_content_b64("images/empty.png")
    
    with open(infoPath, "r") as fin:
        lines = fin.readlines()
        if len(lines) < 3 : # info, stamp.png, depth.png + colour.png + colour.mm
            # TODO draw on image or message on html
            print("[ERROR]/result, nb lines in infoPath {}: nblines {}, lines={}".format(infoPath, len(lines), lines))
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
                stampFilename = lines[index].strip()
                if ".txt" not in stampFilename:
                    print("[ERROR]/result: .txt not found in stampFilename: {}".format(stampFilename))
                    draw_text(displayImagPath="images/error.png", 
                        infoProcess=infoProcess, outputPath="temp.png")
                    return _get_image_content_b64("temp.png")
            elif index==2: # depth.png
                depthFilename = lines[index].strip()
                if "depth" not in depthFilename or ".png" not in depthFilename:
                    print("[ERROR]/result: depth and .png not found in depthFilename: {}".format(depthFilename))
                    draw_text(displayImagPath="images/error.png", 
                        infoProcess=infoProcess+" depth png not found in {}".format(depthFilename), outputPath="temp.png")
                    return _get_image_content_b64("temp.png")
            elif index==3: # colour.png
                colourFilename = lines[index].strip()
                if "colour" not in colourFilename or ".png" not in colourFilename:
                    print("[ERROR]/result: colour and .png not found in colourFilename: {}".format(colourFilename))
                    draw_text(displayImagPath="images/error.png", 
                        infoProcess=infoProcess+" colour png not found in {}".format(colourFilename), outputPath="temp.png")
                    return _get_image_content_b64("temp.png")
            elif index==4: # colour.mm
                mmFilename = lines[index].strip()
                if "colour" not in mmFilename or ".mm" not in mmFilename:
                    print("[ERROR]/result: colour and mm not found in stampFilename: {}".format(mmFilename))
                    draw_text(displayImagPath="images/error.png", 
                        infoProcess=infoProcess+" colour mm not found in {}".format(colourFilename), outputPath="temp.png")
                    return _get_image_content_b64("temp.png")

        if os.path.isfile(os.path.join(app.config['LAST'], stampFilename)) is False:
            print("[ERROR]/result: stampFilename: {} not found in last folder".format(stampFilename))
            draw_text(displayImagPath="images/error.png", 
                infoProcess=infoProcess+" stamp file not found {}".format(stampFilename), outputPath="temp.png")
            return _get_image_content_b64("images/error.png")
        if os.path.isfile(os.path.join(app.config['LAST'], depthFilename)) is False:
            print("[ERROR]/result: depthFilename: {} not found in last folder".format(depthFilename))
            draw_text(displayImagPath="images/error.png", 
                infoProcess=infoProcess+" depth file not found {}".format(depthFilename), outputPath="temp.png")
            return _get_image_content_b64("images/error.png")
        
        displayImagPath = os.path.join(app.config['LAST'], depthFilename)
        displayImg = cv2.imread(displayImagPath)
        height = displayImg.shape[0]
        # width = displayImg.shape[1]
        cv2.putText(img=displayImg, text=infoProcess, org=(10, height-10), fontFace=cv2.FONT_HERSHEY_DUPLEX, fontScale=3.0, color=(54, 212, 204), thickness=3)
        # if os.path.isfile(os.path.join(app.config['LAST'], colourFilename)) is True:
        
        if mmFilename is not None:
            if os.path.isfile(os.path.join(app.config['LAST'], mmFilename)) is True:
                try:
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
                            return _get_image_content_b64("temp.png")
                        except Exception as err:
                            print("[ERROR] {}".format(err))
                            draw_text(displayImagPath="images/error.png", 
                                infoProcess=infoProcess+" draw mm res failed", outputPath="temp.png")
                            return _get_image_content_b64("temp.png")
                except:
                    draw_text(displayImagPath=displayImagPath, 
                        infoProcess=infoProcess+" mm file error", outputPath="temp.png")
                    return _get_image_content_b64("temp.png")
            else:
                draw_text(displayImagPath=displayImagPath, 
                    infoProcess=infoProcess+" error mm file", outputPath="temp.png")
                return _get_image_content_b64("temp.png")
        else:
            draw_text(displayImagPath=displayImagPath, 
                infoProcess=infoProcess+" no mm res", outputPath="temp.png")
            return _get_image_content_b64("temp.png")

        print("[ERROR]/result: reached end of endpoint")
        return _get_image_content_b64("images/error.png")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001)
