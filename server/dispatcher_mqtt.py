import argparse
import asyncio
import json
import logging
import os
import ssl
import uuid

from aiohttp import web
from aiohttp import ClientSession
from av import VideoFrame

from aiortc import MediaStreamTrack, RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaBlackhole, MediaPlayer, MediaRecorder

import paho.mqtt.client as mqtt
# import context
import datetime

ROOT = os.path.dirname(__file__)

logger = logging.getLogger("pc")
pcs = set()

connections = {}

### Subscriber
# The callback function of connection
def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    client.subscribe("Number of connections")
    
# The callback function for received message
def on_message(client, userdata, msg):
    host = json.loads(msg.payload)["host"]
    cons = json.loads(msg.payload)["num_of_connections"] 
    timestamp = datetime.datetime.now().timestamp()
    connections[host] = (cons, timestamp) 
    print(f"Added host {host} with {cons} connections")
    print(f"Timestamp: {timestamp}")
    
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect("localhost", 1883, 60)
#client.loop_forever()
client.loop_start()

def least_connections():

    global connections
    # newest = max([i["host"][1] for i in connections])
    timeslot = datetime.datetime.now().timestamp() - (10)
    
    lc_host = connections.keys()[0]
    for (key, value) in connections.items():
        if value[1] > timeslot and\
                value[0] < lc_host["host"][0]:
            lc_host = key
    return key

        

async def index(request):
    content = open(os.path.join(ROOT, "index.html"), "r").read()
    return web.Response(content_type="text/html", text=content)


async def javascript(request):
    content = open(os.path.join(ROOT, "client.js"), "r").read()
    return web.Response(content_type="application/javascript", text=content)

## Tähän tulee client-verkkosivulta WebRTC-pyynnöt
async def offer(request):
    # Hae post-requestin parametrin. ELi tässä on se sdp-data clientiltä json-muodossa
    params = await request.json()
    #logger.info(offer)
    # Välitä json data eteenpäin 8081-portissa toimivalle videopalvelimelle
    async with ClientSession() as session:
        # Kutsu algoritmia #
        lc_host = least_connections()

        # res = await session.post('http://localhost:8081/offer', json=params)
        res = await session.post(f'{lc_host}:8081/offer', json=params)
    #Lue vastaus videopalvelimelta
    sdp_data = await res.json()
    # Palauta clientin responseen videopalvelimen sdp-data json-muodossa
    return web.Response(
        content_type="application/json",
        text=json.dumps(sdp_data),)

async def on_shutdown(app):
    # close peer connections
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="WebRTC audio / video / data-channels demo"
    )
    parser.add_argument("--cert-file", help="SSL certificate file (for HTTPS)")
    parser.add_argument("--key-file", help="SSL key file (for HTTPS)")
    parser.add_argument(
        "--host", default="0.0.0.0", help="Host for HTTP server (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", type=int, default=8080, help="Port for HTTP server (default: 8080)"
    )
    parser.add_argument("--verbose", "-v", action="count")
    parser.add_argument("--write-audio", help="Write received audio to a file")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    if args.cert_file:
        ssl_context = ssl.SSLContext()
        ssl_context.load_cert_chain(args.cert_file, args.key_file)
    else:
        ssl_context = None

    app = web.Application()
    app.on_shutdown.append(on_shutdown)
    app.router.add_get("/", index)
    app.router.add_get("/client.js", javascript)
    app.router.add_post("/offer", offer)
    web.run_app(
        app, access_log=None, host=args.host, port=args.port, ssl_context=ssl_context
    )
