import argparse
import asyncio
import json
import logging
import os
import ssl
import uuid

from aiohttp import web
from aiohttp import ClientSession
from time import time

ROOT = os.path.dirname(__file__)

logger = logging.getLogger("pc")
pcs = set()


class ServerList(object):
    def __init__(self, timeout):
        self.candidates = []
        self.timeout = timeout
    class Server:
        def __init__(self, address, load):
            self.addr = address
            self.load = load
            self.seen = time()
        def update_time(self):
            self.seen = time()
        def age(self):
            return time() - self.seen
        
    def add_new(self, addr, load):
        self.candidates.append(self.Server(addr,load))

    def update(self, address, load):
        for obj in self.candidates:
            if obj.addr == address:
                obj.load = load
                obj.update_time()
                return
        self.add_new(address, load)

    def remove_old(self):
        pass
    def get_least_loaded_address(self):
        min_addr = None
        for obj in self.candidates:
            if obj.age() < self.timeout:
                min_addr = obj.addr
        return min_addr
        

servers = ServerList(10)

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

async def timer():
    val = 5
    while True:
        servers.update("asda", val)
        await asyncio.sleep(1)
        for s in servers.candidates:
            #print("asd")
            print("%s %s %s" % (s.addr, s.load, s.seen))

        print(servers.get_least_loaded_address())
    

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

    loop = asyncio.get_event_loop()

    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_get("/client.js", javascript)
    app.router.add_post("/offer", offer)

    async def web_runner():
        runner = web.AppRunner(app, access_log=None)
        await runner.setup()
        site = web.TCPSite(runner, port=args.port, host=args.host, ssl_context=ssl_context)
        await site.start()
        print("Web server started in %s port %s " % (args.host, args.port))

    tasks = asyncio.gather(
        web_runner(),
        timer()
    )

    servers.add_new("asd", 10)
    servers.update("asda", 11)
    servers.update("asdb", 12)
    servers.update("asdc", 15)


    loop.run_until_complete(tasks)
    try:
        loop.run_forever()
    except KeyboardInterrupt as e:
        loop.close()

    #web.run_app(
    #    app, access_log=None, host=args.host, port=args.port, ssl_context=ssl_context
    #)
