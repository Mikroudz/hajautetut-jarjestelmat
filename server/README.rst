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

Käynnistä dispatcheri. Huom tarvitset cert-filun ja avaimen jotta selain pystyy käyttämään web-kameraa:

.. code-block:: console

    $ python3 dispatcher.py --cert-file ~/cert.pem --key-file ~/key.pem 

Käynnistä videopalvelin. Näitä voi käynnistää useita käyttämällä eri portteja:

.. code-block:: console

    $ python server.py --port 8081

You can then browse to the following page with your browser:

https://127.0.0.1:8080

Valitse "Broadcast webcam to network" ja sitten paina "start".

Käynnistä toinen videopalvelin, joka hakee videokuvan ensimmäiseltä palvelimelta:

.. code-block:: console

    $ python server.py --port 8082 --ask-stream 1

Avaa toinen selainikkuna ja valitse "Listen for the broadcast from network" ja paina "Start".
Nyt selaimen asiakasohjelma hakee videokuvan palvelimelta, jolla on vähiten kuormitusta.
Vähiten kuormitettu palvelin näkyy dispatcher-komentoruudussa.



Additional options
------------------

If you want to enable verbose logging, run:

.. code-block:: console

    $ python server.py -v

Testiclientin käyttäminen. "Clients" on luotavien asiakasohjelmien määrä ja "client_interval" kuinka usein uusi ohjelma luodaan.

.. code-block:: console
    $ python3 testclient.py --clients 10 --client_interval 4

Credits
-------

The audio file "demo-instruct.wav" was borrowed from the Asterisk
project. It is licensed as Creative Commons Attribution-Share Alike 3.0:

https://wiki.asterisk.org/wiki/display/AST/Voice+Prompts+and+Music+on+Hold+License
