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
import base64

from botocore.exceptions import ClientError

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('cloudsnap-results-table')

confthres = 0.3
nmsthres = 0.1

def lambda_handler(event, context):
    cors_headers = {
        "Access-Control-Allow-Origin": "*",  # This allows any origin
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Methods": "OPTIONS,POST"
    }

    # Parse the event body from a string to a dictionary
    body = json.loads(event.get('body', '{}'))

    # Get the imageFile from the event body
    imageFile = body.get('imageFile', '')
    print(event)

    # Save the Base64-encoded image as a file
    with open('/tmp/image.jpg', 'wb') as f:
        f.write(base64.b64decode(imageFile))
    
    # Add your bucket name here
    bucket_for_zip = 'cloudsnap-configfiles-bucket' # define your bucket name for the zip file here
    bucket_for_images = 'cloudsnap-configfiles-bucket'
    # Generate a unique key for the image file to avoid conflicts
    key = str(uuid.uuid4()) + ".jpg"

    # Upload the image to S3 bucket
    s3_client.upload_file('/tmp/image.jpg', bucket_for_images, key)
    
    try:

        # Download the zip file containing dependencies and extract them
        print(f"Downloading 'cloudsnap_searchbyimage.zip' from bucket: {bucket_for_zip}")
        s3_client.download_file(bucket_for_zip, 'cloudsnap_search_by_image.zip', '/tmp/dependencies.zip')
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


        # Download the image from S3 bucket
        s3_client.download_file(bucket_for_images, key, '/tmp/image.jpg')
        image = cv2.imread('/tmp/image.jpg')

        result = do_prediction(image, net, LABELS, key)

        # The detected tags are used to search for similar images
        response = table.scan()

        matching_image_urls = []

        for item in response['Items']:
            item_tags = item['Tags']
            
            match = all(any(tag_db['tag'] == tag_query['tag'] and tag_db['count'] >= tag_query['count'] for tag_db in item_tags) for tag_query in result)

            if match:
                matching_image_urls.append(item['ImageURL'])

        if len(matching_image_urls) == 0:
            # Assume 'ImageURL' is the primary key of your table
            try:
                table.delete_item(
                    Key={
                        'ImageURL': f"https://s3.amazonaws.com/{bucket_for_images}/{key}"
                    }
                )
            except ClientError as e:
                print(f"Failed to delete item from DynamoDB: {e}")
            
            return {
                'statusCode': 404,
                'headers': cors_headers,
                'body': json.dumps('No matching images found.')
            }

        # return the list of image URLs
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps(matching_image_urls)
        }
    
    except Exception as e:
        print(e)
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': 'Error processing request!'
        }

    finally:
    # Delete the image from the local '/tmp' directory after processing
        if os.path.exists('/tmp/image.jpg'):
            os.remove('/tmp/image.jpg')

        # Delete the image from the S3 bucket after processing
        s3_client.delete_object(Bucket=bucket_for_images, Key=key)

        # Assume 'ImageURL' is the primary key of your table
        try:
            table.delete_item(
                Key={
                    'ImageURL': f"https://s3.amazonaws.com/{bucket_for_images}/{key}"
                }
            )
        except ClientError as e:
            print(f"Failed to delete item from DynamoDB: {e}")


def do_prediction(image, net, LABELS, image_id):
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
    end = time.time()

    # show timing information on YOLO
    print("[INFO] YOLO took {:.6f} seconds".format(end - start))

    tags = []
    boxes = []
    confidences = []
    classIDs = []
    result = {} 

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
