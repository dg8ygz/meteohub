# Tests

Vom Repository-Hauptverzeichnis aus, ohne Zugriff auf eine echte Station:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s dashboard -p 'test_weather*.py'
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s . -p 'test_normalize_native.py'
PYTHONDONTWRITEBYTECODE=1 python3 test-feed-process.py
node --check dashboard/weather.js
sh -n cgi_compat.sh
sh -n rcloggerd
sh -n read-source-socket.sh
```

Stand 05.11.2026: 13 Dashboard-/Parser-/API-Tests, vier Normalisierungstests
und der reale Plugin-Prozesstest bestanden. Zusätzlich wurden im Testgast echte
HTTP-/Browserabrufe, SVG-Einbettung, Authentifizierungsgrenzen, Loggersteuerung,
historische PNG-Erzeugung und Neustart des äußeren Hosts geprüft. Die privaten
Betriebsbelege werden nicht in ein öffentliches Repository exportiert.
