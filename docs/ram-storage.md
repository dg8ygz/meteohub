# RAM-Datenhaltung und SD-Sicherungen

Stand 9. November 2026: **RAM-Betrieb, manuelle/Shutdown-Sicherung und
Wiederherstellung auf dem Stations-Pi nachgewiesen.** Auch der getrennte
Host-RO-Umbau und neue Archivdaten nach dessen Boot sind belegt; Details und
offene Punkte stehen im [Stationsnachweis](current-state.md). Die neue
Intervallumstellung ist lokal mit echten Mounts und systemd getestet. Auf dem
Stations-Pi sind die stuendliche Umstellung, ein automatisch ausgeloester
Nachhollauf und anschliessende dauerhafte Installation im Wartungsboot
nachgewiesen. Auch der folgende Host-RO-Boot mit dauerhaftem Stundenplan,
geladener Sicherung und aktiven Anwendungen ist bestaetigt. Das ist keine
pauschale Langzeitabnahme. Dieses Werkzeug schaltet weder Root noch Boot auf RO und installiert
kein `overlayroot`.

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
wieder gestartet. Ein erfolgreicher lokaler Backend-Test ersetzt die
jeweilige Zielabnahme nicht.

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

Fuer den echten Reboot-Nachweis auf noch normalem RW-ext4-Root kann
`tools/check-ram-reboot.py` separat uebertragen werden:

```bash
python3 check-ram-reboot.py prepare
# Nur bei erfolgreicher Vorbereitung regulaer rebooten, keinen Checkpoint dazwischenschalten.
systemctl reboot
# Nach neuer Anmeldung:
python3 /PFAD/ZU/check-ram-reboot.py check
```

Das Werkzeug rebootet nicht selbst. Es prueft neue Boot-ID/Generation,
ExecStop-Sicherungsbestaetigung, einen ausschliesslich im RAM angelegten
Kontrollmarker sowie den vorher vorhandenen Archiv-Praefix in Sicherung und
wiederhergestelltem RAM. Es erzeugt keine Wetterdaten. Vorherige Diagnose und
RAM-Service-Ausgaben bleiben unter `/root/meteohub-ram-reboot-check` dauerhaft
erhalten. Ein eigener temporaerer Logging-Drop-in wird nach erfolgreicher
Abnahme entfernt. Bei Fehler bleibt er fuer Diagnose bestehen. Vorhandene
Pruefverzeichnisse werden nicht ueberschrieben. Ein neuer Test braucht einen
bewusst separat vorbereiteten Nachweis; nicht blind vorhandene Belege loeschen.
Neue empfangene Messwerte sind anschliessend gesondert nachzuweisen.

## Sicherungsverhalten

- Standardtimer taeglich **04:15 Europe/Berlin**, Persistent=true fuer
  nachgeholte Laeufe. Kuerzere Intervalle sind explizit konfigurierbar, siehe unten.
- Beim regulaeren Stop/Herunterfahren: systemd stoppt zuerst die abhaengigen
  Anwendungen; anschliessend sichert ExecStop der RAM-Unit.
- Dienste pausieren waehrend einer geplanten/manuellen Sicherung. Das ist eine
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
  Beim taeglichen Standard normalerweise bis zu 24 Stunden Verlust, bei
  stuendlicher Sicherung etwa eine Stunde plus Laufzeit/Timerabweichung.
  Bei Sicherungsfehlern kann die Verlustspanne in beiden Faellen groesser sein.
- Kapazitaetspruefung alle fuenf Minuten: ab 80 Prozent RAM-Belegung oder
  Sicherungsalter ueber 26 Stunden beim taeglichen Standard fehlerhafter
  Checkdienst mit Journalbefund. Bei konfigurierten kuerzeren Intervallen gilt
  Intervall plus 30 Minuten (stuendlich also 90 Minuten).
  Waehrend einer laufenden Speicheroperation wird dieser einzelne Check mit
  ausdruecklichem Skip-Befund ausgelassen; das ist keine Gesundheitsbestaetigung.
  Kein E-Mail-/Pushalarm und keine behauptete externe Ueberwachung.

Fehlender Mount, falsche UUID oder beschaedigte Generation verhindern den
Anwendungsstart. Das Werkzeug verwendet nicht still die veraltete Original-
Runtime unter dem RAM-Mount. Bei Fehlern Mountstatus und Units pruefen;
normale Fehler/Signale loesen Aufraeumversuche aus. Stromausfall/SIGKILL
koennen keine Aufraeumgarantie haben.

## Sicherungsintervall aendern

Nach Uebertragung der aktuellen `ram-storage.py` als root:

```bash
python3 ram-storage.py configure-checkpoints --minutes 60 --temporary
systemctl list-timers --all --no-pager --full 'meteohub-ram-*'
python3 /usr/local/libexec/meteohub-ram.py status
```

`--temporary` erlaubt einen ausdruecklichen Versuch bei aktivem Host-Overlay.
Helper, Konfiguration und gehashte Timerunit werden in der beschreibbaren
Host-Schicht geaendert. Bei einem Host-Overlay verschwinden diese Aenderungen
beim Neustart; sie sind nicht Teil der Meteohub-Runtime-Sicherung. Es wird
nichts in die schreibgeschuetzte Root-Unterlage geschrieben. Die Sicherungen
selbst landen wie bisher geprueft auf der Persistenzpartition.

Fuer die dauerhafte Umstellung in einem Wartungsboot mit normalem RW-Root
denselben Befehl **ohne `--temporary`** ausfuehren. Das Skript muss in diesem
Boot erneut verfuegbar sein; eine Kopie allein im vorherigen Host-Overlay
ueberlebt den Neustart nicht. Es fuehrt weder Bootparameterwechsel noch Reboot
aus. Permanente Umstellung bei aktivem Host-Overlay wird abgewiesen.

Erlaubt sind 15, 30 oder 60 Minuten. Die Kalendereintraege liegen auf festen
UTC-Viertel-/Halb-/Vollstunden, ohne zusaetzlichen taeglichen Lauf. Stuendlich
ist die Empfehlung fuer den aktuellen Stationsversuch: Jeder Checkpoint
pausiert Anwendungen und kann anschliessendes Nacharbeiten des Index ausloesen.
Haeufiger ist daher nicht ohne Abwaegung besser. Ein nachzuholender Termin kann
bereits beim erneuten Aktivieren des Timers einen Checkpoint starten.

Die Umstellung prueft die verwalteten Dateien anhand ihrer gespeicherten
Hashes und lehnt unbekannte Timer-Drop-ins ab. Sie aktualisiert Helper und
Alterspruefung gemeinsam mit dem Timer. Ein zuvor inaktiver Timer bleibt
inaktiv; sein Aktivierungszustand wird nicht still geaendert. Ein Schreibfehler
beim Austausch stellt die alten Dateien wieder her. Die Funktion stoppt
Anwendungen nicht selbst; ein vom Timer ausgeloester Checkpoint tut dies wie
bisher. Sicherungsalter und App-Zustaende erscheinen im lokalen Status und
Journal; es existiert weiterhin keine externe Benachrichtigung.

Den automatischen Lauf am Ziel durch Timer-/Dienstjournal, erfolgreiche
Beendigung, neue gespeicherte Generation und RO-Persistenz nachweisen.
Ein manueller `systemctl start ...checkpoint.service` allein ist kein Nachweis
fuer die Timer-Ausloesung. Danach neue native Messwerte und Indexgleichstand
pruefen; der Regenkanal kann ein laengeres stationsspezifisches Intervall haben.

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

### Korrektur der Boot-Abhaengigkeiten

Die erste Fassung ordnete den RAM-Service vor dem Websocket ein, erhielt aber
als normaler Service implizit After=basic.target. Sockets starten wiederum
vor sockets.target/basic.target. Beim echten Pi-Boot loeschte systemd deshalb
den Websocket-Startauftrag. Start-/Stoptests auf einem bereits gestarteten Host
hatten diesen Kreis nicht gezeigt. Die korrigierte RAM-Unit verwendet
DefaultDependencies=no, Requires/After=sysinit.target und explizit
Conflicts/Before=shutdown.target. Die Mount-Abhaengigkeit bleibt erhalten.

Nach Uebertragung der korrigierten Datei als root:

```bash
python3 /PFAD/ZUR/KORRIGIERTEN/ram-storage.py repair-ordering
```

Prueft verwaltete Dateien gegen ihre Hashes, sichert Helper/Unit/Konfiguration
unter /root, aktualisiert den Helper und die RAM-Unit samt Hashes und fuehrt
daemon-reload aus. Keine Dienste werden neu gestartet. Health-Checks melden
nun auch inaktive Anwendungen als Handlungsbedarf. Anschliessend einen
kontrollierten Stop von Target UND RAM-Service mit neuer Sicherung und
Wiederanlauf pruefen; danach erneut echten Shutdown/Reboot abnehmen.
Der erste Pi-Reboot stellte nur den letzten manuellen Checkpoint wieder her;
die genaue Ursache der fehlenden Shutdown-Sicherung ist ohne vorheriges
persistentes Journal nicht nachgewiesen. Nicht mit dem Bootfix als erledigt
deklarieren.

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
Der Reboot-Nachweishelfer wird ebenfalls mit echten Sicherungs-/Restore-Mounts,
Logging-Drop-in und Archiv-/Markervergleich getestet; nur die Boot-ID wird in
diesem lokalen Test simuliert. Eine unveraenderte Boot-ID wird abgewiesen.
Der erste Test fand eine nicht geschlossene
SQLite-Verbindung; explizites Schliessen ist implementiert und erneut getestet.
Pi-Kernel, native Anwendung, echter Reboot und Langzeitwachstum bleiben bis
zur separaten Zielabnahme OFFEN.
