# RAM-Datenhaltung und SD-Sicherungen

Stand 9. November 2026: **lokal implementiert und mit echten Test-Mounts und
systemd getestet; auf dem Stations-Pi noch nicht installiert oder abgenommen.**
Dieses Werkzeug schaltet weder Root noch Boot auf RO. Diese zweite Stufe folgt
erst nach nachgewiesener RAM-Aufzeichnung, Sicherung und Wiederherstellung auf
dem Ziel-Pi. `overlayroot` wird hier nicht installiert.

## Aufbau

`tools/ram-storage.py` legt einen Overlay-Mount ueber die bestehende private
Meteohub-Runtime. Die untere Schicht ist eine unveraenderliche, gepruefte
Generation auf einer getrennten ext4-Datenpartition; die obere Schicht liegt
in einem begrenzten tmpfs. Der Standarddeckel ist 320 MiB. Er ist eine Grenze,
keine Vorabreservierung. Historische Dateien bleiben auf SD und werden nicht
vollstaendig in RAM kopiert. Aenderungen an einer bestehenden Datei koennen
deren vollstaendige Kopie in die obere Schicht ausloesen; insbesondere die
SQLite-Groesse und die bestehenden Dienst-Speicherlimits weiter beobachten.

Die bisherigen RootDirectory-Pfade und gehashten Hauptunits bleiben erhalten.
Zusaetzliche Drop-ins erzwingen die Wiederherstellung vor Logger, Websocket,
Web und Indexer. Der Indexer wartet ebenfalls auf initial synchronisierte
Zeit, damit sein 35-Tage-Fenster und seine Dateipositionen nicht mit alter
Bootzeit verarbeitet werden. Das native TCP-Verfahren bleibt unveraendert.

## Voraussetzungen

- Getrennte ext4-Partition ist anhand ihrer UUID geprueft, nur lesend gemountet
  und fuer Boot eingetragen. Kein Overlay ueber dieser Sicherungspartition.
- Dauerbetrieb mit vier aktiven Anwendungsunits; nachgewiesene echte Messwerte.
- Gepruefte initiale Runtime-Sicherung und vorhandener konkreter Rettungsweg.
- Zeit-Startsperre aktiv; reines ZRAM ohne SD-Backing und ohne anderen Swap.
- Genug freier RAM: angeforderter tmpfs-Deckel plus mindestens 128 MiB
  Momentanreserve. Das ersetzt keine Langzeitmessung des Datenwachstums.
- Noch keine verschachtelten Mounts innerhalb der bisherigen Runtime.
- Operator fuehrt Zielbefehle selbst aus. Bei lokal-only Entwicklung sind die
  Dateien zu uebertragen; ein `git pull` liefert unveroeffentlichte Commits nicht.

## Installation und Abnahme

Die drei Pfade/Kennungen sind lokale Installationsparameter, keine allgemeinen
Stationsvorgaben. Aufruf als root, nach Uebertragung der geprueften Skriptdatei:

```bash
python3 ram-storage.py install \
  --runtime /ABSOLUTER/PFAD/ZUR/RUNTIME \
  --persist /ABSOLUTER/PFAD/ZUM/DATENMOUNT \
  --uuid DATEISYSTEM-UUID \
  --ram-mib 320
```

Der Aufruf pausiert die vier Anwendungsdienste fuer die Ausgangsgeneration,
prueft Kopie und Datenbank, installiert den Helper unter
`/usr/local/libexec/meteohub-ram.py`, die Konfiguration unter
`/etc/meteohub-ram.json` und neue systemd-Units/Drop-ins. Originale Runtime-Daten
unter dem Mount bleiben erhalten. Die Dienste werden auf der RAM-Runtime
wieder gestartet. Die Installationshuelle selbst ist noch am Ziel abzunehmen;
ein erfolgreicher lokaler Backend-Test ist keine Pi-Abnahme.

Danach auf dem Zielsystem pruefen:

```bash
python3 /usr/local/libexec/meteohub-ram.py status
systemctl list-timers --all --no-pager 'meteohub-ram-*'
```

Neue native Messwerte und Indexgleichstand im RAM nachweisen. Danach bewusst
einen manuellen Sicherungslauf ausloesen und erneut Datenfluss/Mounts pruefen:

```bash
python3 /usr/local/libexec/meteohub-ram.py checkpoint
python3 /usr/local/libexec/meteohub-ram.py status
```

Vor einem Reboot Diagnose auf dauerhaftem Speicher sichern. Nach Neustart:
neue Anmeldung, initiale Zeitsynchronisation, wiederhergestellte Daten,
RAM-Overlay, RO-Datenpartition, Timer und neue Messwerte nachweisen.
Host-Root-RO erst danach vorbereiten. Keine alte Root-Unterlage unter einem
laufenden Overlay beschreibbar machen oder zuruecksynchronisieren.

## Sicherungsverhalten

- Timer taeglich **04:15 Europe/Berlin**, Persistent=true fuer nachgeholte Laeufe.
- Beim regulaeren Stop/Herunterfahren: systemd stoppt zuerst die abhaengigen
  Anwendungen; anschliessend sichert ExecStop der RAM-Unit.
- Dienste pausieren waehrend einer taeglichen/manuellen Sicherung. Das ist eine
  kurze geplante Empfangs-/Webpause; keine Zusage lueckenloser Erfassung.
- Der Logger muss sauber beendet sein. Kein laufendes SQLite/WAL wird blind
  kopiert: gepruefte Kopie bei angehaltenen Diensten, Konsolidierung der
  kopierten Datenbank, integrity_check und Inhaltsmanifest mit SHA-256.
- Neue Generation erst nach vollstaendiger Pruefung und Synchronisierung
  veroeffentlichen. Die Datenpartition wird anschliessend wieder RO.
- Nach laufender Sicherung wird das Overlay auf die neue Generation umgestellt;
  erst danach wird die alte RAM-Schicht entfernt. Bei fehlgeschlagenem
  Umstellen wird die bisherige Schicht wieder gemountet.
- Zwei veroeffentlichte Generationen bleiben erhalten; zusaetzlich wird eine
  noch aktive untere Generation nie geloescht. Die vorherige Bootstrap-
  Sicherung unter `snapshots/initial-*` wird nicht angefasst. Teilstaende
  `.pending-*` bleiben bei Fehlern fuer Diagnose erhalten und koennen Platz
  verbrauchen; sie sind keine gueltigen Wiederherstellungspunkte.
- Bei Stromverlust ist nur der letzte abgeschlossene Stand verfuegbar.
  Normalerweise bis zu 24 Stunden Verlust, bei Sicherungsfehlern mehr.
- Kapazitaetspruefung alle fuenf Minuten: ab 80 Prozent RAM-Belegung oder
  Sicherungsalter ueber 26 Stunden fehlerhafter Checkdienst mit Journalbefund.
  Waehrend einer laufenden Speicheroperation wird dieser einzelne Check mit
  ausdruecklichem Skip-Befund ausgelassen; das ist keine Gesundheitsbestaetigung.
  Kein E-Mail-/Pushalarm und keine behauptete externe Ueberwachung.

Fehlender Mount, falsche UUID oder beschaedigte Generation verhindern den
Anwendungsstart. Das Werkzeug verwendet nicht still die veraltete Original-
Runtime unter dem RAM-Mount. Bei Fehlern Mountstatus und Units pruefen;
normale Fehler/Signale loesen Aufraeumversuche aus. Stromausfall/SIGKILL
koennen keine Aufraeumgarantie haben.

## Rueckbau vor Root-RO

### Korrektur der ersten RAM-Installerfassung

Die erste Fassung erzeugte die obere Runtime-Wurzel als root:root/0700.
Overlay uebernimmt diese Metadaten auch fuer den sichtbaren Mount; dadurch
scheitert der externe Beobachter als Benutzer meteohub mit PermissionError.
Die korrigierte Fassung uebernimmt vor jedem Mount die Metadaten der
Runtime-Wurzel aus der geprueften unteren Generation.

Bei bereits installiertem betroffenem Helper die korrigierte Datei separat
uebertragen und als root aufrufen:

```bash
python3 /PFAD/ZUR/KORRIGIERTEN/ram-storage.py repair-permissions
```

Der Aufruf prueft den bisherigen Helper gegen den gespeicherten Hash, sichert
Helper/Konfiguration und bisherige Wurzelrechte unter `/root`, aktualisiert
den installierten Helper samt Hash und korrigiert die sichtbare Runtime-Wurzel.
Keine Dienste werden neu gestartet. Anschliessend den Beobachter als regulaeren
Meteohub-Benutzer ausfuehren; neue Daten sind gesondert nachzuweisen.

### Vollstaendiger Rueckbau

```bash
python3 /usr/local/libexec/meteohub-ram.py remove
```

Der Rueckbau verlangt einen normalen beschreibbaren Host-Root ohne Overlay.
Er prueft die eigenen Konfigurationsdateien gegen die Installationshashes,
stoppt Timer und RAM-Betrieb mit letzter Sicherung, kopiert den neuesten
geprueften Stand in eine neue normale Runtime und bewahrt die alte Unterlage
als benachbartes Backup. Erst dann werden eigene Units/Drop-ins/Helper entfernt
und der bisherige Dauerbetrieb gestartet. Bei bereits aktiviertem Host-RO
zuerst in den normalen Wartungsboot zurueckkehren. `live-remove` darf nicht
unter einer aktiven RAM-Installation ausgefuehrt werden; der aktualisierte
Live-Helfer verweigert dies. Alte Helferversionen nicht dafuer verwenden.

## Lokale Tests und Grenzen

```bash
sudo PYTHONDONTWRITEBYTECODE=1 python3 tools/test-ram-storage.py --isolation
PYTHONDONTWRITEBYTECODE=1 python3 tools/test-live-service.py
```

Getrennte Test-Mountpoints und eindeutig benannte systemd-Testunits; keine
Stationsverbindung, kein ARM-Logger und keine Aenderung am Stations-Pi.
Getestet: ext4/tmpfs/Overlay, WAL-Konsolidierung, Sicherung/Rebase, Behalten
historischer Dateien auf SD, voller RAM-Puffer, injizierter SD-Schreibfehler,
falsche UUID, ungueltiges Sicherungsmanifest mit verweigertem Dienststart,
Shutdown-Reihenfolge, Verlust ungesicherter RAM-Daten, Wiederherstellung und
Rueckbau auf normalen Runtime-Pfad. Zusaetzlich wird die gesamte Installation
mit echten Units und Timern durchlaufen, einschliesslich eines injizierten
Startfehlers mit Ruecknahme und Wiederanlauf. Dabei sind nur die Pi-spezifische
Hardware-Vorpruefung und Stationsanwendungen durch Fixtures ersetzt.
Zusaetzlich prueft ein Prozess mit UID/GID 65534 den Lese- und Schreibzugriff
auf eine ihm gehoerende Runtime mit Modus 0750 nach Mount, Rebase und Restore.
Der alte root:root/0700-Fehler wird reproduziert und mit der Live-Reparatur
korrigiert. Das ersetzt weiterhin keine Pruefung des nativen Pi-Loggers.
Der erste Test fand eine nicht geschlossene
SQLite-Verbindung; explizites Schliessen ist implementiert und erneut getestet.
Pi-Kernel, native Anwendung, echter Reboot und Langzeitwachstum bleiben bis
zur separaten Zielabnahme OFFEN.
