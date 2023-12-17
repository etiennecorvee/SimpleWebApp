import os
import time
import json
import argparse
from flask import Flask
from flask import request, render_template
from flask import redirect, url_for
import flask_login
from logging import getLogger
import subprocess
import pathlib
import shutil
import cv2
from utils import get_4_filenames_from_colour_name, get_stamp_from_request_stamp_data_and_create_empty_file, create_dirs
from utils import _get_doc, move_files_and_update_last, save_doc, draw_text, _get_image_content_b64

MOVE=False


# TODO 1
    # create filename with this time stmap
    # time.strftime("%Y-%m-%dT%H-%M-%S")
    
    # print delta detlat rtimestamp
    
    # here




# add select box for each case: failed + ... + wocoour + the one we have with overlap drwan detection IA
# firewall


# too big proces in image put etxt plus timestamp shall be displayed
# mm empty !!!
# duplicated between procssed and last ... why ?

# TODO get the depth bboxes
#         if unidentified by mm
#         => special case
#         ecovision
#         [WARNING] this is not a valid file: /home/ubuntu/EcoVision/ecolog/2023-11-16T20:32:24.617000.txt

#     ecovision
#     error: object file .git/objects/12/221cd95100ee283dbb36e431a15441eac9e85a is empty
# fatal: loose object 12221cd95100ee283dbb36e431a15441eac9e85a (stored in .git/objects/12/221cd95100ee283dbb36e431a15441eac9e85a) is corrupt

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
app.secret_key = 'e2b44b12-9b66-11ee-9b29-00155db5e5d5'

login_manager = flask_login.LoginManager()
login_manager.init_app(app)

# Our mock database.
# users = {'userhere': {'password': 'passwordhere'}}
class User(flask_login.UserMixin): ...


DEBUG = True


PROJ_PATH = os.path.dirname(os.path.realpath(__file__))
RESULTS_PATH = os.path.join(PROJ_PATH, "results")

app.config['UPLOAD'] = os.path.join(RESULTS_PATH, "uploads")
app.config['PROCESSED'] = os.path.join(RESULTS_PATH, "processed")
app.config['FAILED_MM'] = os.path.join(RESULTS_PATH, "failed_mm")
app.config['LAST'] = os.path.join(RESULTS_PATH, "last")
app.config['ALIVE'] = os.path.join(RESULTS_PATH, "alive")
app.config['MM_OUTPUT_DIR'] = os.path.join(PROJ_PATH, "outputs", "preds")

try:
    create_dirs(folders=[RESULTS_PATH, 
                         app.config['UPLOAD'], 
                         app.config['PROCESSED'], 
                         app.config['FAILED_MM'], 
                         app.config['LAST'],
                         app.config['ALIVE'],
                         "outputs"])
except Exception as err:
    raise Exception(err)


@login_manager.user_loader
def user_loader(email):

    if email != app.config['USERNAME']: 
    # if email not in users:
        return
    
    user = User()
    user.id = email
    return user

# @login_manager.request_loader
# def request_loader(request):
#     email = request.form.get('email')
#     if email not in users:
#         return
    
#     user = User()
#     user.id = email
#     return user

# @app.route("/hello")
# def hello():
#     return "<h1 style='color:blue'>Hello There!</h1>"

# without login
# @app.route("/")
# def upload_file():
#     return render_template('img_render.html')

# with login
@app.route('/img_render', methods = ['GET', 'POST'])
@flask_login.login_required
def img_render():
    return render_template('img_render.html')

@app.route('/', methods = ['GET', 'POST'])
def login():
    if request.method == 'POST':
        formDict = request.form.to_dict()
        email = formDict.get('email')
    
        # if email in users:
        if email == app.config['USERNAME']:
            # if users[email]['password'] == formDict.get('password'):
            if app.config['PASSWORD'] == formDict.get('password'):
                user = User()
                user.id = email
                flask_login.login_user(user)
                # return redirect(url_for('protected_page_1'))
        
        if formDict.get('page'):
            return redirect(url_for('page'))
        elif formDict.get('img_render'):
            # return redirect(url_for('protected_page_1'))
            return redirect(url_for('img_render'))
        # elif formDict.get('protected_page_2'):
        #     return redirect(url_for('protected_page_2'))
        elif formDict.get('logout'):
            return redirect(url_for('logout'))

    return render_template('login.html')

def check_user_pass():
    if request.is_json is False:
        return "bad input request", 400

    if request.json is None:
        return "bad input request", 400
        
    if 'username' not in request.json:
        return "wrong input content", 400
    
    if 'password' not in request.json:
        return "wrong input content", 400
        
    username = request.json.get('username')
    password = request.json.get('password')
    
    # if username in users:
    if username == app.config['USERNAME']:
        # print(" ... username in db: ")
        # if users[username]['password'] == password:
        if app.config['PASSWORD'] == password:
            # print(" ... correct password: ")
            user = User()
            user.id = username
            success = flask_login.login_user(user)
            # print(" ... login: ", success)
            if success is True:
                return None

    return "unauthorized user", 401

@app.route('/version', methods = ['GET'])
def version():
    ret = check_user_pass()
    if ret is not None:
        return ret
    return version_v()

@app.route('/version_v', methods = ['GET'])
@flask_login.login_required
def version_v():
    
    if request.is_json is False:
        return "bad input request", 400

    if request.json is None:
        return "bad input request", 400
        
    if 'username' not in request.json:
        return "wrong input content", 400
    
    if 'password' not in request.json:
        return "wrong input content", 400
        
    username = request.json.get('username')
    password = request.json.get('password')

    # if username in users:
    if username == app.config['USERNAME']:
        # print(" ... username in db: ")
        # if users[username]['password'] == password:
        if app.config['PASSWORD'] == password:
            # print(" ... correct password: ")
            user = User()
            user.id = username
            success = flask_login.login_user(user)
            # print(" ... login: ", success)
            if success is True:
                return "1.0.0", 200
    
    return "unauthorized user", 401

@app.route('/page', methods=['GET','POST'])
def page():
    if request.method == 'POST':
        formDict = request.form.to_dict()
        print('formDcit::', formDict)
        if formDict.get('page'):
            return redirect(url_for('page'))
        elif formDict.get('img_render'):
            # return redirect(url_for('protected_page_1'))
            return redirect(url_for('img_render.html'))
        # elif formDict.get('protected_page_2'):
        #     return redirect(url_for('protected_page_2'))
        elif formDict.get('logout'):
            return redirect(url_for('logout'))
        elif formDict.get('login'):
            return redirect(url_for('login'))
    return render_template('page.html')

@app.route('/alive', methods = ['POST'])
def alive():
    ret = check_user_pass()
    if ret is not None:
        return ret
    return alive_from_v()

@app.route("/alive_v", methods=["POST"])
@flask_login.login_required
def alive_from_v():
    
    # for files =  list files in app.config['ALIVE']
    # if one or zero file: ok add one more
    # if 2 files, delete oldest created one and add new one
    # if more than 2: delete all except the mos recent one
    # in the last 2 cases, get the most recently created file and delete the rest
    
    # YO: no need to get more recent time : get it with sorted function insteaf
    # os.stat(path).st_birthtime
        
    listfilenames = os.listdir(app.config['ALIVE'])
    if len(listfilenames) > 1:
        listfilenames = sorted(listfilenames)
        lastFilename = listfilenames[len(listfilenames)-1]
        for index in range(len(listfilenames)-1):
            filename = listfilenames[index]
            filepath = os.path.join(app.config['ALIVE'], filename)
            if os.path.isfile(filepath) is False:
                return {"details": "failed to find a file"}, 500
            os.remove(filepath)
            if os.path.isfile(filepath) is True:
                return {"details": "failed to delete a file"}, 500
        
        listfilenames = os.listdir(app.config['ALIVE'])
        if len(listfilenames) != 1:
            return {"details": "failed to delete all but last/most recent file"}, 500
    
    
    # TODO 1    


    return {"details": "ok your alive"}, 200 

@app.route('/nocolour', methods = ['POST'])
def nocolour():
    ret = check_user_pass()
    if ret is not None:
        return ret
    return nocolour_v()

@app.route("/nocolour_v/<colour_filename>", methods=["POST"])
@flask_login.login_required
def nocolour_v(colour_filename: str):
    try:
        fourfiles = get_4_filenames_from_colour_name(colour_filename=colour_filename, debug=DEBUG)
    except Exception as err:
        errMsg = "[ERROR] /nocolour/{}: failed with error: {}".format(colour_filename, err)
        print(errMsg)
        return {"details": errMsg}, 400
    
    try:
        move_files_and_update_last(MOVE=MOVE, info="nocolour", nbFiles=2, fourfiles=fourfiles,
            srcDir=app.config['UPLOAD'], dstDir=app.config['PROCESSED'], lastDir=app.config['LAST'])
    except Exception as err:
        msgErr = "[ERROR] /nolour/{} failed with error={}".format(colour_filename, err)
        print(msgErr)
        return {"details": msgErr}, 400

@app.route('/process', methods = ['POST'])
def process():
    ret = check_user_pass()
    if ret is not None:
        return ret
    return process_v()

@app.route("/process_v/<colour_filename>", methods=["POST"])
@flask_login.login_required
def process_v(colour_filename: str):
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
            move_files_and_update_last(MOVE=MOVE, info="failed_mm", nbFiles=3, fourfiles=fourfiles,
                srcDir=app.config['UPLOAD'], dstDir=app.config['FAILED_MM'], lastDir=app.config['LAST'], debug=True)
        except Exception as err:
            errMsg = "[ERROR] /process/{} failed, returned code {} error={}, additional error={}".format(
                output.returncode, bytes.decode(output.stderr), colour_filename)
            print(errMsg, err)
            return {"details": errMsg}, 400
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
            move_files_and_update_last(MOVE=MOVE, info="processed", nbFiles=4, fourfiles=fourfiles,
                srcDir=app.config['UPLOAD'], dstDir=app.config['PROCESSED'], lastDir=app.config['LAST'], debug=True)
        except Exception as err:
            msgErr = "[ERROR] /process/{} mmdetection ok but moving file update failed".format(colour_filename, err)
            print(msgErr)
            return {"details": msgErr}, 400
        
        return { "details": json.dumps(data) }, 200
    
    return {"details": "failure"}, 400

@app.route('/stamp', methods = ['POST'])
def stamp():
    ret = check_user_pass()
    if ret is not None:
        return ret
    return stamp_v()

@app.route("/stamp_v", methods=["POST"])
@flask_login.login_required
def stamp_v():
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

@app.route('/colour/<colourstem>', methods = ['POST'])
def colour(colourstem: str):
    ret = check_user_pass()
    if ret is not None:
        return ret
    return colour_v(colourstem=colourstem)

@app.route("/colour_v/<colourstem>", methods=["POST"])
@flask_login.login_required
def colour_v(colourstem: str):
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

@app.route('/depth/<depthstem>', methods = ['POST'])
def depth(depthstem: str):
    ret = check_user_pass()
    if ret is not None:
        return ret
    return depth_v(depthstem=depthstem)

@app.route("/depth_v/<depthstem>", methods=["POST"])
@flask_login.login_required
def depth_v(depthstem: str):
    
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

@app.route('/processedimage/<string:camId>/<string:filename>', methods = ['GET'])
def processedimage(camId: str, filename: str):
    ret = check_user_pass()
    if ret is not None:
        return ret
    return processedimage_v(camId=camId, filename=filename)

@app.route('/processedimage_v/<string:camId>/<string:filename>', methods=['GET'])
@flask_login.login_required
def processedimage_v(camId: str, filename: str):
    fullpath = os.path.join(app.config['PROCESSED'], filename)
    print(" ... ... processedimage, camId", camId, "filename", filename, "fullpath", fullpath)
    if os.path.isfile(fullpath) is False:
        print(" ... ...does not exist")
        return _get_image_content_b64("images/error.png")
    else:
        print(" ... ...ok")
        return _get_image_content_b64(fullpath)

@app.route('/deleteprocessedimage/<string:camId>/<string:filename>', methods=['DELETE'])
def deleteprocessedimage(camId: str, filename: str):
    ret = check_user_pass()
    if ret is not None:
        return ret
    return deleteprocessedimage_v(camId=camId, filename=filename)

@app.route('/deleteprocessedimage_v/<string:camId>/<string:filename>', methods=['DELETE'])
@flask_login.login_required
def deleteprocessedimage_v(camId: str, filename: str):
    fullpath = os.path.join(app.config['PROCESSED'], filename)
    print(" ... ... deleteprocessedimage, camId", camId, "filename", filename, "fullpath", fullpath)
    if os.path.isfile(fullpath) is False:
        print(" ... ...does not exist")
        return {"details": "KO: file dos not exist to be deleted"}, 400
    else:
        print(" ... ...ok")
        try:
            os.remove(fullpath)
            return {"details": "OK: file deleted"}, 200
        except Exception as err:
            print("removed failed:", err)
            return {"details": "KO: file to be deleted failed"}, 400

@app.route('/result/<string:camId>', methods=['GET'])
def result_api(camId: str):
    ret = check_user_pass()
    if ret is not None:
        return ret
    return result_api_v(camId=camId)

@app.route('/result/<string:camId>', methods=['GET'])
@flask_login.login_required
def result_api_v(camId: str):
    
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
        cv2.putText(img=displayImg, text=infoProcess, org=(10, height-10), fontFace=cv2.FONT_HERSHEY_DUPLEX, 
                    fontScale=0.5, color=(54, 212, 204), thickness=1)
        # if os.path.isfile(os.path.join(app.config['LAST'], colourFilename)) is True:
        
        if mmFilename is not None:
            if os.path.isfile(os.path.join(app.config['LAST'], mmFilename)) is True:
                try:
                    with open(os.path.join(app.config['LAST'], mmFilename), "r") as fjson:
                        data = json.loads(fjson.read())
                        # print(" ... mmdetection data", data)
                        try:
                            for obj in data['predictions']:
                                # if obj['class'] == 'person':
                                left = int(obj['bbox'][0])
                                top = int(obj['bbox'][1])  
                                right = int(obj['bbox'][2])
                                bottom = int(obj['bbox'][3])
                                displayImg = cv2.rectangle(displayImg, (left, top), (right, bottom), (200,50,200), 2)
                                displayImg = cv2.putText(img=displayImg, text=obj['class'],
                                    org=(left, top), fontFace=cv2.FONT_HERSHEY_DUPLEX, fontScale=0.5, color=(125, 246, 55), thickness=1)
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

@app.route('/resultListProcessed', methods=['GET'])
def resultListProcessed():
    ret = check_user_pass()
    if ret is not None:
        return ret
    return resultListProcessed_v()

# @app.route('/resultListProcessed/<string:camId>', methods=['GET'])
# def resultListProcessed(camId: str):
@app.route('/resultListProcessed', methods=['GET'])
@flask_login.login_required
def resultListProcessed_v():
    print(" ... resultListProcessed")
    output = []
    output2=""
    response_html = '["'
    output3 = {}
    
    listfilenames = os.listdir(app.config['PROCESSED'])
    listfilenames = sorted(listfilenames)
    # print(" ... listfilenames", listfilenames)
    for index in range(len(listfilenames)):
        filename = listfilenames[index]
    # for filename in :
        if "depth" in filename and ".png" in filename:
            output.append(filename)
            
            # output2 += filename + str(index+0) + "\n"
            # output2 += filename + str(index+1) + "\n"
            # output2 += filename + str(index+2) + "\n"
            
            # todo to delete
            output.append(filename)
            # output2 += filename + str(index+3)
            output2 += filename
            if index != len(listfilenames)-1:
                output2 += "\n"
            
            output3["item"] = filename
            output3["item2"] = filename
            
            response_html += filename + ","
            response_html += filename
            
            if index != len(listfilenames)-1:
                response_html += ","
                
            
    # print(" ... resultListProcessed output", output)
    
    response_html += '"]'
    
    # print(" ... return list:", output2)
     
    return output2
        
    # return output
    # return output2

@app.route('/logout')
def logout():
    flask_login.logout_user()
    return redirect(url_for('login'))

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description='ecovision threads manager')
    parser.add_argument('--debug', action='store_true', default=False)
    parser.add_argument("-username", dest="username", required=True, type=str, help="username")
    parser.add_argument("-password", dest="password", required=True, type=str, help="password")
    args = parser.parse_args()
    
    app.config['USERNAME'] = args.username
    app.config['PASSWORD'] = args.password
    
    app.run(host='0.0.0.0', port=5001)
