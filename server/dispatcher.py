import argparse
import asyncio
import json
import logging
import os
import ssl
import uuid

from aiohttp import web
from aiohttp import ClientSession
<<<<<<< Updated upstream
from av import VideoFrame

from aiortc import MediaStreamTrack, RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaBlackhole, MediaPlayer, MediaRecorder
=======
from collections import namedtuple
>>>>>>> Stashed changes

ROOT = os.path.dirname(__file__)

logger = logging.getLogger("pc")
pcs = set()


class ServerList(object):
    def __init__(self):
        self.candidates = []
        #server: address, load, seen
    class Server:
        def __init__(self, address, load):
            self.addr = address
            self.load = load
            self.seen = 0
        
    def add_new(self, addr, load):
        self.candidates.append(self.Server(addr,load))

    def update(self, data):
        pass
    def remove(self, address):
        pass
    def remove_old(self):
        pass
    def get_least_loaded(self):
        pass        

servers = ServerList()

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
        res = await session.post('http://localhost:8081/offer', json=params)
    #Lue vastaus videopalvelimelta
    sdp_data = await res.json()
    # Palauta clientin responseen videopalvelimen sdp-data json-muodossa
    return web.Response(
        content_type="application/json",
        text=json.dumps(sdp_data),)

<<<<<<< Updated upstream
async def on_shutdown(app):
    # close peer connections
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()

=======
async def timer():
    while True:
        await asyncio.sleep(10)
        for s in servers.candidates:
            print(s)
    
>>>>>>> Stashed changes

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
<<<<<<< Updated upstream
=======

    servers.add_new("asd", 10)

    loop.run_until_complete(tasks)
    try:
        loop.run_forever()
    except KeyboardInterrupt as e:
        loop.close()

    #web.run_app(
    #    app, access_log=None, host=args.host, port=args.port, ssl_context=ssl_context
    #)
>>>>>>> Stashed changes
