#Testiclient kesken
import argparse
import asyncio
import json
import logging
import os
import ssl
import uuid
import time

import paho.mqtt.client as mqtt
from aiohttp import web
from aiohttp import ClientSession
from aiortc import MediaStreamTrack, RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaBlackhole, MediaPlayer, MediaRecorder, MediaRelay

ROOT = os.path.dirname(__file__)

#logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("pc")
pcs = set()

relay = MediaRelay()
broadcast = None
blackhole = MediaBlackhole()

def create_broadcast(track):
    global broadcast
    broadcast = track

def broadcast_ended():
    global broadcast
    broadcast = None

## Pyydetään dispatcherilta WebRTC-streami
async def ask_stream(ask_stream):
    global blackhole
    print("Haetaan streami")
    ## TODO: testaa onko meillä streami olemassa
    pc = RTCPeerConnection()
    pc_id = "PeerConnection(%s)" % uuid.uuid4()

    pcs.add(pc)
    def log_info(msg, *args):
        logger.info(pc_id + " " + msg, *args)
    # Videolle on kanava "track"
    pc.createDataChannel("track")
    pc.addTransceiver("video",direction="recvonly")
    # Tämä luo itse offerin oikeassa muodossa
    await pc.setLocalDescription(await pc.createOffer())
    # Asetetaan pyynnön parametreiksi
    params =  {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type, "listen_video": True}

    @pc.on("track")
    def on_track(track):
        log_info("Track %s received from other server", track.kind)
        blackhole.addTrack(track)
        '''
        if track.kind == "audio":
            pc.addTrack(player.audio)
        elif track.kind == "video":
            create_broadcast(track)
            pc.addTrack(relay.subscribe(broadcast))
        '''
        @track.on("ended")
        async def on_ended():
            log_info("Track %s ended", track.kind)
            broadcast = None

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        log_info("Connection state is %s", pc.connectionState)
        if pc.connectionState == "failed":
            await pc.close()
            pcs.discard(pc)
    # POST-pyyntö dispatcherille
    async with ClientSession() as session:
        res = await session.post('http://localhost:8080/offer', json=params,ssl=False)
    result = await res.json()

    answer = RTCSessionDescription(sdp=result["sdp"], type=result["type"])
    #print(answer.sdp)
    await pc.setRemoteDescription(answer)


async def generate_client(interval, clients):
    for i in range(clients):
        await ask_stream(args.ask_stream)
        print("Client %d added", i)
        await asyncio.sleep(interval)


async def on_shutdown(app):
    # close peer connections
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="WebRTC audio / video / data-channels demo"
    )
    parser.add_argument(
        "--host", default="0.0.0.0", help="Host for HTTP server (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", type=int, default=8080, help="Port for HTTP server (default: 8080)"
    )
    parser.add_argument("--verbose", "-v", action="count")
    parser.add_argument("--write-audio", help="Write received audio to a file")
    parser.add_argument("--ask-stream", default="False", help="Write received audio to a file")

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    ssl_context = None

    loop = asyncio.get_event_loop()

    #app = web.Application()
    #app.on_shutdown.append(on_shutdown)
    #app.router.add_post("/offer", offer)
    '''
    client = mqtt.Client()
    client.on_connect = on_connect
    client.connect("localhost", 1883, 60)
    client.loop_start()
    
    async def web_runner():
        runner = web.AppRunner(app, access_log=None)
        await runner.setup()
        site = web.TCPSite(runner, port=args.port, host=args.host, ssl_context=ssl_context)
        await site.start()
        print("Web server started in %s port %s " % (args.host, args.port))
    '''

    tasks = asyncio.gather(
        generate_client(interval=1, clients=10)
    )

    loop.run_until_complete(tasks)
    try:
        loop.run_forever()
    except KeyboardInterrupt as e:
        loop.close()