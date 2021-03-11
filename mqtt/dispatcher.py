import paho.mqtt.client as mqtt #import the client1
import time

def on_message(client, userdata, message):
    clients = str(message.payload.decode("utf-8"))
    print("Number of clients" ,clients)

broker_address="127.0.0.1"

client = mqtt.Client("dispatcher") #create new instance
client.on_message=on_message
client.connect(broker_address) #connect to broker
client.loop_start()
client.subscribe("clients")


while True:
    client.publish("call_clients", "CALL")
    time.sleep(10)

client.loop_stop()
