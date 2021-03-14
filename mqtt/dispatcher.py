import paho.mqtt.client as mqtt #import the client1
import time
import json

def on_message(client, userdata, message):
    message = str(message.payload.decode("utf-8"))
    dictionary = json.loads(message)
    clients = dictionary["clients"]
    client_id = dictionary["client_id"]
    print("Number of clients" ,clients)
    print("Client id", client_id)

broker_address="127.0.0.1"

client = mqtt.Client("dispatcher") #create new instance
client.on_message=on_message
client.connect(broker_address) #connect to broker
client.subscribe("clients")
client.loop_forever()
