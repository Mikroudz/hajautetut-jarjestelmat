import argparse
import asyncio
import json
import logging
import os
import ssl
import uuid
import paho.mqtt.client as mqtt
import csv

from aiohttp import web
from aiohttp import ClientSession
from time import gmtime, strftime, time

ROOT = os.path.dirname(__file__)

logger = logging.getLogger("pc")
class ServerList(object):
    def __init__(self, timeout):
        # Lista serveriobjekteista
        self.candidates = []
        self.timeout = timeout
    # Luokka joka kuvaa yhtä serveriä
    class Server:
        def __init__(self, address, load):
            self.addr = address
            self.load = load
            self.seen = time()
        # Päivitä ikä
        def update_time(self):
            self.seen = time()
        # Laske ikä ja palauta
        def age(self):
            return time() - self.seen
    def add_new(self, addr, load):
        self.candidates.append(self.Server(addr,load))
    # Päivitä tai lisää objektilistaan
    def update(self, address, load):
        for obj in self.candidates:
            if obj.addr == address:
                obj.load = load
                obj.update_time()
                return
        self.add_new(address, load)
    # Poista vanha palvelin käytöstä jos seen > timeout
    def remove(self):
        pass
    #Tähän tulee nyt se algoritmi palvelimen valintaan
    def get_least_loaded_address(self):
        min_addr = None
        for obj in self.candidates:
            if obj.age() < self.timeout:
                if min_addr == None:
                    min_addr = obj
                elif obj.load < min_addr.load:
                    min_addr = obj
            else:
                # Poista vanha listasta
                self.candidates.remove(obj)
        return min_addr

servers = ServerList(timeout=10)

### Subscriber
# The callback function of connection
def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    client.subscribe("Number of connections")
    
# The callback function for received message
def on_message(client, userdata, msg):
    host = json.loads(msg.payload)["host"]
    cons = json.loads(msg.payload)["num_of_connections"] 
    servers.update(host, cons)
    #print(f"Added host {host} with {cons} connections")

async def index(request):
    content = open(os.path.join(ROOT, "index.html"), "r").read()
    return web.Response(content_type="text/html", text=content)

async def javascript(request):
    content = open(os.path.join(ROOT, "client.js"), "r").read()
    return web.Response(content_type="application/javascript", text=content)

## Tähän tulee client-verkkosivulta WebRTC-pyynnöt
async def offer(request):
    global servers
    # Hae post-requestin parametrin. ELi tässä on se sdp-data clientiltä json-muodossa
    params = await request.json()
    #logger.info(params)
    # Välitä json data eteenpäin 8081-portissa toimivalle videopalvelimelle
    #async with ClientSession() as session:
    session = ClientSession()
    if params["listen_video"]:
        server = servers.get_least_loaded_address()
        if isinstance(server, ServerList.Server):
            print(f"Valittiin {server.addr} Kuorma: {server.load}")
            #raise web.HTTPFound(f'http://{server.addr}/offer')
            res = await session.post(f'http://{server.addr}/offer', json=params)
        else:
            return web.Response(status=500)
            #res = await session.post('http://localhost:8081/offer', json=params)
    else:
        res = await session.post('http://localhost:8081/offer', json=params)
    #Lue vastaus videopalvelimelta
    #print(res)
    sdp_data = await res.json()
    await session.close()
   # print(sdp_data)
    # Palauta clientin responseen videopalvelimen sdp-data json-muodossa
    return web.Response(
        content_type="application/json",
        text=json.dumps(sdp_data),)

async def timer(interval, csv_file):
    prog_time = 0
    while True:
        #servers.update("asd1", 20)
        await asyncio.sleep(interval)
        print("Palavelimet listassa:")
        for s in servers.candidates:
            print("%s %s %s" % (s.addr, s.load, s.age()))
            with open(f"logs/{csv_file}.csv", 'a', newline='') as f:
                csv_writer = csv.writer(f)
                csv_writer.writerow([prog_time,s.addr, s.load, s.age()])
        prog_time += interval
    
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

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect("localhost", 1883, 60)
    client.loop_start()

    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_get("/client.js", javascript)
    app.router.add_post("/offer", offer)

    file_csv = strftime('%Y-%m-%d_%H-%M-%S', gmtime())
    
    with open(f"logs/{file_csv}.csv", 'w', newline='') as f:
        with f:
            csv_writer = csv.writer(f)
            csv_writer.writerow(["Time","Address", "Load", "Age"])

    async def web_runner():
        runner = web.AppRunner(app, access_log=None)
        await runner.setup()
        site = web.TCPSite(runner, port=args.port, host=args.host, ssl_context=ssl_context)
        await site.start()
        print("Web server started in %s port %s " % (args.host, args.port))

    tasks = asyncio.gather(
        web_runner(),
        timer(interval=5, csv_file=file_csv)
    )

    loop.run_until_complete(tasks)
    try:
        loop.run_forever()
    except KeyboardInterrupt as e:
        loop.close()
