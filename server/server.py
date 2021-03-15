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
from aiortc.contrib.media import MediaBlackhole, MediaPlayer, MediaRecorder, MediaRelay

ROOT = os.path.dirname(__file__)

#logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("pc")
pcs = set()

relay = MediaRelay()
broadcast = None

def create_broadcast(track):
    global relay, broadcast
    broadcast = track

async def offer(request):
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    logger.info(offer)

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

    @pc.on("track")
    def on_track(track):
        log_info("Track %s received", track.kind)
        if track.kind == "audio":
            pc.addTrack(player.audio)
            recorder.addTrack(track)
        elif track.kind == "video":
            create_broadcast(track)
            pc.addTrack(relay.subscribe(broadcast))

        @track.on("ended")
        async def on_ended():
            log_info("Track %s ended", track.kind)
            #await recorder.stop()

    # handle offer
    await pc.setRemoteDescription(offer)

    # Tämä ajetaan kun clientistä on "Listen for..." valittuna
    # addTrack menee clienttiin ja siihen laitetaan relay broadcastista
    if params["listen_video"]:
        log_info("Kuuntelu")
        for t in pc.getTransceivers():
            # Tarkasta onko "broadcast" olemassa
            if t.kind == "video" and broadcast:
                pc.addTrack(relay.subscribe(broadcast))

    #await recorder.start()

    # send answer
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

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

async def timer(interval):
    while True:
        await asyncio.sleep(interval)
        print("tulosta")

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

    async def web_runner():
        runner = web.AppRunner(app, access_log=None)
        await runner.setup()
        site = web.TCPSite(runner, port=args.port, host=args.host, ssl_context=ssl_context)
        await site.start()
        print("Web server started in %s port %s " % (args.host, args.port))

    tasks = asyncio.gather(
        web_runner(),
        timer(5)
    )

    loop.run_until_complete(tasks)
    try:
        loop.run_forever()
    except KeyboardInterrupt as e:
        loop.close()
