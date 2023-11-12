import os
import requests
import pathlib

def SendItToCloudServer(url_address: str, timeout: int, stamp: str, depth: str, colour: str=None):

    stamp = stamp.replace(":", "-") # converted to % when receved by webapp
    entries = [(stamp, "/stamp", "txt"), (depth, "/depth", "image/png"), (colour, "/colour", "image/png")]
    for entry in entries:
        if entry[0] is not None:
            try:
                
                if entry[1]=="/stamp":
                    result_upload = requests.post(
                        url=url_address + entry[1],
                        headers={"Content-type": entry[2]},
                        data={"stamp": os.path.basename(stamp).strip(".txt")},
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

    if colour is not None:
        try:
            result_process = requests.post(
                # url=url_address + "/process/" + os.path.basename(stamp).strip(".txt"),
                url=url_address + "/process/" + os.path.basename(colour),
                timeout=timeout,
            )
            if result_process.status_code != 200:
                print("result process status: {} {}".format(result_process.status_code, result_process.content))
        except Exception as err:
            raise FileExistsError("SendItToCloudServer failed process error={}".format(err))

SendItToCloudServer(url_address="http://127.0.0.1:5002", timeout=10,
                    stamp="/home/ubuntu/EcoVision/ecolog/chute_d-2023-11-01T13:04:39.014000.txt", # this does not have to exist
                    colour=None, # "/home/ubuntu/SimpleWebApp/uploads/chute_d-2023-11-01T13:04:39.014000-nbp1-colour.png",
                    depth="/home/ubuntu/SimpleWebApp/uploads/chute_d-2023-11-01T13:04:39.014000-nbp1-depth.png")
