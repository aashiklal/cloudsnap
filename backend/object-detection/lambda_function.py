import boto3
import os
import io
import urllib
import zipfile
import cv2
import numpy as np
import time
import json
import uuid

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('cloudsnap-results-table')

confthres = 0.3
nmsthres = 0.1

def lambda_handler(event, context):
    # Get bucket name and file key from the event
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    user_id = str(uuid.uuid4())  # Generate a unique UUID


    bucket_for_zip = 'cloudsnap-configfiles-bucket' # defined bucket name for the zip file here
    bucket_for_images = 'cloudsnap-uploadedimages-bucket'

    try:
        # Download the zip file containing dependencies and extract them
        print(f"Downloading 'cloudsnap.zip' from bucket: {bucket_for_zip}")
        s3_client.download_file(bucket_for_zip, 'cloudsnap_object_detection.zip', '/tmp/dependencies.zip')
        with zipfile.ZipFile('/tmp/dependencies.zip', 'r') as zip_ref:
            zip_ref.extractall('/tmp')

        import cv2
        import numpy as np

        # Now your paths will be within /tmp directory
        yolo_path  = "/tmp"
        labelsPath= "coco.names"
        cfgpath= "yolov3-tiny.cfg"
        wpath= "yolov3-tiny.weights"

        # Load the COCO class labels our YOLO model was trained on
        lpath = os.path.sep.join([yolo_path, labelsPath])
        LABELS = open(lpath).read().strip().split("\n")

        # Load our YOLO object detector trained on COCO dataset (80 classes)
        print("[INFO] loading YOLO from disk...")
        weightsPath = os.path.sep.join([yolo_path, wpath])
        configPath = os.path.sep.join([yolo_path, cfgpath])
        net = cv2.dnn.readNetFromDarknet(configPath, weightsPath)

        # Download image from S3 bucket
        print(f"Downloading file {key} from bucket: {bucket_for_images}")
        s3_client.download_file(bucket_for_images, key, '/tmp/image.jpg')
        image = cv2.imread('/tmp/image.jpg')

        result = do_prediction(image, net, LABELS, key, user_id)

        # Insert detected objects to DynamoDB
        response = table.put_item(
            Item={
                'ImageID': user_id,
                'ImageURL': f'https://s3.amazonaws.com/{bucket}/{key}',
                'Tags': result
            }
        )

        return {
            'statusCode': 200,
            'body': 'Object detection completed successfully!'
        }

    except Exception as e:
        print(e)
        return {
            'statusCode': 500,
            'body': 'Error processing image!'
        }

def do_prediction(image, net, LABELS, image_id, user_id):
    # Your previous do_prediction function code goes here.
    (H, W) = image.shape[:2]
    # determine only the *output* layer names that we need from YOLO
    ln = net.getLayerNames()
    ln = [ln[i - 1] for i in net.getUnconnectedOutLayers()]

    # construct a blob from the input image and then perform a forward
    # pass of the YOLO object detector, giving us our bounding boxes and
    # associated probabilities
    blob = cv2.dnn.blobFromImage(image, 1 / 255.0, (416, 416),
                                 swapRB=True, crop=False)
    net.setInput(blob)
    start = time.time()
    layerOutputs = net.forward(ln)
    #print(layerOutputs)
    end = time.time()

    # show timing information on YOLO
    print("[INFO] YOLO took {:.6f} seconds".format(end - start))

    # initialize our lists of detected bounding boxes, confidences, and
    # class IDs, respectively
    tags = []
    boxes = []
    confidences = []
    classIDs = []
    result = {} # Creating an empty dictionary to store the result.

    # loop over each of the layer outputs
    for output in layerOutputs:
        # loop over each of the detections
        for detection in output:
            scores = detection[5:]
            classID = np.argmax(scores)
            confidence = scores[classID]

            if confidence > confthres:
                label = LABELS[classID]
                # Append the label to the 'tags' list.
                tags.append(label)

    # Count the occurrences of each tag.
    unique_tags = set(tags)
    result = [{"tag": tag, "count": int(tags.count(tag))} for tag in unique_tags]
    return result

        
        
