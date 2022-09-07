import Adafruit_DHT
import pymongo
import time
import requests
import RPi.GPIO as GPIO
import schedule
from multiprocessing import Process
import telepot
import time

token = "5760699009:AAGBKuDEw-4wrI58djCvJzgZNpn0GrLBQwY"
id = "-692036680"
bot = telepot.Bot(token)

client = pymongo.MongoClient("mongodb://altissimo:altissimo@ac-1k1ioje-shard-00-00.tktjcey.mongodb.net:27017,ac-1k1ioje-shard-00-01.tktjcey.mongodb.net:27017,ac-1k1ioje-shard-00-02.tktjcey.mongodb.net:27017/?ssl=true&replicaSet=atlas-wn5rne-shard-0&authSource=admin&retryWrites=true&w=majority")
db = client['Farmops']
inputPakan = db["input pakan"]
inputSuhu = db["input temperatur"]

TOKEN = "BBFF-thUhhRPJojoHiUB78bozuZuPy2dKTv"  # Put your TOKEN here
DEVICE_LABEL = "farmops"
VARIABLE_LABEL_1 = "temperatur"
VARIABLE_LABEL_2 = "kelembapan"
VARIABLE_LABEL_3 = "tank-pakan"
VARIABLE_LABEL_4 = "tank-minum"

#monitoring DHT
DHT = 4
RELAY_FAN = 17
RELAY_HEATER = 22
#tank pakan
GPIO_TRIGGER = 20
GPIO_ECHO = 21
#water sensor
GPIO_WTR = 26
GPIO_SOLENOID = 27
#servo
GPIO_SERVO = 16
#tank minum
GPIO_100 = 6
GPIO_50 = 13
GPIO_25 = 19

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(RELAY_FAN, GPIO.OUT)
GPIO.setup(RELAY_HEATER, GPIO.OUT)
GPIO.setup(GPIO_TRIGGER, GPIO.OUT)
GPIO.setup(GPIO_ECHO, GPIO.IN)
GPIO.setup(GPIO_WTR, GPIO.IN , pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(GPIO_SOLENOID, GPIO.OUT)
GPIO.setup(GPIO_SERVO, GPIO.OUT)
GPIO.setup(GPIO_100, GPIO.IN , pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(GPIO_50, GPIO.IN , pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(GPIO_25, GPIO.IN , pull_up_down=GPIO.PUD_DOWN)

dht = Adafruit_DHT.DHT11

servo = GPIO.PWM(GPIO_SERVO, 50)
servo.start(0)

tankMinum = 0

def build_payload(variable_1, variable_2, variable_3, variable_4):
    kelembapan, temperatur = Adafruit_DHT.read_retry(dht, DHT)
    #tank pakan
    GPIO.output(GPIO_TRIGGER, True)
    time.sleep(0.00001)
    GPIO.output(GPIO_TRIGGER, False)
 
    StartTime = time.time()
    StopTime = time.time()
 
    while GPIO.input(GPIO_ECHO) == 0:
        StartTime = time.time()
 
    while GPIO.input(GPIO_ECHO) == 1:
        StopTime = time.time()
 
    TimeElapsed = StopTime - StartTime
    tankPakan = (100 - ((((TimeElapsed * 34300) / 2) - 3 ) / 10.600 * 100))
    
    #tank minum
    if GPIO.input(GPIO_25) == 1 and GPIO.input(GPIO_50) == 0 and GPIO.input(GPIO_100) == 0 :
        tankMinum = 25
        print(tankMinum)
    elif GPIO.input(GPIO_25) == 1 and GPIO.input(GPIO_50) == 1 and GPIO.input(GPIO_100) == 0 :
        tankMinum = 50
        print(tankMinum)
    elif GPIO.input(GPIO_25) == 1 and GPIO.input(GPIO_50) == 1 and GPIO.input(GPIO_100) == 1 :
        tankMinum = 100
        print(tankMinum)
    else :
        tankMinum = 0
    
    payload = {
        variable_1: temperatur,
        variable_2: kelembapan,
        variable_3: tankPakan,
        variable_4: tankMinum
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
        VARIABLE_LABEL_1, VARIABLE_LABEL_2, VARIABLE_LABEL_3, VARIABLE_LABEL_4)
    print(payload)
    print("[INFO] Attemping to send data")
    post_request(payload)
    print("[INFO] finished")
    
def tempControl(tempHi, tempLo):
    kelembapan, temperatur = Adafruit_DHT.read_retry(dht, DHT)
    if temperatur != None and temperatur <= tempLo :
        GPIO.output(RELAY_HEATER, GPIO.LOW)
    elif temperatur != None and temperatur >= tempHi :
        GPIO.output(RELAY_FAN, GPIO.LOW)
    else:
        GPIO.output(RELAY_FAN, GPIO.HIGH)
        GPIO.output(RELAY_HEATER, GPIO.HIGH)
    time.sleep(1)

def waterSensor():
        #Water Sensor
    if GPIO.input(GPIO_WTR) == 0 :
        GPIO.output(GPIO_SOLENOID, GPIO.LOW)
        print("Pengisi minum menyala")
        time.sleep(10)
        GPIO.output(GPIO_SOLENOID, GPIO.HIGH)
        print("Pengisi minum mati")
        time.sleep(0.5)
    else :
        GPIO.output(GPIO_SOLENOID, GPIO.HIGH)
        
def setAngle(angle) :
    duty = angle / 18 + 2
    GPIO.output(16, True)
    servo.ChangeDutyCycle(duty)
    time.sleep(1)
    GPIO.output(16, False)
    servo.ChangeDutyCycle(0)
 
def servoPakan():
    setAngle(0)
    setAngle(180)
    time.sleep(5)
    
def jadwalPakan():
    for dataPakan in inputPakan.find().sort([('_id', -1)]).limit(1) :
        jamPakan = dataPakan["jamPakan"]
        jamPakan2 = dataPakan["jamPakan2"]
        jamPakan3 = dataPakan["jamPakan3"]
            
    schedule.every().day.at(jamPakan).do(servoPakan)
    schedule.every().day.at(jamPakan2).do(servoPakan)
    schedule.every().day.at(jamPakan3).do(servoPakan)
    
def tele():
    payload = build_payload(
        VARIABLE_LABEL_1, VARIABLE_LABEL_2, VARIABLE_LABEL_3, VARIABLE_LABEL_4)
    pakan = payload['tank-pakan']
    if pakan <= 5 :
        sendTele = 1
    else :
        sendTele = 0
    return sendTele
        
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
        msg = 0
        while msg == 0 and msg < 1 :
            if tele() == 1 :
                bot.sendMessage(id, "pakan ayam habis, tolong kirim hari ini ya")
                msg = msg + 1
            break
        
        while True:
            for dataSuhu in inputSuhu.find().sort([('_id', -1)]).limit(1) :
                tempHi = int(dataSuhu["tempHi"])
                tempLo = int(dataSuhu["tempLo"])
            if msg == 1 and tele() == 0:
                msg = msg - 1
            runInParallel(main, tempControl(tempHi, tempLo), waterSensor, jadwalPakan, schedule.run_pending())
            time.sleep(1)
            
    except KeyboardInterrupt:
        GPIO.cleanup()