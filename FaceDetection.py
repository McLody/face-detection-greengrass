# import greengrasssdk
import time
import cv2
import numpy as np
from threading import Thread
# import boto3
import base64
import json
# from botocore.exceptions import ClientError
import multiprocessing as mp

# Creating a greengrass core sdk client
# client = greengrasssdk.client('iot-data')

iotTopic = 'face_detection'
errTopic = 'detection_failed'

secret_name = "greengrass-lambda-access-s3-secretkey"
region_name = "-east-1"
secret = ''
access_key_id=''
access_secret_key=''

faceCascade = cv2.CascadeClassifier('Cascades/haarcascade_frontalface_default.xml')

# def get_secret():
    
#     # Create a Secrets Manager client
#     session = boto3.session.Session()
#     client = session.client(
#         service_name='secretsmanager',
#         region_name=region_name
#     )
#     # In this sample we only handle the specific exceptions for the 'GetSecretValue' API.
#     # See https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
#     # We rethrow the exception by default.
#     try:
#         get_secret_value_response = client.get_secret_value(SecretId=secret_name)
#     except ClientError as e:
#         print(e)
#         if e.response['Error']['Code'] == 'DecryptionFailureException':
#             # Secrets Manager can't decrypt the protected secret text using the provided KMS key.
#             # Deal with the exception here, and/or rethrow at your discretion.
#             raise e
#         elif e.response['Error']['Code'] == 'InternalServiceErrorException':
#             # An error occurred on the server side.
#             # Deal with the exception here, and/or rethrow at your discretion.
#             raise e
#         elif e.response['Error']['Code'] == 'InvalidParameterException':
#             # You provided an invalid value for a parameter.
#             # Deal with the exception here, and/or rethrow at your discretion.
#             raise e
#         elif e.response['Error']['Code'] == 'InvalidRequestException':
#             # You provided a parameter value that is not valid for the current state of the resource.
#             # Deal with the exception here, and/or rethrow at your discretion.
#             raise e
#         elif e.response['Error']['Code'] == 'ResourceNotFoundException':
#             # We can't find the resource that you asked for.
#             # Deal with the exception here, and/or rethrow at your discretion.
#             raise e
#     else:
#         # Decrypts secret using the associated KMS CMK.
#         # Depending on whether the secret is a string or binary, one of these fields will be populated.
#         if 'SecretString' in get_secret_value_response:
#             global secret
#             secret = get_secret_value_response['SecretString']
#         else:
#             decoded_binary_secret = base64.b64decode(get_secret_value_response['SecretBinary'])

# get_secret()
# secret_json = json.loads(secret)
# access_key_id = secret_json['access_key_id']
# access_secret_key = secret_json['access_secret_key']

# clientS3 = boto3.client(
#     's3',
#     aws_access_key_id = access_key_id,
#     aws_secret_access_key = access_secret_key
# )

# bucket='greengrass-detect-realtime-video-702586307767'

def getFrame(q):
    cap = cv2.VideoCapture('/dev/video0')
    cap.set(3,640) # set Width
    cap.set(4,480) # set Height
    while True:
        st = time.time()
        ret, frame = cap.read()
        if not(ret):
            cap.release()
            cap = cv2.VideoCapture('/dev/video0')
            cap.set(3,640) # set Width
            cap.set(4,480) # set Height
            continue
        q.put(frame)
        if q.qsize() > 1:
            for i in range(q.qsize() - 1):
                q.get()

def detectFaces():
    count = 0
    try:
        frame = queue.get()
        if frame is None:
            print("queue.get() is None")
        if len(frame) == 0:
            raise Exception("Failed to get frame from the stream")
        
        while True:
            time.sleep(0.1)

            if(queue.qsize()==0):
                print("queue size == ",queue.qsize())
                continue
            frame = queue.get()

            if frame is None:
                continue
            else:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = faceCascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(20, 20))
                faceNum = len(faces)

            if faceNum > 70.0 :
                try:
                    for (x,y,w,h) in faces:
                        cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)

                    imgID = time.strftime("%Y%m%d%H%M%S")
                    cv2.imwrite(imgID + '.jpg', frame)
                    count += 1
                    if count == 10 :
                        break
                
                except IOError as e:
                    print("err: ",str(e))                
           
    except Exception as e:
        print(str(e))

class Frame_Thread(Thread):
    def __init__(self):
        ''' Constructor. '''
        Thread.__init__(self)
        
    def run(self):
        mp.set_start_method('fork',True)
        process = mp.Process(target = getFrame,args=(queue,))
        process.daemon = True
        process.start()
        
queue = mp.Queue(maxsize=4)
frame_thread = Frame_Thread()
frame_thread.start()

frame = queue.get()

detectFaces()

