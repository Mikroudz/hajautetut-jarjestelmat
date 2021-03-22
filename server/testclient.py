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

## Pyydetään dispatcherilta WebRTC-streami
async def ask_stream(interval):
    global blackhole
    await asyncio.sleep(interval)
    print("Haetaan streami")
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

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        log_info("Connection state is %s", pc.connectionState)
        if pc.connectionState == "failed":
            await pc.close()
            pcs.discard(pc)
    status = False
    session = ClientSession()
    # POST-pyyntö dispatcherille
    while not status:
        status = True
        await asyncio.sleep(1)
        try:
            res = await session.post('https://localhost:8080/offer', json=params,ssl=False, timeout=3)
        except:
            status = False
            continue
        print("onko jumissa")
        if res.status == "500":
            status = False
            continue
        try:
            result = await res.json()
        except:
            status = False
            continue
    answer = RTCSessionDescription(sdp=result["sdp"], type=result["type"])
    await session.close()
    #print(answer.sdp)
    await pc.setRemoteDescription(answer)


async def generate_client(interval, clients):
    for i in range(clients):
        tasks = set()
        task = asyncio.create_task(ask_stream(interval * i))
        tasks.add(task)
        print("Client %d added", i)

    print("Client generated!")
    return await asyncio.gather(*tasks)

            

async def on_shutdown():
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
    parser.add_argument("--clients", default=1, help="How many clients to create")
    parser.add_argument("--client_interval", default=1, help="How long wait between client creation")


    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    #loop.run_until_complete(tasks)
    try:
        asyncio.run(generate_client(interval=float(args.client_interval), clients=int(args.clients)))
    except KeyboardInterrupt as e:
        asyncio.run(on_shutdown)
        loop.close()