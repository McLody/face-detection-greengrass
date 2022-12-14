
import time
import cv2
import numpy as np
import boto3
from botocore.exceptions import ClientError
import json
import os
from threading import Thread
import multiprocessing as mp
import random
import sys


iotTopic = 'face_detection'
errTopic = 'detection_failed'

secret_name = "greengrass-lambda-access-s3-secretkey"
region_name = "us-east-1"
secret_json = ''
access_key_id=''
access_secret_key=''



def get_secret():
    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        # For a list of exceptions thrown, see
        # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
        raise e

    # Decrypts secret using the associated KMS key.
    global secret_json
    secret_json = get_secret_value_response['SecretString']

get_secret()
secret = json.loads(secret_json)
access_key_id = secret['access_key_id']
access_secret_key = secret['access_secret_key']

print("get secret")

s3 = boto3.client(
    's3',
    aws_access_key_id = access_key_id,
    aws_secret_access_key = access_secret_key
)

print("get s3")

# def download_file(s3, bucket_name, key_name):
#     file_name = key_name.split('/')[-1]
#     content_dir = key_name.replace(file_name, '')

#     # resource_local = os.path.join(local_save_path, content_dir)  # 本地存储路径
#     # logger.info(f" 本地存储路径 resource_local = {resource_local}")
#     if not os.path.exists(content_dir):
#         os.makedirs(content_dir)

#     local_storage = os.path.join(content_dir, file_name)  # 本地存储路径全路径
    
#     if os.path.exists(local_storage):
#         return
#     try:
#         with open(local_storage, 'wb') as f:
#             s3.download_fileobj(bucket_name, key_name, f)
#             f.close()
#     except OSError as e:
#         return


# bucket = s3.Bucket('greengrass-detect-realtime-video-702586307767')
bucket = 'greengrass-detect-realtime-video-702586307767'
# if not os.path.exists("haarcascade_frontalface_default.xml"):
#     resp = s3.get_object(Bucket = bucket, Key = "haarcascade_frontalface_default.xml")
    # bucket.download_file("haarcascade_frontalface_default.xml", "haarcascade_frontalface_default.xml", ExtraArgs=None, Callback=None, Config=None)
# faceCascadeXml = s3.get_object(Bucket = bucket, Key = "haarcascade_frontalface_default.xml")
# faceCascade = cv2.CascadeClassifier(faceCascadeXml)
# route = 'Cascades/haarcascade_frontalface_default.xml'
route = sys.argv[1]
# download_file(s3, bucket, route)
faceCascade = cv2.CascadeClassifier(route)

print("get faceCascade")

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

def del_files(dir_path):
    if os.path.isfile(dir_path):
        try:
            os.remove(dir_path)
        except BaseException as e:
            print(e)
    elif os.path.isdir(dir_path):
        file_lis = os.listdir(dir_path)
        for file_name in file_lis:
            tf = os.path.join(dir_path, file_name)
            del_files(tf)


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
                faces = faceCascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=4, minSize=(20, 20))
                faceNum = len(faces)

            if faceNum >= 1 :
                print("detect face.")
                try:
                    for (x,y,w,h) in faces:
                        cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)

                    imgID = "image-" + time.strftime("%Y%m%d%H%M%S") + str(random.randint(0,9)) + '.jpg'
                    cv2.imwrite(imgID, frame)
                    global s3, bucket, jpg
                    resp = s3.put_object(Bucket = bucket, Body = open(imgID, 'rb'), Key = imgID)
                    # resp = s3.put_object(Bucket = bucket, Body = jpg.tobytes(), Key = imgID)
                    print("upload the image")
                    del_files(imgID)
                    count += 1
                    if count == 2 :
                        break
                
                except IOError as e:
                    print("err: ",str(e))    

            else:
                ret, jpg = cv2.imencode('.jpg', frame)
                print("detect nothing.")            
           
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
ret, jpg = cv2.imencode('.jpg', frame)

detectFaces()



