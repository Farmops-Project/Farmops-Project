import Adafruit_DHT
import time
import requests
from ubidots import ApiClient
import RPi.GPIO as GPIO

TOKEN = "BBFF-thUhhRPJojoHiUB78bozuZuPy2dKTv"  # Put your TOKEN here
DEVICE_LABEL = "farmops"  # Put your device label here 
VARIABLE_LABEL_1 = "temperatur"  # Put your first variable label here
VARIABLE_LABEL_2 = "kelembapan"  # Put your second variable label here

api = ApiClient(token="BBFF-thUhhRPJojoHiUB78bozuZuPy2dKTv")
tempHi = api.get_variable("62ffaf3d57021d11c524c9a5")
tempLo = api.get_variable("62ffaf97a6ecfc1fe89212fb")

DHT = 4
RELAY_FAN = 17
RELAY_HEATER = 22

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.OUT)
GPIO.setup(22, GPIO.OUT)

def build_payload(variable_1, variable_2):
    # Creates two random values for sending data

    sensor = Adafruit_DHT.DHT11
    kelembapan, temperatur = Adafruit_DHT.read_retry(sensor, DHT)
    
    value_1 = temperatur
    value_2 = kelembapan
    
    payload = {
        variable_1: value_1,
        variable_2: value_2
    }
    
    if value_1 <= 25 :
        GPIO.output(22, GPIO.HIGH)
    elif value_1 >= 30 :
        GPIO.output(17, GPIO.HIGH)
    else:
        GPIO.output(17, GPIO.LOW)
        GPIO.output(22, GPIO.LOW)
    
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
        VARIABLE_LABEL_1, VARIABLE_LABEL_2)
    print(payload)
    print("[INFO] Attemping to send data")
    post_request(payload)
    print("[INFO] finished")


if __name__ == '__main__':
    while (True):
        main()
        time.sleep(1)
