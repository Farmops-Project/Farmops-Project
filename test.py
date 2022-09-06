import time
def tele():
    y = 10
    if y <= 5 :
        sendTele = 1
    else :
        sendTele = 0
    return sendTele

try:
        payload = {'temperatur': 28.0, 'kelembapan': 69.0, 'pakan': 85.4072354874521, 'tank-minum': 0}
        for x in payload :
            z = x["pakan"]
            print(type(z))
        msg = 0
        while 0 == msg < 1 :
            if tele() == 1:
                print("halo")
                msg = msg + 1
            time.sleep(0.5)
        while True:
            print(msg)

except KeyboardInterrupt:
    print("salah")