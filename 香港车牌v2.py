# -*- coding: utf-8 -*-
"""香港车牌v2.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1MW5L16hKPnuBap1LTZcpxZ43jOX4K1LY
"""

# 环境安装
!pip uninstall tensorflow-gpu -y
!pip uninstall -y tensorflow
!pip install gast==0.3.2
!pip install tensorflow-gpu==1.14.0
!pip install easyocr

import os
import pathlib
if "models" in pathlib.Path.cwd().parts:
  while "models" in pathlib.Path.cwd().parts:
    os.chdir('..')
elif not pathlib.Path('models').exists():
  !git clone --depth 1 https://github.com/tensorflow/models

# Commented out IPython magic to ensure Python compatibility.
# %%bash 
# cd models/research
# # Compile protos.
# protoc object_detection/protos/*.proto --python_out=.
# # Install TensorFlow Object Detection API.
# cp object_detection/packages/tf1/setup.py .
# python -m pip install .

# Commented out IPython magic to ensure Python compatibility.
!git clone https://github.com/wAikAp/Car-License-Plate-Recognition
# %cd Car-License-Plate-Recognition

#
import numpy as np
import os
import sys
import tensorflow as tf
import cv2
import matplotlib as mpl
from matplotlib import pyplot as plt
from PIL import Image, ImageDraw, ImageFont
from object_detection.utils import ops as utils_ops
from object_detection.utils import label_map_util
from object_detection.utils import visualization_utils as vis_util
tf.compat.v1.disable_eager_execution()
import easyocr
reader = easyocr.Reader(['en'])
#store the img list
MODEL_NAME = './car_plate_model_110K'
PATH_TO_FROZEN_GRAPH = MODEL_NAME + '/frozen_inference_graph.pb'
PATH_TO_LABELS = './labelmap/labelmap.pbtxt'
font = ImageFont.truetype('./font/Uknumberplate-A4Vx.ttf', 30)

def load_images_to_array(inDirectory):    
    for img in os.listdir(inDirectory):

        if os.path.splitext(img)[-1] == '.jpg' or os.path.splitext(img)[-1] == '.jpeg' or os.path.splitext(img)[-1] == '.JPG' or os.path.splitext(img)[-1] == '.png' or os.path.splitext(img)[-1] == '.PNG':
            orgimg_list.append(img)

def load_image_into_numpy_array(image):
    (im_width, im_height) = image.size
    return np.array(image.getdata()).reshape(
        (im_height, im_width, 3)).astype(np.uint8)

def run_inference_for_single_image(image, graph):
    with graph.as_default():
        with tf.compat.v1.Session() as sess:
            # Get handles to input and output tensors
            ops = tf.compat.v1.get_default_graph().get_operations()
            all_tensor_names = {output.name for op in ops for output in op.outputs}
            tensor_dict = {}
            for key in ['num_detections', 'detection_boxes', 'detection_scores','detection_classes', 'detection_masks']:
                tensor_name = key + ':0'
                if tensor_name in all_tensor_names:
                    tensor_dict[key] = tf.compat.v1.get_default_graph().get_tensor_by_name(tensor_name)
            if 'detection_masks' in tensor_dict:
                # The following processing is only for single image
                detection_boxes = tf.squeeze(tensor_dict['detection_boxes'], [0])
                detection_masks = tf.squeeze(tensor_dict['detection_masks'], [0])
                # Reframe is required to translate mask from box coordinates to image coordinates and fit the image size.
                real_num_detection = tf.cast(tensor_dict['num_detections'][0], tf.int32)
                detection_boxes = tf.slice(detection_boxes, [0, 0], [real_num_detection, -1])
                detection_masks = tf.slice(detection_masks, [0, 0, 0], [real_num_detection, -1, -1])
                detection_masks_reframed = utils_ops.reframe_box_masks_to_image_masks(detection_masks, detection_boxes, image.shape[1], image.shape[2])
                detection_masks_reframed = tf.cast(tf.greater(detection_masks_reframed, 0.5), tf.uint8)
                # Follow the convention by adding back the batch dimension
                tensor_dict['detection_masks'] = tf.expand_dims(detection_masks_reframed, 0)
            image_tensor = tf.compat.v1.get_default_graph().get_tensor_by_name('image_tensor:0')
            # Run inference
            output_dict = sess.run(tensor_dict,feed_dict={image_tensor: image})
            
            # all outputs are float32 numpy arrays, so convert types as appropriate
            output_dict['num_detections'] = int(output_dict['num_detections'][0])
            output_dict['detection_classes'] = output_dict['detection_classes'][0].astype(np.int64)
            output_dict['detection_boxes'] = output_dict['detection_boxes'][0]
            output_dict['detection_scores'] = output_dict['detection_scores'][0]
            if 'detection_masks' in output_dict:
                output_dict['detection_masks'] = output_dict['detection_masks'][0]
    return output_dict

category_index = label_map_util.create_category_index_from_labelmap(PATH_TO_LABELS, use_display_name=True)
detection_graph = tf.Graph()
with detection_graph.as_default():
    od_graph_def = tf.compat.v1.GraphDef() 
    with tf.gfile.GFile(PATH_TO_FROZEN_GRAPH, 'rb') as fid:
        serialized_graph = fid.read()
        od_graph_def.ParseFromString(serialized_graph)
        tf.import_graph_def(od_graph_def, name='')

input_directory = 'test_images/'
orgimg_list = []   
load_images_to_array(input_directory)
input_directory = input_directory #get the images path with folder
print('*************************Total ',len(orgimg_list),' images in here*************************')
PATH_TO_TEST_IMAGES_DIR = input_directory
TEST_IMAGE_PATHS = []
image_list = [] 
for orgimg in orgimg_list:
    TEST_IMAGE_PATHS.append(os.path.join(PATH_TO_TEST_IMAGES_DIR, orgimg))
print('image_list = ',TEST_IMAGE_PATHS)

image_count = 1
print('******************detection start******************')

#image list for return
return_dic = {}
for image_path in TEST_IMAGE_PATHS:
    print('processing image: ',image_count,'/ ',len(TEST_IMAGE_PATHS),'.....','\nimage path:',image_path)
    image = Image.open(image_path)

    # the array based representation of the image will be used later in order to prepare the
    # result image with boxes and labels on it.
    if image.format == "PNG":
        #sRGB convert to RGB
        image = image.convert('RGB')
    image_np = load_image_into_numpy_array(image)
    # Expand dimensions since the model expects images to have shape: [1, None, None, 3]
    image_np_expanded = np.expand_dims(image_np, axis=0)
    # Actual detection.
    output_dict = run_inference_for_single_image(image_np_expanded, detection_graph)
    # Visualization of the results of a detection.
    vis_util.visualize_boxes_and_labels_on_image_array(
        image_np,
        output_dict['detection_boxes'],
        output_dict['detection_classes'],
        output_dict['detection_scores'],
        category_index,
        instance_masks=output_dict.get('detection_masks'),
        use_normalized_coordinates=True,
        line_thickness=3)#To change the line width of boxes: thickness=4 (change to number what you want) deafult is 4 

    plt.axis('off')
    #get the box coordinates
    boxes = output_dict['detection_boxes']
    # get all boxes from an array
    max_boxes_to_draw = boxes.shape[0]
    # get scores to get a threshold
    scores = output_dict['detection_scores']
    #Accuracy rate default 0.5
    min_score_thresh=.5
    #image array to store the box frame eg:"image_name1":[{"Land": [0.36901385, 0.2333157, 0.5195253, 0.3745013]}...]
    image_list = [] 
    #plate list since one image may have more than one plate
    plate_num_list = []
    
    #record the plate position on the image 
    position_x_min_list = []
    position_y_min_list = []
    
    #iterate over all objects found
    #loop all the objects 
    for i in range(min(max_boxes_to_draw, boxes.shape[0])):
        if scores is None or scores[i] > min_score_thresh:
            # boxes[i] is the box which will be drawn
            class_name = category_index[output_dict['detection_classes'][i]]['name']                
            
            #output_dict['detection_boxes']: ymin, xmin, ymax, xmax
            # ymin = yStart, xmin = xStart, ymax = yEnd , xmax = xEnd 
            ymin = boxes[i][0]
            xmin = boxes[i][1]
            ymax = boxes[i][2]
            xmax = boxes[i][3]
            #detected box area to image
            (d_ymin,d_xmin,d_ymax,d_xmax) = (ymin*image.height,xmin*image.width,ymax*image.height,xmax*image.width)
            cropped_image = tf.image.crop_to_bounding_box(image_np,int(d_ymin),int(d_xmin),int(d_ymax - d_ymin),int(d_xmax - d_xmin))
            with tf.compat.v1.Session() as sess:
                detect_cropped_image = sess.run(cropped_image)
                
                #image rgb to gary
                gray = cv2.cvtColor(detect_cropped_image, cv2.COLOR_BGR2GRAY)
                gray = cv2.threshold(gray, 0, 255,cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
                gray = cv2.medianBlur(gray, 3)
                
                #image to text white list for text
                custom_config = r'-c tessedit_char_whitelist=ABCDEFGHJKLMNPQRSTUVWXYZ1234567890 --psm 6'
                #record the x 
                position_x_min_list.append(xmin)
                position_y_min_list.append(ymin)
                
                
                #plate_path = out_dir_plate + '/' + orgimg_list[image_count-1]
                #cv2.imwrite(plate_path,gray)
                
            
            #return json format
            img_dic = {class_name: [d_ymin,d_xmin,d_ymax,d_xmax],'plate_num':""}
            image_list.append(img_dic)
            print(img_dic)
            
        return_dic[orgimg_list[image_count-1]] = image_list #add array to Dictionary

    #change format to image 
    im = Image.fromarray(image_np)
    
    #draw plate num to image
    for img_dir in image_list:
        car_plate_position = img_dir['Car_Plate']
        car_plate_num = img_dir['plate_num']
        draw = ImageDraw.Draw(im)
        margin_y = 100
        draw.text((car_plate_position[1], car_plate_position[0]), car_plate_num, font=font, fill='red') 
        
    
    #show the img
    plt.imshow(im)
    plt.show()
    im.save(r'output_images/%s' % orgimg_list[image_count-1])
    
    img = cv2.imread(r'output_images/%s' % orgimg_list[image_count-1])
    cropped = img[int(car_plate_position[0]):int(car_plate_position[2]), int(car_plate_position[1]):int(car_plate_position[3])]  # 裁剪坐标为[y0:y1, x0:x1]
    #print(int(car_plate_position[2]))
    cv2.imwrite(r'output_images/%s' % orgimg_list[image_count-1], cropped)

    result = reader.readtext(r'output_images/%s' % orgimg_list[image_count-1])
    plate_num=""
    for single_result in result:
        plate_num =plate_num+str(single_result[1])
    plate_num =plate_num.replace(" ","")
    print('plate number = ',plate_num)

    print('image',image_count,'/',len(orgimg_list),'finished.....')
    image_count+=1
    
    
print('******************Detection complete.******************')