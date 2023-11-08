https://vinleonardo.com/detecting-objects-in-pictures-and-extracting-their-data-using-mmdetection/



result = inference_detector(model, img_path)

bbox_result = result
# if instance segmentation
# bbox_result, segm_result = result
labels = [
    np.full(bbox.shape[0], i, dtype=np.int32)\
    for i, bbox in enumerate(bbox_result)
]
labels = np.concatenate(labels)
bboxes = np.vstack(bbox_result)
labels_impt = np.where(bboxes[:, -1] > 0.3)[0]

classes = get_classes("coco")
labels_impt_list = [labels[i] for i in labels_impt]
labels_class = [classes[i] for i in labels_impt_list]


geting one crop

# Importing Image class from PIL module
from PIL import Image

# Opens a image in RGB mode
im = Image.open(img_path)

# Size of the image in pixels (size of original image)
# (This is not mandatory)
width, height = im.size

# Setting the points for cropped image
left = bboxes[labels_impt][0][0]
top = bboxes[labels_impt][0][1]
right = bboxes[labels_impt][0][2]
bottom = bboxes[labels_impt][0][3]

# Cropped image of above dimension
# (It will not change original image)
im1 = im.crop((left, top, right, bottom))

# Shows the image in image viewer
im1.show()