# Geführter Installer und separates Dashboard-Update

Stand: 7. November 2026. Der Installer fasst die bisher einzeln ausgeführten,
geprüften Vorbereitungsschritte zusammen. Er richtet die **5.1e-Testoberfläche**
und optional die **Dashboard-/SVG-Erweiterung** ein. Er ist noch kein fertiger
Produktionsinstaller für die gesamte Wetterstation: nativer Logger,
Archiv-/Aggregat-/Exportabnahme, dauerhafter Datenzubringer und Autostart bleiben
separate Schritte. Er akzeptiert keine Lizenzbedingungen und wählt keine Station
stellvertretend für den Anwender.

**Aktueller Umzugsweg:** [Direkter nativer Meteohub-TCP-Empfang](#direkter-nativer-meteohub-tcp-empfang).
Der ältere JSON-/Plugin-Spiegelpfad unten bleibt als Diagnosehistorie erhalten.
Er ist für die Übernahme vom vorhandenen Meteohub nicht erforderlich;
`plugin-update` dafür nicht ausführen.

## Ausgangspunkt

Raspberry Pi 3 Model B/B+ oder Pi 4 Model B mit Raspberry Pi OS Lite **Trixie,
64 Bit**, abgeschlossener Paketaktualisierung und funktionierendem SSH-Zugang.
Ein normaler Benutzer mit `sudo` ist erforderlich. Mindestens 5 GiB freien Platz
für die erste Vorbereitung vorsehen. Auf dem bisherigen Stations-Pi wird nichts
installiert. Der neue Pi darf nicht gleichzeitig dessen serielle Konsole lesen.

Auf dem **neuen Pi**, als normaler Benutzer:

```bash
sudo apt-get install --no-install-recommends git python3 ca-certificates
mkdir -p "$HOME/src"
cd "$HOME/src"
git clone https://github.com/dg8ygz/meteohub.git
cd meteohub
python3 install-pi.py install
```

Bei bereits vorhandenem Checkout **nicht nochmals klonen**:

```bash
cd "$HOME/src/meteohub"
git pull --ff-only
python3 install-pi.py install
```

Der Installer verwendet dieselben Verzeichnisse wie die bisherige Anleitung:
`~/meteohub-original`, `~/meteohub-staging/5.0s-openssl3`,
`~/meteohub-staging/5.1e-openssl3` und `~/meteohub-staging/5.1e-runtime`.
Geprüfte vorhandene Downloads, Kandidaten und Laufzeitumgebung werden
weiterverwendet. Konfiguration, Webpasswort und Messdaten werden nicht zurückgesetzt.
Bei abweichenden Dateien oder fremden Mounts stoppt das Programm mit einer
Fehlermeldung, statt etwas zu überschreiben.

Der Ablauf:

1. Trixie/ARM64/Pi-Modell und sauberen Paketstatus prüfen; armhf ergänzen und
   fehlende Abhängigkeiten installieren. APT zeigt den Plan; mit `J` bestätigen.
   Keine Paketentfernung. Bereits aktive Standard-lighttpd-Dienste werden nicht
   übernommen. Die drei Standard-lighttpd-Units bleiben maskiert, damit kein
   zusätzlicher ungeschützter Webserver startet.
2. Hersteller-RAR 5.0s und Update 5.1e herunterladen und gegen fest hinterlegte
   SHA-256-Werte prüfen. Keine proprietären Programme kommen aus diesem Git-Repo.
3. Das Image entpacken und dessen zweite Partition **nur lesbar** einhängen.
   Größe, Partitionstabelle, Loop-Zuordnung und Mount-Optionen werden geprüft.
   Hersteller-Update-/Bootskripte werden nicht ausgeführt.
4. Die fünf Kernprogramme samt geprüfter CGI-Bibliothek vorbereiten und ihre
   Bibliotheksauflösung prüfen. Bei der OpenSSL-Anpassung bleiben ausführbare
   Programmabschnitte unverändert. Das allein beweist noch keine vollständige
   Funktionskompatibilität.
5. Private Laufzeitumgebung und Passwortschutz anlegen, dann die isolierte
   Testoberfläche auf **127.0.0.1:18090** starten. Ein bereits passender Dienst
   wird weiterverwendet; eine andere laufende Testumgebung wird nicht ersetzt.

Beim ersten Web-Setup zweimal ein neues **Webpasswort** eingeben. Es wird nicht
in Befehlszeile, Git oder Diagnoseausgaben geschrieben. Der Webbenutzer heißt
`meteohub`; das ist unabhängig vom SSH-Anmeldenamen und SSH-Passwort.

## Oberfläche öffnen und Station auswählen

Auf dem eigenen Rechner einen SSH-Tunnel öffnen; `BENUTZER` und `PI_IP` ersetzen:

```bash
ssh -N -L 18090:127.0.0.1:18090 BENUTZER@PI_IP
```

Im Browser: <http://127.0.0.1:18090/cgi-bin/meteohub.cgi>.
Nach der Anmeldung die Lizenzbedingungen selbst lesen/akzeptieren und unter
System Information **5.1e (Build 277)** kontrollieren. Leere System-ID mit dem
Wort „activated“ ist kein Aktivierungsnachweis. Lizenzübertragung und eine
vollständige Betriebsabnahme sind davon getrennt.

Für den bereits vorhandenen TCP-Messwertkopie-Dienst auf der alten Station:

- Unter Weather Stations Station 0 als **User-defined / Plug-in** anlegen.
- Plug-in path: **`/home/meteohub/plugin.sh`**.
- Name und Höhe entsprechend dem eigenen Standort setzen.
- Die Warnung zu noch nicht zugewiesenen Sensoren zunächst stehen lassen.

Die isolierte Oberfläche hat absichtlich keinen Zugriff auf USB oder das echte
Hostnetz. Ihre Angaben „kein Gateway“, „IP inactive“, fehlende alte PID-Dateien
oder eine falsche Modellbezeichnung beschreiben nicht den Netzwerk-/SSH-Zustand
des neuen Pi. Nicht versuchen, mit dieser alten Oberfläche dessen Hostnetz zu ändern.

## Befristeten Messwerttest ausführen

Der Quellhost muss ausdrücklich angegeben werden. `STATIONS_IP` durch die Adresse
des bestehenden **TCP-Kopiedienstes** ersetzen, nicht durch einen seriellen Port:

```bash
python3 install-pi.py feed-test --source-host STATIONS_IP --source-port 5500
```

Der Schritt erzeugt `logger.conf` mit dem nativen CGI-Parameter `-1`, prüft Station
0 und bereitet den Plugin-Wrapper vor. Bereits passende Plugin-Dateien bleiben
erhalten. Danach liest der Collector standardmäßig **120 Sekunden** TCP-Daten,
ohne Kommandos an die Station zu senden. Anschließend läuft das echte Plugin
für 15 Sekunden in der isolierten Umgebung. Private Berichte dokumentieren die
Ausgabe. Vollständige ursprüngliche THB-Datensätze mit gültigem Stationsdruck
werden an die Pipe ausgegeben; Dashboard/SVG wählen daraus nur Druck aus.
Bestehende Installationen zuerst mit `plugin-update` aktualisieren.

Collector und Plugin enden danach wieder. **Der native Logger startet nicht.**
Ein erfolgreicher Test ist kein dauerhafter Empfang und keine Archivabnahme.
Bei seltenen Sensoren kann `--duration 300` helfen; erlaubt sind 30–600 Sekunden.

## Dashboard und SVG als Extension installieren/aktualisieren

Nach vorbereiteter Laufzeitumgebung und Webzugang:

```bash
cd "$HOME/src/meteohub"
git pull --ff-only
python3 install-pi.py extension-update
```

Das ist ein eigener Update-Schritt. Er verändert keine Herstellerprogramme,
Stationseinstellungen oder Zugangsdaten und startet den Webserver nicht neu.
Er legt eine anhand ihres Inhalts identifizierte Ausgabe unter
`root/opt/meteohub-dashboard/releases/` ab und schaltet `current` atomar um.
Alte Ausgaben bleiben für den Rückweg erhalten; bearbeitete installierte
Dateien und fremde URL-Ziele werden nicht überschrieben.

Über den bestehenden SSH-Tunnel:

- **Dashboard:** <http://127.0.0.1:18090/dashboard/>
- **SVG, 600 × 180 Pixel:** <http://127.0.0.1:18090/cgi-bin/weather-image.cgi>
- JSON für das Dashboard: `/cgi-bin/weather-api.cgi`.

Alle drei Wege verwenden dieselbe Webanmeldung. Die SVG benötigt weder Flash
noch JavaScript. Einbettung auf einer Seite **derselben Herkunft**:

```html
<img src="/cgi-bin/weather-image.cgi"
     width="600" height="180" alt="Aktuelles Wetter und Windvektor">
```

Auch ein normaler Link auf die SVG funktioniert. Ein `<img>` aktualisiert sich
nicht automatisch; für neue Werte die einbettende Seite neu laden. Der
SSH-/Passwortschutz wird durch Einbettung nicht umgangen. Für eine öffentliche
Webseite ist später ein ausdrücklich eingerichteter Veröffentlichungsweg nötig;
keine Passwörter in URLs schreiben.

Der eigene Dienst `meteohub-dashboard-index.service` erstellt alle zehn Sekunden
einen **abgeleiteten** SQLite-Index aus `/data/weather` und dem
TCP-Plugin-Herkunftsprotokoll. Er hat keine Netzwerk-/USB-Rechte und darf nur
`/data/dashboard` beschreiben. Rohdaten bleiben unverändert. Der Index liegt
außerhalb der versionierten Anzeige-Dateien und bleibt bei Updates erhalten.

Fehlende oder alte Messungen werden nicht künstlich aktualisiert. Wenn nur der
befristete Messwerttest lief, zeigt die Anzeige später folgerichtig veraltete
Werte. Ein laufender Indexer ersetzt keinen laufenden Collector oder Logger.
Ohne eigene Sensorintervall-Konfiguration verwendet die Anzeige die vorhandene
Standardannahme von 60 Sekunden; die tatsächlichen Intervalle sind vor
Produktivbetrieb gesondert abzugleichen.

Rückweg zum vorherigen **Extension-Update** (nach mindestens zwei verschiedenen
installierten Ausgaben):

```bash
python3 install-pi.py extension-rollback
```

Bei einem fehlgeschlagenen Aktivierungsschritt versucht das Werkzeug, die
vorherige Ausgabe und ihren Indexer wiederherzustellen. Ein Fehler beim Rückweg
wird sichtbar gemeldet. Datenbank und Rohdaten werden nicht zurückgesetzt.

## Unterbrechen, wieder aufnehmen und Neustart

```bash
python3 install-pi.py status
sudo systemctl stop meteohub-dashboard-index.service
sudo systemctl stop meteohub-web-test.socket meteohub-web-test.service
```

Die bisherigen Dienste sind **temporäre Testdienste ohne Boot-Autostart**.
Nach einem Neustart, wenn Kandidat und Laufzeitumgebung bereits vorhanden sind:

```bash
cd "$HOME/src/meteohub"
python3 install-pi.py web
python3 install-pi.py extension-update
```

Für diese beiden Schritte ist das Originalimage nicht erforderlich. Einen
bereits belegten Testport oder eine andere geladene Testunit zuerst anhand von
`systemctl status meteohub-web-test.socket meteohub-web-test.service` prüfen.
Nicht blind fremde Dienste beenden.

Image nach der Vorbereitung aushängen:

```bash
python3 install-pi.py unmount-image
```

Das betrifft nur den gespeicherten, gegen den Originalpfad geprüften Loop-Mount;
die installierten Testkopien bleiben erhalten. Nach einem Rechnerneustart kann
eine alte `image-loop.device` auf eine nicht mehr gültige Zuordnung zeigen. Der
Installer stoppt dann bewusst. Erst mit `sudo losetup -l` und
`findmnt /mnt/meteohub-original` die Zuordnung prüfen; keine fremden Loop-Geräte
ablösen. Unterbrochene Downloads bleiben als `.part` erhalten. Nur die konkret
genannte Partialdatei nach Prüfung entfernen und den Schritt erneut starten.

## Belege und Grenzen dieser Veröffentlichung

- Bereits auf dem Pi manuell bestätigt: ARMHF-Bibliotheksauflösung aller fünf
  5.1e-Kernprogramme, native CGI-Oberfläche Build 277, private Konfiguration,
  Station-0-Plugin-Vorbereitung und lesender TCP-Empfang.
- Installer: automatisierte Prüfungen für vorhandene/beschädigte Downloads,
  fremde Mounts/Loop-Geräte, Wiederaufnahme und fremde laufende Webumgebung.
  APT/Mount sind dabei kontrollierte Testgrenzen, keine reale Neuinstallation.
- Erweiterung: echte Python-Index-/API-/SVG-Prozesse; Druck ohne THB-Temperatur,
  veraltete Daten, Update/Rollback, veränderte Dateien und fremde Ziele geprüft.
- Echter lighttpd-HTTP-Test unter systemd-Isolation mit Anmeldung, Dashboard,
  API, SVG, statischen Dateien, Methodenprüfung und gesperrten privaten Pfaden.
  Indexer-Start/Stop/Neustart tatsächlich ausgeführt; synthetische Daten.
- **Noch offen:** kompletter Installerlauf von leerer Pi-SD, vollständige Browser-/HTTP-Abnahme der neuen
  Extension auf ARM, dauerhafter Datenzubringer, nativer Logger/Archive/Aggregate/Exporte,
  Autostart und Langzeitabnahme. Diese Veröffentlichung behauptet keine fertige
  produktive Wetterstation.

Reproduzierbare lokale Tests:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tools/test-installer.py
PYTHONDONTWRITEBYTECODE=1 python3 tools/test-extension.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s dashboard -p 'test_weather*.py'
PYTHONDONTWRITEBYTECODE=1 python3 test-feed-process.py
```

Optional auf einem separaten Testsystem mit lighttpd/apache2-utils und systemd,
als root (synthetische private Laufzeitumgebung, keine echte Station):

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tools/test-web.py
PYTHONDONTWRITEBYTECODE=1 python3 tools/test-tcp-plugin-prepare.py --isolation
```

## Optional geplantes Read-only-System

Die gewünschte Trennung in schreibgeschütztes Betriebssystem, RAM-Puffer und
tägliche Sicherung ist [separat beschrieben](read-only-plan.md). `storage-check`
erfasst dafür nur den Zustand; der aktuelle Installer aktiviert noch keinen
RO-Modus und keinen Sicherungstimer.

## Pi-4-Zielprüfung am 7. November 2026

Betreiber-Ausgabe nach dem ZRAM-Neustart, ausgeführt als `meteohub`:

- Browser-Test wieder gestartet; Isolationsprüfung bestanden, ohne Anmeldung
  HTTP 401. Native Station-0-Konfiguration erneut erzeugt, 361 Bytes.
- TCP-Zubringer: 120,4 Sekunden, eine Verbindung, 17 Datensätze / 202 Bytes,
  keine verworfenen Datensätze, keine Teilzeilen-Abbrüche und keine Verdrängungen.
- Tatsächlich installierter Plugin-Wrapper: 16 Ausgaben plus ein separat
  geführter Druckwert, keine unerwartete Ausgabe/Verwerfung. Exit 124 war das
  vorgesehene Ende nach 15 Sekunden; `plugin_probe_passed=true`.
- THB-Stationsdruck 983,8 hPa wurde übernommen; THB-Temperatur/Feuchte nicht als
  Plugin-Datensatz ausgegeben. `t2 -5` entspricht -0,5 °C aus dem eigenen Sensor.
- Extension `8eebe649702e11208f2be80e1fc9d59fb1a191e6be0f7b7eeed7a5fe8478df5a`
  auf ARM installiert. Der echte Indexlauf schrieb 17 Datensätze ohne Ablehnung;
  der anschließende Indexer-Dienst startete. Gesamtablauf Exit 0.

Das bestätigt Installation und Indexverarbeitung auf ARM. Authentifizierte
Dashboard-/SVG-Antwort und Darstellung im Browser auf diesem Ziel sind noch
zu prüfen; die bisherigen echten HTTP-Tests liefen separat mit Testdaten.
Collector und Plugin des befristeten Tests sind beendet. Der Indexer läuft
weiter, erzeugt aber keine neuen Messungen. Native Archivierung, dauerhafter
Zubringer und RO-/RAM-/Sicherungsbetrieb sind dadurch noch nicht abgenommen.

### Aufruf aus einer Root-Shell

Auf diesem Pi brachte der Aufruf mit `sudo -iu meteohub bash -c ...` keine
Ausgabe. Die Ursache in der Login-Startkette ist nicht nachgewiesen. Der folgende
Aufruf mit explizitem HOME und ohne Bash-Startdateien funktionierte dagegen:

```bash
sudo -H -u meteohub -- /bin/bash --noprofile --norc -c '
set -e
cd "$HOME/src/meteohub"
python3 install-pi.py status
'
```

Damit wird kein Dienst als root gestartet; es bleibt beim bisherigen normalen
Anwendungsbenutzer. Keine Login-Dateien wurden zur Umgehung verändert.

## Native Logger-/Archivprüfung mit laufendem TCP-Zubringer

Die erfolgreiche Dashboard-Installation startet keinen nativen Logger. Deshalb
kann die alte Oberfläche weiterhin `Connection refused` auf `127.0.0.1:5555`
und `Data logging has been halted` melden. Ein ausschließlich laufender
Dashboard-Indexer ersetzt diesen Backendprozess nicht. Sensorzuordnungen auf
`Sensors` sind zusätzlich zu prüfen, sobald der Logger Sensoren liefert.

Der neue Befehl führt beide Prozesse gemeinsam für eine begrenzte Zeit aus:

```bash
python3 install-pi.py web
python3 install-pi.py native-test --source-host STATIONS_IP --source-port 5500 --duration 180
```

`STATIONS_IP` durch die eigene TCP-Kopie-Quelle ersetzen. Nur numerische
IP-Adressen sind in diesem Schritt erlaubt. Aus einer Root-Shell den oben
beschriebenen Aufruf als normaler Benutzer verwenden.

Der native Test:

1. Prüft den vorhandenen Kandidaten, den installierten Plugin-Wrapper, Station 0
   und die passende aktive isolierte Webunit. Ein gemeinsamer Lock verhindert
   parallele Installer-`feed-test`-/`native-test`-Aufrufe auf demselben Plugin-Cursor.
2. Sichert die private Anwendungskonfiguration in `native-logger-test-*` und
   erstellt eine separate Logger-Konfiguration mit deaktivierten Uploadintervallen.
   Standort-/Kalibrierungswerte werden nicht pauschal entfernt.
3. Startet den lesenden TCP-Zubringer als unprivilegierten, eingeschränkten
   Dienst. Die Quell-IP wird explizit übergeben; keine Befehle an die Wetterstation
   und kein direkter USB-Zugriff.
4. Startet das echte vorbereitete `loggerd -n -c ...` ohne alte Hersteller-
   Init-Skripte. Der Logger teilt den privaten Netzwerkbereich der geprüften
   Webunit (`JoinsNamespaceOf`), damit deren Zugriff auf Loopback-Port 5555
   grundsätzlich möglich ist. `/run` ist für diesen Test privat beschreibbar.
5. Lässt den Logger maximal 180 Sekunden arbeiten und beendet anschließend beide
   Dienste. Bestehende rohe Archivdateien werden nicht geleert. Neu angehängte
   Zeilen in `/data/weather/YYYYMM/raw` werden auf UTC-Zeitstempel, Sensor-ID und
   Zahlenformat geprüft. Alte Zeilen zählen nicht als Erfolg; ersetzte/gekürzte
   Archive und ungültige neue Zeilen verhindern eine erfolgreiche Abnahme.
6. Sichert stdout, stderr, beide Journale, Unit-Ergebnis und `result.json` auf
   dauerhaftem Speicher im privaten Report-Verzeichnis. Die normalen Ausgaben
   enthalten nur Zusammenfassungen, keine vollständige Logger-Konfiguration.

Als Erfolg gelten neue frische Rohdatensätze, tatsächlich neu empfangene TCP-
Datensätze und das erwartete Ende durch das Laufzeitlimit. Ein früher Prozess-
Exit, eine leere Datei oder lediglich `active` reichen nicht. Bei einem Fehler
bleiben die privaten Diagnoseberichte erhalten. Der Test verändert keine
Aktivierung und behauptet keine gültige Lizenz auf Grundlage einer leeren ID.

**Nach dem Test enden Collector und Logger wieder.** Der Befehl installiert
keinen Boot-Autostart. Die Oberfläche kann anschließend erneut einen fehlenden
Logger melden. Erst anhand des nativen Ergebnisses wird der dauerhafte Betrieb
samt Neustart und späterem RO-/RAM-Konzept eingerichtet.

Lokale Prüfung des neuen Startwegs:

```bash
# Parser/Archivprüfung; kein nativer ARM-Prozess:
PYTHONDONTWRITEBYTECODE=1 python3 tools/test-native-orchestration.py

# Als root auf einem separaten Testsystem mit systemd:
PYTHONDONTWRITEBYTECODE=1 python3 tools/test-native-orchestration.py --isolation
```

Vier Tests bestanden am 7. November 2026, einschließlich echter TCP-Verbindung,
echtem Plugin, einem ausdrücklich **synthetischen** Archivschreiber, privater
Loopback-Verbindung zwischen Units und zeitlich begrenztem Cgroup-Stop.
Der originale ARM-Logger auf dem Ziel-Pi wurde durch diesen lokalen Test
nicht geprüft; das nachfolgende Betreiberergebnis ist davon getrennt.

### Erstes natives Pi-Ergebnis: Archivierung noch fehlgeschlagen

Der Betreiberlauf vom 7. November 2026 (180 Sekunden) brachte 25 TCP-Datensätze
ohne Verwerfung, jedoch **keine neuen Roharchivzeilen**. Der Dienst erreichte
sein Laufzeitlimit (`Result=timeout`, Hauptprozess-Exit 0 beim Beenden), und die
Prüfung meldete folgerichtig `archive_observed=false`. Keine gekürzten oder
ersetzten Archive wurden beobachtet. Collector und Logger wurden beendet.

Die anschließende Betreiberdiagnose bestätigt: Die verwendete Konfiguration
enthielt `@LOGINTERVAL 0`, aber keine `@SENSORIDMAP`-Einträge. Plugin-Cursor und
Provenienz wurden während des Tests bis 12:56:50 CET aktualisiert; die letzten
Ausgaben enthielten `sol0`, `data0` und `uv0`. Der native Logger meldete Start,
Plugin-Verbindung und geordnetes Beenden durch das Testlimit, keinen Absturz.
Die Plugin-Ausgabe ist damit belegt, ihre Übernahme ins native Archiv noch nicht.

Die fehlende Zuordnung ist ein konkretes Hindernis: Laut
[Herstellerhandbuch, Abschnitt 2.5 Sensors](https://www.meteohub.de/files/meteohub-v4.6en.pdf)
werden Sensoren ohne zugewiesene ID nicht aufgezeichnet. Erst der erneute
Archivtest nach Zuordnung kann zeigen, ob weitere Hindernisse bestehen.

### Sensoren erstmals zuordnen

Der native Logger muss für die Sensorerkennung laufen. Dazu einen begrenzten
zehnminütigen Test starten (als normaler Anwendungsbenutzer im Repository):

```bash
python3 install-pi.py web
python3 install-pi.py native-test --source-host STATIONS_IP --source-port 5500 --duration 600
```

Während der Befehl läuft, die bisherige Weboberfläche über den SSH-Tunnel
öffnen und auf **Sensors** wechseln. Etwa zwei Minuten auf die unterschiedlich
häufig sendenden Sensoren warten und die Seite neu laden. Für Station 0 die
angezeigten Typen und ursprünglichen Kanalnummern prüfen und eindeutige IDs
zuweisen. Bei der bisher geprüften Quelle sind dies Temperatur Kanal 1 → `t1`,
Temperatur Kanal 2 → `t2`, Wind Kanal 0 → `wind0`, Solar Kanal 0 → `sol0`,
UV Kanal 0 → `uv0` und Daten Kanal 0 → `data0`. Nur tatsächlich erkannte Kanäle
zuordnen und **Save** drücken. Namen sind optional. Fehlende oder abweichende
Kanäle zuerst klären; keine Rohdaten oder Zuordnungen erfinden.

Seit der THB-Korrektur wird auch THB-Kanal 0 an den nativen Logger ausgegeben
und muss als `thb0` zugeordnet werden. Dashboard/SVG verwenden davon nur Druck.
Die vor der Korrektur dokumentierten Tests enthielten noch keinen nativen THB.

Dieser Test benutzt eine feste, separate Logger-Konfiguration. Ein Speichern
im Browser ändert diese laufende Kopie nicht. Eine Meldung „Data Logging
restarted“ aus der alten Oberfläche belegt hier keinen Neustart unseres
systemd-Testprozesses. Den Test regulär auslaufen lassen; ein negatives
Archivergebnis ist bei der noch unzugeordneten Startkonfiguration zu erwarten.
Keine parallelen Tests starten.

Nach Ende des Tests die gespeicherten UI-Einstellungen in eine neue
Logger-Konfiguration übertragen:

```bash
python3 tools/probe-cgi.py \
  "$HOME/meteohub-staging/5.1e-openssl3" \
  --runtime "$HOME/meteohub-staging/5.1e-runtime" \
  --generate-logger-config

grep -E '^@SENSORIDMAP[[:space:]]' \
  "$HOME/meteohub-staging/5.1e-runtime/root/home/meteohub/logger.conf"
```

Sind weiterhin keine Zuordnungen vorhanden, den Speichervorgang untersuchen.
Andernfalls mit der neuen Konfiguration die Archivprüfung wiederholen:

```bash
python3 install-pi.py native-test --source-host STATIONS_IP --source-port 5500 --duration 180
```

Erst frische native Roharchivzeilen belegen die erfolgreiche Aufzeichnung.

### Native Aufzeichnung nach Sensorzuordnung bestätigt

Der anschließende Betreiberlauf vom 7. November 2026 mit 300 Sekunden
Soll-Laufzeit erfasste 45 TCP-Datensätze ohne Verwerfung und schrieb **24 neue,
frische native Archivzeilen** nach `202611/raw` (560 zusätzliche Bytes):

| Archiv-ID | Neue Zeilen |
| --- | ---: |
| `t1` | 4 |
| `t2` | 1 |
| `sol0` | 7 |
| `uv0` | 7 |
| `data0` | 5 |

Keine ungültigen neuen Zeilen, keine gekürzten oder ersetzten Archive.
`archive_observed=true`; der Test meldete PASS. Nach 302,37 Sekunden war
auch das kontrollierte Beenden abgeschlossen. `Result=timeout` und der
systemd-run-Rückgabecode 1 gehören hier zum absichtlich gesetzten Laufzeitlimit;
der Hauptprozess beendete sich mit Status 0. Collector und Logger sind danach
gestoppt. Die geringere Anzahl an Archivzeilen gegenüber TCP-Zeilen ist allein
kein Verlustnachweis: Nicht alle eingehenden Sensorkanäle werden nativ
aufgezeichnet, und Druck wird separat verarbeitet.

Damit ist die Kette TCP-Kopie → Plugin → nativer ARM-Logger → Roharchiv für
die aufgeführten IDs belegt. Die zuvor fehlende Sensorzuordnung war eine
bestätigte Ursache der leeren Archive. Der erfolgreiche Lauf verwendete noch
Temperaturkanal 2 → `t1` und Temperaturkanal 1 → `t2`; Wind war nicht zugeordnet.
Die im Browser möglicherweise inzwischen korrigierten Zuordnungen müssen
erneut mit `--generate-logger-config` übernommen und kontrolliert werden.
Im folgenden Betreiberlauf mit korrigierten Temperaturzuordnungen und `wind0`
wurden 42 TCP-Datensätze empfangen und 41 native Archivzeilen geschrieben:
`wind0` 20, `t2` 3, `t1` 1, `sol0` 6, `uv0` 6 und `data0` 5. Keine verworfenen
TCP-Datensätze oder ungültigen neuen Archivzeilen; 1209 Bytes hinzugefügt,
keine gekürzten/ersetzten Archive. PASS nach kontrolliertem Ende (302,14 s).
Dieser Lauf nutzte noch die frühere Druckbehandlung ohne natives THB.
Langzeittest, dauerhafter Betrieb, Boot-Autostart und RO-Modus bleiben offen.
Ein begrenzter Test ist keine laufende Überwachung oder Produktionsabnahme.

## Native THB-Druckaufzeichnung aktualisieren

**Durch den direkten TCP-Umzugsweg abgelöst.** Dieser Abschnitt dokumentiert die
zuvor entwickelte Plugin-Korrektur; für den aktuellen Pi-Umzug nicht installieren.

Die bisherige ausschließliche Speicherung des Drucks im Anzeigeindex war für
eine vollständige Meteohub-Migration unzureichend. Mit Betreiberfreigabe wird
der ursprüngliche THB-Datensatz jetzt vollständig an den nativen Logger
weitergegeben. Dashboard/SVG nutzen daraus weiterhin nur Stationsdruck.
Die native THB-Sensoransicht kann auch die ursprünglichen Temperatur- und
Feuchtewerte anzeigen. Diese nicht als Temperatur-/Feuchtequelle für Anzeigen,
Wetterexporte oder Berechnungen auswählen. `t1`/`t2` bleiben die gewählten
Temperaturkanäle; die vorhandene Windchill-Auswahl bleibt `t2`.
Für die Druckreduktion bei Station 0 die vorhandene Einstellung
„based on station's altitude“ belassen; keine THB-Temperatur dafür auswählen.

Im dokumentierten Hersteller-Pluginformat ist Druck Teil von THB:
Temperatur in Zehntelgrad, relative Feuchte und Stationsdruck in Zehntel-hPa.
Die Korrektur ersetzt keine Messwerte. Beim Einlesen alter Roharchive wird
die Druckeinheit korrekt normalisiert und die native Ausgabe auf genau drei
THB-Eingabefelder begrenzt. Details: [Druckregel](feed-recovery.md#druck-aus-dem-kombisensor-getrennt-übernehmen).

Nach Ende laufender Feed-/Loggertests als normaler Anwendungsbenutzer:

```bash
cd "$HOME/src/meteohub"
git pull --ff-only
python3 install-pi.py plugin-update
python3 install-pi.py web
python3 install-pi.py native-test --source-host STATIONS_IP --source-port 5500 --duration 300
```

`plugin-update` akzeptiert nur die bekannte vorherige Plugin-Version oder die
aktuelle Version mit passendem Manifest und unverändertem Wrapper. Unbekannte
lokale Änderungen werden nicht überschrieben. Der gemeinsame Consumer-Lock
verhindert eine Aktualisierung während der installer-gesteuerten Tests.
Außerhalb des Installers manuell gestartete Plugin-Prozesse vorher beenden.
Sicherung von Plugin und Manifest: `runtime/tcp-plugin-before-*` (privat).
Die Dateien werden einzeln atomar ersetzt; bei einem abgefangenen Fehler wird
zurückgerollt. Kein transaktionssicheres Versprechen bei Stromausfall zwischen
beiden Dateiumbenennungen: Ein Manifestkonflikt muss anhand der Sicherung
repariert werden. Archive, Cursor, Plugin-Wrapper und Stationseinstellungen
bleiben erhalten. Es gibt keinen Neustart, Autostart oder historischen Replay.

Während des fünfminütigen Tests auf **Sensors** den neu auftauchenden
**THB-Kanal 0** als **`thb0`** zuordnen und **Save** drücken. Die vorhandenen
Zuordnungen nicht ändern. Dies ist zunächst die Erkennung mit laufendem Logger;
seine feste Testkonfiguration enthält die neue Zuordnung noch nicht.

Nach Testende die gespeicherte Einstellung übernehmen:

```bash
python3 tools/probe-cgi.py \
  "$HOME/meteohub-staging/5.1e-openssl3" \
  --runtime "$HOME/meteohub-staging/5.1e-runtime" \
  --generate-logger-config
grep -E '^@SENSORIDMAP[[:space:]]' \
  "$HOME/meteohub-staging/5.1e-runtime/root/home/meteohub/logger.conf"
```

Zusätzlich zu den bisherigen Einträgen wird `@SENSORIDMAP 0 2 0 0` erwartet
(Station 0, Typ THB, Quellkanal 0, Ziel-ID 0). Falls vorhanden, erneut mit
`native-test --source-host STATIONS_IP --source-port 5500 --duration 300`
prüfen. `thb0` muss dann in **frischen nativen Archivzeilen** erscheinen.
Die Druckwerte mit der Quelle vergleichen und Dashboard/SVG auf weiterhin
ausgeschlossene THB-Temperatur/Feuchte prüfen. Ein bloß erkannter Sensor oder
eine erfolgreiche Pipe-Ausgabe ist noch keine Druckarchiv-Abnahme.

Lokale Nachweise vom 7. November 2026:

- Echte Plugin-Prozesse: vollständige ursprüngliche THB-Ausgabe, Druckeinheiten
  in Plugin- und Roharchivformat, Ablehnung fehlerhafter Druckdaten,
  unveränderte Windfreigabe nach `t2`, kein Replay, Ende bei geschlossener Pipe.
- Tatsächlicher SQLite-Indexer: aus Live-THB und nativem THB-Rohformat nur Druck,
  keine Temperatur-/Feuchteeinträge.
- Neun Vorbereitung-/Update-Tests einschließlich realem TCP und unprivilegierter
  systemd-Plugin-Ausführung, Sicherung, Wiederholbarkeit, Rückrollen nach
  injiziertem Schreibfehler und Ablehnung unbekannter/parallel benutzter Stände.
- Vier Orchestrierungstests einschließlich realem TCP, Plugin, gemeinsamem
  privaten Netzwerk und **synthetischem** Archivschreiber; kein nativer ARM-Test.
- 13 Dashboard-Tests und sieben Installer-Tests bestanden.

Die native THB-Verarbeitung auf dem Ziel-Pi ist mit dieser Änderung noch nicht
abgenommen. Insbesondere muss der originale Logger den ungewöhnlichen
ursprünglichen THB-Temperaturwert akzeptieren, ohne den Druckdatensatz zu
verwerfen. Keine Produktionsfreigabe allein aus den lokalen Tests ableiten.

## Direkter nativer Meteohub-TCP-Empfang

Der ursprüngliche Meteohub stellt den Stationsdatenstrom selbst über TCP bereit:
erste Station auf Port 5500, weitere Stationen auf 5501 usw.
[Herstellerhandbuch v4.7, Abschnitte 2.4 und 4.3](https://www.meteohub.de/files/meteohub-v4.7en.pdf).
In der vorhandenen Hersteller-Oberfläche für Stationstyp **User-defined** ist
neben **Plug-in** auch **TCP/IP Meteohub** vorhanden (Verbindungstyp 4).
Deshalb benötigen wir weder einen JSON-Zwischenspeicher noch ein eigenes
Empfangsplugin. Auf dem alten Pi ist keine Änderung an `plugin.sh` erforderlich.

```text
alter Meteohub / Stationsdaten-Port → neuer originaler loggerd → natives Roharchiv
                                                               ↓
                                                         Dashboard / SVG
```

Der nachfolgende Test installiert noch keinen Dauerbetrieb. Die originale
ARM-Anwendung muss diese Verbindungsart auf dem Ziel-Pi erfolgreich ausführen.
Die Syntax und lokale Testmechanik sind geprüft; deren Erfolg ersetzt nicht
den Nachweis frischer nativer Wetterdaten vom echten alten Meteohub.

### Einstellungen im Browser

Alle bisherigen begrenzten Feed-/Loggertests zuerst auslaufen lassen. Nicht
parallel weitere Leser an den Stationsport hängen: Das Handbuch beschreibt
für diesen Port nur eine gleichzeitige Verbindung. Die Originalstation und
deren USB-Konsole bleiben unverändert; keine zweite serielle `cat`-Instanz.

Auf dem neuen Pi im bestehenden Meteohub-Webinterface:

1. **Weather Station 0 / User-defined** öffnen.
2. **Type of Connection** von **Plug-in** auf **TCP/IP Meteohub** stellen.
3. Im Geräte-/Adressfeld statt des Pluginpfads `STATIONS_IP:5500` eintragen.
   `STATIONS_IP` durch die IPv4-Adresse des alten Meteohubs ersetzen.
4. Name, Höhe, Druckberechnung nach Höhe und Windchill-Temperaturquelle `t2`
   sowie die vorhandenen Sensorzuordnungen beibehalten. **Save** drücken.

Dann als normaler Anwendungsbenutzer im Repository:

```bash
git pull --ff-only
python3 tools/probe-cgi.py \
  "$HOME/meteohub-staging/5.1e-openssl3" \
  --runtime "$HOME/meteohub-staging/5.1e-runtime" \
  --generate-logger-config
python3 install-pi.py direct-test --source-host STATIONS_IP --source-port 5500 --duration 300
```

Die Prüfung verlangt genau Station 0, Typ User-defined (9), Verbindung
Meteohub TCP (4), die explizit angegebene IPv4/Port-Kombination sowie die privaten
Archiv-/Logpfade. Andere Konfigurationen werden vor dem Start abgelehnt.
Sie liest und startet weder `live_feed_plugin.py` noch `tcp-feed.py`; installierte
ältere Plugin-Dateien und deren Cursor sind für diesen Weg unbenutzt.

### Begrenzter Test und Webzugriff

Die bisherige Testumgebung hat ein privates Netzwerk ohne externe Route. Für
den direkten Test teilt der native Logger vorübergehend das Hostnetz. Seine
cgroup-IP-Freigaben erlauben Loopback und die explizite Stations-IP. Die
Webunit teilt für den Zugriff auf den nativen Loopback-Port 5555 ebenfalls
vorübergehend das Hostnetz, erhält aber nur eine Loopback-IP-Freigabe.
Die bestehenden unprivilegierten Benutzer, privaten Dateisysteme, Authentifizierung
und der ausschließlich lokale HTTP-Listener `127.0.0.1:18090` bleiben erhalten.

Vor dem Wechsel werden echte lokale Verbindungen geprüft: Ein eigens gestarteter
nicht-Loopback-Testlistener ist mit expliziter Freigabe erreichbar und mit der
vorgesehenen Sperre nicht; Loopback bleibt erreichbar. Funktioniert die
Kernel-Durchsetzung nicht, startet die originale Anwendung nicht mit diesem
Netzprofil. Keine hostweiten Firewallregeln oder Interfaces werden geändert.

Die Web-Testunit wird zu Beginn kurz neu gestartet, damit die Sensors-Seite den
laufenden Logger erreicht. Nach Ende des Tests wird der Logger beendet und
die reguläre Web-Testunit mit privatem Netzwerk wiederhergestellt. Bei einem
Fehler dieses Rückwegs nennt das Werkzeug dies ausdrücklich. Dann die
konkreten Web-Testunits prüfen; keinen zweiten Logger starten.

Beim ersten Lauf **Sensors** öffnen, den tatsächlich erkannten THB-Kanal 0
als **`thb0`** zuordnen und **Save** drücken. Die anderen Zuordnungen beibehalten.
Die Kopie der Logger-Konfiguration bleibt während dieses Tests fest. Nach dem
Test die Konfiguration erneut mit `--generate-logger-config` erzeugen und
`direct-test` wiederholen, damit die neue THB-Zuordnung aktiv wird.
Die native THB-Ansicht enthält die ursprünglichen Temperatur-/Feuchtewerte;
Dashboard/SVG nutzen davon ausschließlich Druck. Temperatur-/Feuchtequellen
für Nutzanzeigen oder Exporte nicht auf diesen Kombisensor umstellen.

### Auswertung und verbleibende Arbeit

`native-direct-test-*` enthält private Konfigurationssicherung, Ausgangsgrößen
der Archive, stdout/stderr, natives Journal und `result.json`. Frische neue
Roharchivzeilen sind für PASS erforderlich; alte Daten, ein aktiver Dienst
oder eine gelungene TCP-Verbindung allein reichen nicht. Der Bericht enthält
keine unabhängigen TCP-Empfangszähler: Es läuft kein zusätzlicher Collector.
`pressure_archive_observed` meldet separat, ob frische `thb0`-Zeilen vorliegen;
deren Druckwerte sind anschließend gegen Quelle und Anzeige zu prüfen.
Während dieses Wegs kommen keine neuen JSON-Provenienzwerte hinzu. Der
Dashboard-Indexer kann weiterhin die nativen Roharchive lesen.

Der Lauf endet nach der angeforderten Zeit. `Result=timeout` ist das erwartete
Testende. Kein Hintergrundempfang, Autostart oder RO-Modus wird eingerichtet.
Erst nach nativer Abnahme folgen Dauerbetrieb, Aggregation/Exporte, Langzeittest
und Neustartprüfung. Beim späteren lokalen USB-Anschluss wird wieder die
originale Plug-in-Verbindung mit der passenden seriellen `cat`-Quelle benutzt;
keine proprietären Loggerprogramme werden dafür verändert.

Lokale Prüfung: Konfigurationsablehnung bei falscher Quelle/Verbindungsart,
reale systemd-IP-Filterprüfung, realer TCP-Empfang mit unveränderten Bytes,
keine Quellbefehle aus dem **synthetischen** Testlogger, Archivzählung und
Wiederherstellung des Web-Netzprofils. Ein absichtlich früh beendeter Testlogger
darf die vorhandenen Archivzeilen nicht erneut als Erfolg zählen.
Zusätzlich echte Lighttpd-/CGI-/HTTP-Tests im begrenzten Hostnetz: Authentifizierung,
Loopback-Backendzugriff, Dashboard/API/SVG und geschützte Dateien.
Diese Entwicklungsprüfungen führen den originalen ARM-Logger nicht aus.
