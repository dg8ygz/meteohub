# Geführter Installer und separates Dashboard-Update

Stand: 7. November 2026. Der Installer fasst die bisher einzeln ausgeführten,
geprüften Vorbereitungsschritte zusammen. Er richtet die **5.1e-Testoberfläche**
und optional die **Dashboard-/SVG-Erweiterung** ein. Er ist noch kein fertiger
Produktionsinstaller für die gesamte Wetterstation: nativer Logger,
Archiv-/Aggregat-/Exportabnahme, dauerhafter Datenzubringer und Autostart bleiben
separate Schritte. Er akzeptiert keine Lizenzbedingungen und wählt keine Station
stellvertretend für den Anwender.

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
Ausgabe und übernehmen nur gültigen **Stationsdruck** aus THB; dessen Temperatur
und Feuchte werden nicht ausgegeben. Der Druck wird im Herkunftsprotokoll für
die Anzeige geführt, nicht als vollständiger nativer THB-Datensatz ausgegeben.

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
- **Noch offen:** kompletter Installerlauf von leerer Pi-SD, ARM-Abnahme der neuen
  Extension, dauerhafter Datenzubringer, nativer Logger/Archive/Aggregate/Exporte,
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
