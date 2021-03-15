Audio, video and data channel server
====================================

Hajautettujen työ

Running
-------

HUOM.
Tarvitset python 3.7 tai uudemman

Asenna paketit:

.. code-block:: console

    $ pip install aiohttp aiortc paho-mqtt

Käynnistä dispatcheri. Huom tarvitset cert-filun ja avaimen:

.. code-block:: console

    $ python3 dispatcher.py --cert-file ~/cert.pem --key-file ~/key.pem 

Käynnistä videopalvelin:

.. code-block:: console

    $ python server.py --port 8081

Käynnistä toinen videopalvelin:

.. code-block:: console

    $ python server.py --port 8082

You can then browse to the following page with your browser:

http://127.0.0.1:8080

Valitse "Broadcast webcam to network" ja sitten paina "start". Avaa toinen
selainikkuna ja valitse "Listen for the broadcast from network" ja paina "Start".

The server will play a pre-recorded audio clip and send the received video back
to the browser, optionally applying a transform to it.

In parallel to media streams, the browser sends a 'ping' message over the data
channel, and the server replies with 'pong'.

Additional options
------------------

If you want to enable verbose logging, run:

.. code-block:: console

    $ python server.py -v

Credits
-------

The audio file "demo-instruct.wav" was borrowed from the Asterisk
project. It is licensed as Creative Commons Attribution-Share Alike 3.0:

https://wiki.asterisk.org/wiki/display/AST/Voice+Prompts+and+Music+on+Hold+License
