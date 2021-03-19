import argparse
import asyncio
import json
import logging
import os
import ssl
import uuid

import paho.mqtt.client as mqtt
from aiohttp import web
from aiohttp import ClientSession
from av import VideoFrame

from aiortc import MediaStreamTrack, RTCPeerConnection, RTCSessionDescription, RTCRtpSender
from aiortc.contrib.media import MediaBlackhole, MediaPlayer, MediaRecorder, MediaRelay

ROOT = os.path.dirname(__file__)

#logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("pc")
pcs = set()

relay = MediaRelay()
broadcast = None

### Publisher
def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    client.subscribe("Number of connections")

def create_broadcast(track):
    global broadcast
    broadcast = track

def broadcast_ended():
    global broadcast
    broadcast = None

## Pyydetään toiselta palvelimelta WebRTC-streami, jos itsellä sitä ei ole
async def ask_stream(ask_stream, timeout):
    while True:
        await asyncio.sleep(3)
        if ask_stream == "False":
            return
        # Onko meillä streami
        if broadcast:
            return

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
            if track.kind == "audio":
                pc.addTrack(player.audio)
            elif track.kind == "video":
                create_broadcast(track)
                pc.addTrack(relay.subscribe(broadcast))
            @track.on("ended")
            async def on_ended():
                log_info("Track %s ended", track.kind)
                broadcast_ended()
                coros = [pc.close() for pc in pcs]
                await asyncio.gather(*coros)
                pcs.clear()
            @track.on("oninactive")
            async def on_inactive():
                log_info("Track inactive")


        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            log_info("Connection state is %s", pc.connectionState)
            if pc.connectionState == "failed":
                broadcast_ended()
                coros = [pc.close() for pc in pcs]
                await asyncio.gather(*coros)
                pcs.clear()
        print("onko jumiss")

        # POST-pyyntö dispatcherille
        session = ClientSession()
        res = await session.post('https://localhost:8080/offer', json=params,ssl=False,timeout=3)
        if res.status == "500":
            continue
        try:
            result = await res.json()
        except:
            continue
        await session.close()
        answer = RTCSessionDescription(sdp=result["sdp"], type=result["type"])
        #print(answer.sdp)
        await pc.setRemoteDescription(answer)
    
async def offer(request):
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    #logger.info(offer)

    pc = RTCPeerConnection()

    pc_id = "PeerConnection(%s)" % uuid.uuid4()
    pcs.add(pc)

    def log_info(msg, *args):
        logger.info(pc_id + " " + msg, *args)

    log_info("Created for %s", request.remote)

    @pc.on("datachannel")
    def on_datachannel(channel):
        @channel.on("message")
        def on_message(message):
            if isinstance(message, str) and message.startswith("ping"):
                channel.send("pong" + message[4:])

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        log_info("Connection state is %s", pc.connectionState)
        if pc.connectionState == "failed":
            await pc.close()
            pcs.discard(pc)

    # Otetaan video ja audio vastaan striimin välittävältä palvelimelta
    # Tässä toistetaan video / audio -tiedosto, mitä tarkoittaa jatkuvan
    # streamin tapauksessa?

    @pc.on("track")
    def on_track(track):
        log_info("Track %s received", track.kind)
        if track.kind == "audio":
            pc.addTrack(player.audio)
            recorder.addTrack(track)
        elif track.kind == "video":
            create_broadcast(track)
            pc.addTrack(track)

            #pc.addTrack(track)#relay.subscribe(broadcast))

        @track.on("ended")
        async def on_ended():
            log_info("Track %s ended", track.kind)
            #await pc.close()
            #pcs.discard(pc)
            broadcast_ended()

            coros = [pc.close() for pc in pcs]
            await asyncio.gather(*coros)
            pcs.clear()


    # handle offer
    await pc.setRemoteDescription(offer)

    # Tämä ajetaan kun clientistä on "Listen for..." valittuna
    # addTrack menee clienttiin ja siihen laitetaan relay broadcastista
    if params["listen_video"]:
        log_info("Kuuntelu")
        for t in pc.getTransceivers():
            log_info("Kuuntelu %s", t.kind)
            # Tarkasta onko "broadcast" olemassa
            if t.kind == "video" and broadcast:
                pc.addTrack(relay.subscribe(broadcast))
                capabilities = RTCRtpSender.getCapabilities('video')
                preferences = list(filter(lambda x: x.name == 'H264', capabilities.codecs))
                print(preferences)
                transc = pc.getTransceivers()[0]
                transc.setCodecPreferences(preferences)


    # send answer
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    print(json.dumps(
            {"type": pc.localDescription.type}
        ))
    return web.Response(
        content_type="application/json",
        text=json.dumps(
            {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
        ),
    )

async def on_shutdown(app):
    # close peer connections
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()

async def report_connections(interval, host, port):
    while True:
        await asyncio.sleep(interval)
        if broadcast:
            payload_dict = {
                "num_of_connections": len(pcs),
                "host": f"{host}:{port}"
            }
            client.publish('Number of connections',
                payload=json.dumps(payload_dict), qos=0, retain=False
            )
            print(f"send value of {payload_dict['num_of_connections']}"
                +f" connections from host {payload_dict['host']}"
                +" to broker")


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

    app = web.Application()
    app.on_shutdown.append(on_shutdown)
    app.router.add_post("/offer", offer)
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

    tasks = asyncio.gather(
        web_runner(),
        report_connections(5, args.host, args.port),
        ask_stream(args.ask_stream, timeout=5)
    )

    loop.run_until_complete(tasks)
    try:
        loop.run_forever()
    except KeyboardInterrupt as e:
        loop.close()
