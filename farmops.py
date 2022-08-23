import Adafruit_DHT
import pymongo
import time
import requests
import RPi.GPIO as GPIO
import schedule
from ubidots import ApiClient
from multiprocessing import Process

client = pymongo.MongoClient("mongodb://altissimo:altissimo@ac-1k1ioje-shard-00-00.tktjcey.mongodb.net:27017,ac-1k1ioje-shard-00-01.tktjcey.mongodb.net:27017,ac-1k1ioje-shard-00-02.tktjcey.mongodb.net:27017/?ssl=true&replicaSet=atlas-wn5rne-shard-0&authSource=admin&retryWrites=true&w=majority")
db = client['Farmops']
my_collections = db["Data input"]

TOKEN = "BBFF-thUhhRPJojoHiUB78bozuZuPy2dKTv"  # Put your TOKEN here
DEVICE_LABEL = "farmops"  # Put your device label here 
VARIABLE_LABEL_1 = "temperatur"  # Put your first variable label here
VARIABLE_LABEL_2 = "kelembapan"  # Put your second variable label here
VARIABLE_LABEL_3 = "tank-pakan"

api = ApiClient(token="BBFF-thUhhRPJojoHiUB78bozuZuPy2dKTv")
tempHi = api.get_variable("62ffaf3d57021d11c524c9a5")
tempLo = api.get_variable("62ffaf97a6ecfc1fe89212fb")
pakan = api.get_variable("6301f9ff1f9dff32b3c7e828")

#monitoring DHT
DHT = 4
RELAY_FAN = 17
RELAY_HEATER = 22
#ultrasonic
GPIO_TRIGGER = 20
GPIO_ECHO = 21
#water sensor
GPIO_WTR = 26
GPIO_SOLENOID = 27
#servo
GPIO_SERVO = 16

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(RELAY_FAN, GPIO.OUT)
GPIO.setup(RELAY_HEATER, GPIO.OUT)
GPIO.setup(GPIO_TRIGGER, GPIO.OUT)
GPIO.setup(GPIO_ECHO, GPIO.IN)
GPIO.setup(GPIO_WTR, GPIO.IN , pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(GPIO_SOLENOID, GPIO.OUT)
GPIO.setup(GPIO_SERVO, GPIO.OUT)

servo = GPIO.PWM(GPIO_SERVO, 50)
servo.start(0)
duty = 0
dataMongo = my_collections.find().sort([('_id', -1)]).limit(1)


def build_payload(variable_1, variable_2,variable_3):
    #DHT
    sensor = Adafruit_DHT.DHT11
    kelembapan, temperatur = Adafruit_DHT.read_retry(sensor, DHT)
    
    value_tempHi = tempHi.get_values(1)
    value_tempLo = tempLo.get_values(1)
    
    dataTempHi = value_tempHi[0].get("value")
    dataTempLo = value_tempLo[0].get("value")

    
    if temperatur != None and temperatur <= dataTempLo :
        GPIO.output(22, GPIO.LOW)
    elif temperatur != None and temperatur >= dataTempHi :
        GPIO.output(17, GPIO.LOW)
    else:
        GPIO.output(17, GPIO.HIGH)
        GPIO.output(22, GPIO.HIGH)
    
    #Ultrasonic
    GPIO.output(GPIO_TRIGGER, True)
    time.sleep(0.00001)
    GPIO.output(GPIO_TRIGGER, False)
 
    StartTime = time.time()
    StopTime = time.time()
 
    # save StartTime
    while GPIO.input(GPIO_ECHO) == 0:
        StartTime = time.time()
 
    # save time of arrival
    while GPIO.input(GPIO_ECHO) == 1:
        StopTime = time.time()
 
    # time difference between start and arrival
    TimeElapsed = StopTime - StartTime
    tankPakan = (100 - (((TimeElapsed * 34300) / 2 - 2) / 20 * 100))
    
    payload = {
        variable_1: temperatur,
        variable_2: kelembapan,
        variable_3: tankPakan
    }
    return payload

def post_request(payload):
    # Creates the headers for the HTTP requests
    url = "http://industrial.api.ubidots.com"
    url = "{}/api/v1.6/devices/{}".format(url, DEVICE_LABEL)
    headers = {"X-Auth-Token": TOKEN, "Content-Type": "application/json"}

    # Makes the HTTP requests
    status = 400
    attempts = 0
    while status >= 400 and attempts <= 5:
        req = requests.post(url=url, headers=headers, json=payload)
        status = req.status_code
        attempts += 1
        time.sleep(1)

    # Processes results
    if status >= 400:
        print("[ERROR] Could not send data after 5 attempts, please check \
            your token credentials and internet connection")
        return False

    print("[INFO] request made properly, your device is updated")
    return True


def main():
    payload = build_payload(
        VARIABLE_LABEL_1, VARIABLE_LABEL_2, VARIABLE_LABEL_3)
    print(payload)
    print("[INFO] Attemping to send data")
    post_request(payload)
    print("[INFO] finished")

def waterSensor(cek):
        #Water Sensor
    if GPIO.input(26) == 0 :
        GPIO.output(27, GPIO.LOW)
        print("Pengisi minum menyala")
        time.sleep(5)
        GPIO.output(27, GPIO.HIGH)
        time.sleep(0.5)
    else :
        GPIO.output(27, GPIO.HIGH)
        print("Pengisi minum mati")
        time.sleep(2)
        
def servoPakan() :
    servo.ChangeDutyCycle(duty)

    servo.ChangeDutyCycle(7)
    time.sleep(2)
    servo.ChangeDutyCycle(2)
    time.sleep(0.5)
    servo.ChangeDutyCycle(0)
    print("Pakan diberikan")
    time.sleep(1)
        
def runInParallel(*fns):
  proc = []
  for fn in fns:
    p = Process(target=fn)
    p.start()
    proc.append(p)
  for p in proc:
    p.join()


if __name__ == '__main__':
    try :
        while (True):  
            dataMongo = my_collections.find().sort([('_id', -1)]).limit(1)
            for x in dataMongo:
                jamPakan = x["jamPakan"]
            schedule.every().day.at(jamPakan).do(servoPakan)
            runInParallel(main, waterSensor(5),  schedule.run_pending())
            time.sleep(1)
           
    except KeyboardInterrupt:
        GPIO.cleanup()
