import os
from flask import Flask
from flask import Response, request, jsonify
from logging import getLogger
import base64
from io import BytesIO
from dataclasses import dataclass
from uuid import uuid1

logger = getLogger(__name__)

app = Flask(__name__)

upload_folder = "./uploads"

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

@app.route("/")
def hello():
    return "<h1 style='color:blue'>Hello There!</h1>"

@app.route("/stamp", methods=["POST"])
def stamp():
    content_type = request.headers.get('Content-Type')
    nb_bytes = len(request.data) # request.data is of type "bytes"
    text = request.data.decode("utf-8")
    print("[INFO] received stamp: ", content_type, nb_bytes, request.data, text)
    
    return {"details": "stamp upload success"}, 200

@app.route("/colour/<stamp>", methods=["POST"])
def colour(stamp: str):
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

    filename = stamp + "-colour." + file_extension
    buffer = BytesIO(content_file) # (content)
    file = File(filename, buffer, file_extension)
    try:
        save_file(upload_folder=upload_folder, im_file=file)
    except Exception as err:
        return {"details" : "failed to save file"}, 400

    return {"details": "colour upload success"}, 200

@app.route("/depth/<stamp>", methods=["POST"])
def depth(stamp: str):
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

    filename = stamp + "-depth." + file_extension
    buffer = BytesIO(content_file) # (content)
    file = File(filename, buffer, file_extension)
    try:
        save_file(upload_folder=upload_folder, im_file=file)
    except Exception as err:
        return {"details" : "failed to save file"}, 400

    return {"details": "depth upload success"}, 200

if __name__ == "__main__":
    app.run(host='0.0.0.0')
