import paho.mqtt.client as mqtt #import the client1
import time
from random import randrange, uniform

def on_message(client, userdata, message):
    print("message received " ,str(message.payload.decode("utf-8")))

    clients = uniform(0, 100)
    client.publish("clients", clients)

broker_address="127.0.0.1"

client = mqtt.Client("server") #create new instance
client.on_message=on_message #attach function to callback
client.connect(broker_address) #connect to broker

client.subscribe("call_clients")
client.loop_forever()