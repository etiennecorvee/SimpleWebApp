from flask import Flask
from flask import Response, request, jsonify
from logging import getLogger
import base64
from io import BytesIO
from dataclasses import dataclass

logger = getLogger(__name__)

app = Flask(__name__)

@dataclass
class File:
    name: str
    buffer: BytesIO 
    extension: str

    @property
    def file(self):
        self.buffer.seek(0)
        return self.buffer

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
    logger.info("/documents content_type received: " + str(content_type))
    accepted_content_type = ["application/octet-stream", "image/jpeg", "image/png"]
    if content_type not in accepted_content_type:
        dict_out["information"] = "the input request has header of content type " + str(content_type)  + \
            " which is not among the accepted ones: "+str(accepted_content_type)
        dict_out["content_type"] = str(content_type)
        return (dict_out, 400, content_file)

    nb_bytes = len(request.data) # request.data is of type "bytes"
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

@app.route("/stamp")
def stamp():
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

    filename = "input." + file_extension
    buffer = BytesIO(content_file) # (content)
    # extension = Path(filename).suffix # get_file_extension(filename)
    file = File(filename, buffer, file_extension)
    # uid = self.service.create_folder(file)
    return {"identifier": "1"}, 200

if __name__ == "__main__":
    app.run(host='0.0.0.0')
