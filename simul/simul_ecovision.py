import os
import requests
import pathlib
import json
import base64
from cryptography.fernet import Fernet

# without login authentification: ok
def SendItToCloudServer_no_login(url_address: str, timeout: int, 
                        stamp_filename: str, 
                        depth_filename: str, 
                        colour_filename: str=None):

    stamp_filename = stamp_filename.replace(":", "-") # converted to % when receved by webapp
    entries = [(stamp_filename, "/stamp", "txt"), (depth_filename, "/depth", "image/png"), (colour_filename, "/colour", "image/png")]
    for entry in entries:
        if entry[0] is not None:
            try:
                
                if entry[1]=="/stamp":
                    result_upload = requests.post(
                        url=url_address + entry[1],
                        headers={"Content-type": entry[2]},
                        data={"stamp": os.path.basename(stamp_filename).strip(".txt")},
                        timeout=timeout,
                    )
                    if result_upload.status_code != 200:
                        print("result upload stamp status: {} {}".format(result_upload.status_code, result_upload.content))
                else:
                    # _url = url_address + entry[1] + "/" + os.path.basename(stamp).strip(".txt")
                    _url = url_address + entry[1] + "/" + pathlib.Path(entry[0]).stem #  os.path.basename(stamp).strip(".txt")
                    print(" ... send image to: ", _url)
                    with open(entry[0], mode="rb") as f:
                        fileContent = f.read()
                        result_upload = requests.post(
                            url = _url,
                            headers={"Content-type": entry[2]},
                            data=fileContent,
                            timeout=timeout,
                        )
                        # print("result upload status: {}".format(result_upload.status_code))
                        # print("result upload content: {}".format(result_upload1.content))
                        # json_data_res = json.loads(result_upload1.content.decode("utf-8"))
                
                if result_upload.status_code != 200:
                    print("result upload image status: {} {}".format(result_upload.status_code, result_upload.content))
                    raise Exception("SendItToCloudServer request failed for '{}': error={}".format(entry, err))
                
            except Exception as err:
                raise FileExistsError("SendItToCloudServer failed sending {} error={}".format(entry, err))

    if colour_filename is not None:
        try:
            result_process = requests.post(
                # url=url_address + "/process/" + os.path.basename(stamp).strip(".txt"),
                url=url_address + "/process/" + os.path.basename(colour_filename),
                timeout=timeout,
            )
            if result_process.status_code != 200:
                print("result process status: {} {}".format(result_process.status_code, result_process.content))
        except Exception as err:
            raise FileExistsError("SendItToCloudServer failed process error={}".format(err))

def SendItToCloudServer_with_login_bu_not_ecrypted(USERNAME: str, PASSWORD: str, url_address: str, timeout: int, stamp: str, depth: str, colour: str=None):

    stamp = stamp.replace(":", "-") # converted to % when receved by webapp
    
    # before authentification
    # entries = [(stamp, "/stamp", "txt"), (depth, "/depth", "image/png"), (colour, "/colour", "image/png")]
    # with login, we need to send json, so we need to send image png inside json
    # now send image mng dfepth inside jsoin alsonside user and pass

    entries = [(stamp, "/stamp", "application/json"), (depth, "/depth", "application/json"), (colour, "/colour", "application/json")]
    for entry in entries:
        if entry[0] is not None:
            try:
                
                if entry[1]=="/stamp":
                    result_upload = requests.post(
                        url=url_address + entry[1],
                        headers={"Content-type": entry[2]},
                        # data={"stamp": os.path.basename(stamp).strip(".txt")},
                        json={"username": USERNAME, "password": PASSWORD, "stamp": os.path.basename(stamp).strip(".txt")},
                        timeout=timeout,
                    )
                    if result_upload.status_code != 200:
                        print("[INFO]result upload stamp status: {} {}".format(result_upload.status_code, result_upload.content))
                else:
                    # _url = url_address + entry[1] + "/" + os.path.basename(stamp).strip(".txt")
                    _url = url_address + entry[1] + "/" + pathlib.Path(entry[0]).stem #  os.path.basename(stamp).strip(".txt")
                    print("[INFO] ... send image to: ", _url)
                    # "stream": (open(input_filename, "rb").read()).decode("iso-8859-1"),
                    with open(entry[0], mode="rb") as f:
                        
                        #  .... f.read() - bytes -  b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x01@\x00\x00\x00\xf0\x08\x02\x00\x00\x00\xfeO*<\x00\x00K\xf6IDATx\x9c\xed\xbd{\xb0\x9eUu?\xbe\x9fs\x92p\x93\x8b:j\xedT[\xc7\xff:
                        #                            '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x01@\x00\x00\x00ð\x08\x02\x00\x00\x00þO*<\x00\x00KöIDATx\x9cí½{°\x9eUu?¾\x9fs\x92p\x93\x8b:jíT[Çÿ:µ\x1d)\x83\x15\x03\x01Ê%\x92»Ñ\x04\t·\x18Í$\x81à7øë0AnB\x90AG\x98©\x918\nÄ6\x02\x86j¸\x04(\x01¹\x04\x82U\x14Æéß\x9dqZ!\x88\xad\x06\x8aCs;ïþý±{V×»n{íý<ï
                        # fileContent = (f.read()).decode("iso-8859-1") # receives str in received request afet posting this data
                        
                        fileContent = f.read()
                        
                        fileContent = fileContent.decode("iso-8859-1")
                        # print(" ... fileContent", type(fileContent), fileContent) # jiberish, messed up terminal
                        
                        # ... fileContent <class 'bytes'> b'iVBORw0KGgoAAAANSUhEUgAAAUAAAADwCAIAAAD+Tyo8AABL9klEQVR4nO29e7CeVXU/vp9zknCTizpq7VRbx/86tR0pgxUDAcolkrvRBAm3GM0kgeA3+OswQW5CkEFHmKmROArENgKGargEKAG5BIJVFMbp351xWiGIrQaKQ3M
                        # fileContent = base64.b64encode(fileContent)
                        # print(" ... fileContent", type(fileContent), fileContent)
                        
                        # print(" ... fileContent", type(fileContent)) # str
                        
                        # fileContent = f.read() # bytes
                        # print(" ... type ", type(fileContent))
                        # test = fileContent.encode('utf-8')
                        # print(" ... type ", type(test))
                        # fileContent = base64.encodebytes(fileContent)
                        # fileContent = base64.b64encode(fileContent)
                        # print(" ... typeb64? ", type(fileContent)) # bytes
                        
                        result_upload = requests.post(
                            url = _url,
                            headers={"Content-type": entry[2]},
                            # data=fileContent, # before login
                            json={"username": USERNAME, "password": PASSWORD, "data": fileContent},
                            timeout=timeout,
                        )
                        print("[INFO]result upload status: {}".format(result_upload.status_code))
                        # print("result upload content: {}".format(result_upload1.content))
                        # json_data_res = json.loads(result_upload1.content.decode("utf-8"))
                
                if result_upload.status_code != 200:
                    print("result upload image status: {} {}".format(result_upload.status_code, result_upload.content))
                    # raise Exception("SendItToCloudServer request failed for '{}': error={}".format(entry, err))
                    raise Exception("SendItToCloudServer request failed for '{}': error=?".format(entry))
                
            except Exception as err:
                # print(" ... err", err)
                # raise FileExistsError("SendItToCloudServer failed sending {} error={}".format(entry, err))
                raise FileExistsError("SendItToCloudServer failed sending {} error=?".format(entry))

    if colour is not None:
        try:
            url = url_address + "/process/" + os.path.basename(colour)
            print(" ... post process ", url)
            result_process = requests.post(
                # url=url_address + "/process/" + os.path.basename(stamp).strip(".txt"),
                url=url,
                json={"username": USERNAME, "password": PASSWORD},
                timeout=timeout,
            )
            print("result post process colour: {}".format(result_process.status_code))
            if result_process.status_code != 200:
                print("result process status: {} {}".format(result_process.status_code, result_process.content))
        except Exception as err:
            raise FileExistsError("SendItToCloudServer failed process error={}".format(err))
        
    else:
        try:
            result_process = requests.post(
                url=url_address + "/nocolour/" + os.path.basename(stamp),
                json={"username": USERNAME, "password": PASSWORD},
                timeout=timeout,
            )
            if result_process.status_code != 200:
                print("result nocolour status: {} {}".format(result_process.status_code, result_process.content))
        except Exception as err:
            raise FileExistsError("SendItToCloudServer failed nocolour request error={}".format(err))

def load_key():
    """
    Loads the key named `secret.key` from the current directory.
    """
    try:
        keyfile = "/etc/ecodata/secret.key"
        if os.path.isfile(keyfile) is False:
            raise FileExistsError("key file does not exist")
        with open(keyfile, "rb") as fkey:
            return fkey.read()
    except Exception as err:
        raise FileExistsError("key file was not found")

def SendItToCloudServer(USERNAME: str, PASSWORD: str, url_address: str, timeout: int, stamp: str, depth: str, colour: str=None):

    stamp = stamp.replace(":", "-") # converted to % when receved by webapp
    
    entries = [(stamp, "/stamp", "application/octet-stream"), (depth, "/depth", "application/octet-stream"), (colour, "/colour", "application/octet-stream")]
    for entry in entries:
        if entry[0] is not None:
            try:
                
                if entry[1]=="/stamp":
                    
                    jsondata={"username": USERNAME, "password": PASSWORD, "stamp": os.path.basename(stamp).strip(".txt")}
                    jsonstr = json.dumps(jsondata)  # str
                    jsonbytes = jsonstr.encode() # bytes
                    print(" ... jsondata", jsondata)
                    
                    try:
                        key = load_key()
                    except Exception as err:
                        raise FileExistsError("load key failed: {}".format(err))
                    ferkey = Fernet(key)
                    encrypted_message = ferkey.encrypt(jsonbytes) # bytes
                    
                    print(" ... encrypted_message", type(encrypted_message), encrypted_message)
                    
                    result_upload = requests.post(
                        url=url_address + entry[1],
                        headers={"Content-type": entry[2]},
                        # data={"stamp": os.path.basename(stamp).strip(".txt")},
                        # json={"username": USERNAME, "password": PASSWORD, "stamp": os.path.basename(stamp).strip(".txt")},
                        data=encrypted_message,
                        timeout=timeout,
                    )
                    if result_upload.status_code != 200:
                        print("[INFO]result upload stamp status: {} {}".format(result_upload.status_code, result_upload.content))
                else:
                    # _url = url_address + entry[1] + "/" + os.path.basename(stamp).strip(".txt")
                    _url = url_address + entry[1] + "/" + pathlib.Path(entry[0]).stem #  os.path.basename(stamp).strip(".txt")
                    print("[INFO] ... send image to: ", _url)
                    # "stream": (open(input_filename, "rb").read()).decode("iso-8859-1"),
                    with open(entry[0], mode="rb") as f:
                        
                        #  .... f.read() - bytes -  b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x01@\x00\x00\x00\xf0\x08\x02\x00\x00\x00\xfeO*<\x00\x00K\xf6IDATx\x9c\xed\xbd{\xb0\x9eUu?\xbe\x9fs\x92p\x93\x8b:j\xedT[\xc7\xff:
                        #                            '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x01@\x00\x00\x00ð\x08\x02\x00\x00\x00þO*<\x00\x00KöIDATx\x9cí½{°\x9eUu?¾\x9fs\x92p\x93\x8b:jíT[Çÿ:µ\x1d)\x83\x15\x03\x01Ê%\x92»Ñ\x04\t·\x18Í$\x81à7øë0AnB\x90AG\x98©\x918\nÄ6\x02\x86j¸\x04(\x01¹\x04\x82U\x14Æéß\x9dqZ!\x88\xad\x06\x8aCs;ïþý±{V×»n{íý<ï
                        # fileContent = (f.read()).decode("iso-8859-1") # receives str in received request afet posting this data
                        
                        fileContent = f.read()
                        
                        fileContent = fileContent.decode("iso-8859-1")
                        # print(" ... fileContent", type(fileContent), fileContent) # jiberish, messed up terminal
                        
                        # ... fileContent <class 'bytes'> b'iVBORw0KGgoAAAANSUhEUgAAAUAAAADwCAIAAAD+Tyo8AABL9klEQVR4nO29e7CeVXU/vp9zknCTizpq7VRbx/86tR0pgxUDAcolkrvRBAm3GM0kgeA3+OswQW5CkEFHmKmROArENgKGargEKAG5BIJVFMbp351xWiGIrQaKQ3M
                        # fileContent = base64.b64encode(fileContent)
                        # print(" ... fileContent", type(fileContent), fileContent)
                        
                        # print(" ... fileContent", type(fileContent)) # str
                        
                        # fileContent = f.read() # bytes
                        # print(" ... type ", type(fileContent))
                        # test = fileContent.encode('utf-8')
                        # print(" ... type ", type(test))
                        # fileContent = base64.encodebytes(fileContent)
                        # fileContent = base64.b64encode(fileContent)
                        # print(" ... typeb64? ", type(fileContent)) # bytes
                        
                        jsondata={"username": USERNAME, "password": PASSWORD, "data": fileContent}
                        jsonstr = json.dumps(jsondata)  # str
                        jsonbytes = jsonstr.encode() # bytes
                        # print(" ... jsondata", jsondata)
                        
                        try:
                            key = load_key()
                        except Exception as err:
                            raise FileExistsError("load key failed: {}".format(err))
                        ferkey = Fernet(key)
                        encrypted_message = ferkey.encrypt(jsonbytes) # bytes
                        
                        
                        
                        result_upload = requests.post(
                            url = _url,
                            headers={"Content-type": entry[2]},
                            # data=fileContent, # before login
                            # json={"username": USERNAME, "password": PASSWORD, "data": fileContent},
                            data=encrypted_message,
                            timeout=timeout,
                        )
                        print("[INFO]result upload status: {}".format(result_upload.status_code))
                        # print("result upload content: {}".format(result_upload1.content))
                        # json_data_res = json.loads(result_upload1.content.decode("utf-8"))
                
                if result_upload.status_code != 200:
                    print("result upload image status: {} {}".format(result_upload.status_code, result_upload.content))
                    # raise Exception("SendItToCloudServer request failed for '{}': error={}".format(entry, err))
                    raise Exception("SendItToCloudServer request failed for '{}': error=?".format(entry))
                
            except Exception as err:
                # print(" ... err", err)
                # raise FileExistsError("SendItToCloudServer failed sending {} error={}".format(entry, err))
                raise FileExistsError("SendItToCloudServer failed sending {} error=?".format(entry))

    if colour is not None:
        try:
            url = url_address + "/process/" + os.path.basename(colour)
            print(" ... post process ", url)
            result_process = requests.post(
                # url=url_address + "/process/" + os.path.basename(stamp).strip(".txt"),
                url=url,
                json={"username": USERNAME, "password": PASSWORD},
                timeout=timeout,
            )
            print("result post process colour: {}".format(result_process.status_code))
            if result_process.status_code != 200:
                print("result process status: {} {}".format(result_process.status_code, result_process.content))
        except Exception as err:
            raise FileExistsError("SendItToCloudServer failed process error={}".format(err))
        
    else:
        try:
            result_process = requests.post(
                url=url_address + "/nocolour/" + os.path.basename(stamp),
                json={"username": USERNAME, "password": PASSWORD},
                timeout=timeout,
            )
            if result_process.status_code != 200:
                print("result nocolour status: {} {}".format(result_process.status_code, result_process.content))
        except Exception as err:
            raise FileExistsError("SendItToCloudServer failed nocolour request error={}".format(err))


## SendItToCloudServer(url_address="http://127.0.0.1:5001", timeout=10,
##                     stamp_filename="/home/ubuntu/EcoVision/ecolog/chute_d-2023-11-01T13:04:39.014000.txt", # this does not have to exist
##                     # colour=None, # "/home/ubuntu/SimpleWebApp/uploads/chute_d-2023-11-01T13:04:39.014000-nbp1-colour.png",
##                     colour_filename="/home/ubuntu/SimpleWebApp/uploads/chute_d-2023-11-01T13:04:39.014000-nbp1-colour.png",
##                     depth_filename="/home/ubuntu/SimpleWebApp/uploads/chute_d-2023-11-01T13:04:39.014000-nbp1-depth.png")

# SendItToCloudServer(url_address="http://127.0.0.1:5001", timeout=10,
#                     stamp_filename="/home/ubuntu/SimpleWebApp/results/tests/chute_d-2023-11-01T13:04:39.014000.txt", # this does not have to exist
#                     colour_filename="/home/ubuntu/SimpleWebApp/results/tests/chute_d-2023-11-01T13:04:39.014000-nbp1-colour.png",
#                     depth_filename="/home/ubuntu/SimpleWebApp/results/tests/chute_d-2023-11-01T13:04:39.014000-nbp1-depth.png")

SendItToCloudServer(USERNAME="user", PASSWORD="pass",
                    url_address="http://127.0.0.1:5001", timeout=10,
                    stamp="/home/ubuntu/SimpleWebApp/results/tests/chute_d-2023-11-19T21-54-14.463000.txt", # this does not have to exist
                    colour="/home/ubuntu/SimpleWebApp/results/tests/chute_d-2023-11-19T21-54-14.463000-nbp2-colour.png",
                    depth="/home/ubuntu/SimpleWebApp/results/tests/chute_d-2023-11-19T21-54-14.463000-nbp2-depth.png")

