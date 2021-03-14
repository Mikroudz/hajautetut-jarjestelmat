import paho.mqtt.client as mqtt #import the client1
import time
import json
from random import randrange, uniform

"""
def on_message(client, userdata, message):
    print("message received " ,str(message.payload.decode("utf-8")))

    clients = uniform(0, 100)
    client.publish("clients", clients)
"""

broker_address="127.0.0.1"

client = mqtt.Client("server") #create new instance
client.connect(broker_address) #connect to broker
client.loop_start()

while True:
    client_id = "server"
    clients = uniform(0, 100)
    dictionary = {
        "client_id": client_id,
        "clients": clients
    }
    client_number = json.dumps(dictionary)
    client.publish("clients", client_number)
    print("Message published", client_number)
    time.sleep(10)

client.loop_stop()