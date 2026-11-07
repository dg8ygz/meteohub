# Dauerhafter direkter TCP-Empfang und Autostart

Stand: 7. November 2026. Dieser Schritt folgt **nach** dem erfolgreichen
begrenzten [direkten Empfangstest](installer.md#direkter-nativer-meteohub-tcp-empfang).
Er installiert den originalen Logger, die private Weboberfläche und den
Dashboard-Indexer als dauerhafte systemd-Dienste. Die bisherigen Tests bleiben
als Diagnosewerkzeuge erhalten, dürfen aber nicht parallel zum Dauerbetrieb laufen.

**Prüfstand:** Echte systemd-Dienste, TCP-Verbindungen, HTTP-Anmeldung,
Dateisystem-Isolation, Neustart nach Prozessabbruch und Rückbau sind mit einer
synthetischen Anwendung lokal geprüft. Das ist keine Abnahme des originalen
ARM-Loggers im Dauerbetrieb und kein echter Pi-Neustart. Diese Zielprüfungen
folgen erst nach Ausführung der nachstehenden Schritte durch den Anwender.

## Voraussetzungen

- Vorbereitete 5.1e-Laufzeit und passende laufende private Testoberfläche.
- Installierte Dashboard-/SVG-Erweiterung.
- Ein erfolgreicher `direct-test` mit frischen nativen Archivzeilen für
  **dieselbe** Quelle und Logger-Konfiguration. Der Installer prüft den privaten
  Testbericht gegen die aktuelle Konfiguration. Bei inzwischen geänderten
  Sensorzuordnungen zuerst erneut testen.
- Eigene Quell-IP und eigener Stationsport. `STATIONS_IP` ersetzen; Port 5500
  bezeichnet die erste Quellstation. Sensorzuordnungen, Höhe und Druckregel
  stammen aus der eigenen gespeicherten Konfiguration, nicht aus einem Beispiel.
- Keine weiteren Leser am Quellport. Keine Änderungen am ursprünglichen Pi
  oder an dessen serieller Konsole nötig.

Der direkte Weg setzt einen schon vorhandenen Meteohub-TCP-Datenstrom voraus.
Die spätere Umstellung auf eine lokal angeschlossene USB-Konsole ist ein
separater Schritt. Aggregation und externe Wetter-Uploads werden hier nicht
eingerichtet; die drei Uploadfrequenzen in der privaten Logger-Kopie bleiben 0.

## Installation auf dem neuen Pi

Als normaler Anwendungsbenutzer im Repository:

```bash
cd "$HOME/src/meteohub"
git pull --ff-only
python3 install-pi.py web
python3 install-pi.py extension-update
python3 install-pi.py live-install --source-host STATIONS_IP --source-port 5500
```

`web` und `extension-update` stellen die Voraussetzungen her; sie starten noch
keinen Empfang. `live-install` sichert die Anwendungskonfiguration und die
erzeugten Units unter einem privaten `live-before-*`-Verzeichnis. Vor dem
Wechsel werden die tatsächlichen Kernel-IP-Sperren geprüft. Fremde Units und
abweichende bestehende Dateien werden nicht ersetzt.

Bei erfolgreicher Installation laufen diese Dienste weiter, auch nach Ende
der SSH-Sitzung:

| Unit | Aufgabe |
| --- | --- |
| `meteohub-live.target` | Gemeinsamer Start/Stop; für den Systemstart aktiviert. |
| `meteohub-live-runtime.service` | Gemeinsamer flüchtiger PID-/Laufzeitbereich unter `/run`. |
| `meteohub-live-logger.service` | Originaler Logger mit direktem TCP-Empfang, ohne Collector oder Eingangsplugin. |
| `meteohub-web-test.socket` / `.service` | Bisheriger Name bleibt zur Kompatibilität erhalten; jetzt dauerhafte Units für den lokalen Webzugriff. |
| `meteohub-dashboard-index.service` | Liest native Roharchive und aktualisiert den abgeleiteten Anzeigeindex. |

Die Anwendung läuft mit dem normalen Benutzer in der privaten Laufzeitumgebung.
Logger und Weboberfläche teilen den flüchtigen `/run`-Bereich, damit PID-Angaben
zur selben Instanz gehören. Der Logger darf Loopback und die Quell-IP erreichen;
die Weboberfläche nur Loopback. Der Indexer hat ein privates Netz ohne externe
Route. Die Quellfreigabe ist eine IP-, keine Portbeschränkung. Keine hostweiten
Firewallregeln oder Netzwerkadressen werden verändert.

Die Services starten nach einem Prozessende mit 30 Sekunden Abstand erneut.
Das ist **keine** Erkennung eines noch laufenden, aber festhängenden Empfängers.
Eine echte Quellunterbrechung und Wiederverbindung müssen auf dem Ziel noch
beobachtet bzw. gezielt geprüft werden.

## Frische Archivierung und Anzeige prüfen

Nach einem ausreichend langen Fenster für die eigenen Sensorintervalle:

```bash
python3 install-pi.py live-status
```

Der Bericht nennt Aktivzustände, Boot-Aktivierung, neue Rohdaten seit der
Installation, letzte Sensorzeitstempel und Indexstatus. Ein aktiver Dienst
allein ist kein Messwertnachweis. Der begrenzte Blick auf die letzten
Archivzeilen ist außerdem keine vollständige Lückenanalyse.

Prüfen:

1. `boot_enabled` ist `true`; Logger, Web und Indexer sind aktiv.
2. Neue native Rohdaten kommen hinzu; die erwarteten Sensor-IDs erscheinen
   innerhalb ihrer tatsächlichen Intervalle. `recent_sensors` zeigt Alter und UTC.
3. Keine neuen Formatfehler oder unerwartet ersetzten/gekürzten Roharchive.
   Der Bericht wird während laufender Schreibzugriffe erstellt, nicht aus einem
   eingefrorenen Archivsnapshot. Auffälligkeiten anhand der konkreten Zeilen prüfen.
4. Indexstatus hat keinen Fehler und einen aktuellen `last_success`.
5. Im Browser stimmen echte neue Werte, Einheiten und Sensorquellen.
   Die [stationsabhängigen Anzeigevorgaben](station-example.md) gelten weiterhin.

Zugriff wie bisher über den SSH-Tunnel, geöffnet **am eigenen Rechner**:

```bash
ssh -N -L 18090:127.0.0.1:18090 BENUTZER@PI_IP
```

- Meteohub: <http://127.0.0.1:18090/cgi-bin/meteohub.cgi>
- Dashboard: <http://127.0.0.1:18090/dashboard/>
- SVG: <http://127.0.0.1:18090/cgi-bin/weather-image.cgi>

Alle Wege bleiben passwortgeschützt. Kein öffentlicher Listener wird eingerichtet.
Die bekannte native MAC-/Netzwerkwarnung ist mit diesem Schritt nicht behoben.
Die Netzwerkseite des alten CGI nicht zur Konfiguration des echten Pi verwenden.

## Neustart und längerer Betrieb

**Erst nach bestätigten frischen Daten** und mit verfügbarem lokalen Rückweg
einen geplanten Pi-Neustart durchführen. Vorher `live-status` sowie die relevanten
Journale dauerhaft privat speichern. Nach dem Neustart eine neue SSH-Anmeldung
prüfen und erneut `live-status` ausführen. Nicht `direct-test` oder einen
zusätzlichen Collector starten. `boot_changed_since_install` kann den Wechsel
der Boot-ID anzeigen; entscheidend bleiben neue Daten nach diesem Neustart.

Danach mindestens 24 Stunden beobachten: erwartete Sensorintervalle gegen das
gesamte native Archiv vergleichen, Lücken und Dienstneustarts erfassen sowie
Anzeige und Rohdaten abgleichen. Eine alte Archivzeile oder eine einzelne
Statusabfrage genügt nicht. Es wird keine automatische Alarmierung oder
vollständige Lückenüberwachung installiert.

## Wartung, Wiederanlauf und Rückweg

Bewusst anhalten **und** Boot-Autostart deaktivieren:

```bash
python3 install-pi.py live-stop
```

Wieder starten und Boot-Autostart aktivieren:

```bash
python3 install-pi.py live-resume
python3 install-pi.py live-status
```

Nur die Anzeige aktualisieren, während der Live-Target aktiv ist:

```bash
git pull --ff-only
python3 install-pi.py extension-update
```

Dabei wird nur der Indexer angehalten und wieder gestartet. Der Empfänger läuft
weiter. Bei bewusst gestopptem Live-Target zuerst `live-resume` ausführen.

Zur bisherigen temporären Web-/Index-Testumgebung zurückkehren:

```bash
python3 install-pi.py live-remove
```

Das deaktiviert den Boot-Target, stoppt die Dienste und entfernt nur die
unverändert wiedererkannten Unit-Dateien. Roharchive, Anwendungseinstellungen
und Sicherung bleiben erhalten. Der native Logger ist anschließend **aus**;
Web und Indexer laufen wieder als temporäre Testdienste ohne Autostart.
Ein erkannter Installationsfehler versucht denselben Rückweg. Bei unterbrochener
Installation bleibt `live-install.json` zur Diagnose erhalten; nach Prüfung
`live-remove` verwenden. Bei manuell veränderten Units wird der Rückbau
abgebrochen, statt diese Änderungen zu überschreiben. Ein fehlgeschlagener
Web-Wiederanlauf ist gesondert zu beheben; kein zweiter Logger als Ersatz.

## Konfigurationsänderungen und Speicher

Der Logger verwendet eine gesonderte, schreibgeschützt eingebundene Kopie unter
`runtime/live/logger.conf`. Ein **Save** im alten CGI ersetzt diese laufende
Konfiguration nicht. Änderungen an Quelle oder Sensorzuordnung derzeit über
`live-remove`, Speichern im CGI, erneute Konfigurationserzeugung und einen
erfolgreichen `direct-test` abnehmen; danach erneut `live-install` ausführen.
Der Installer blockiert begrenzte Empfangstests, solange die Live-Installation
registriert ist. Zusätzlich hält der laufende Logger dieselbe Dateisperre wie
die Testhelfer. Manuell gestartete fremde Leser kann diese Sperre nicht verhindern.

Nur Prozesszustand unter `/run` ist hier flüchtig. **Roharchive, Anwendungskonfiguration,
native Logs und SQLite liegen weiterhin auf der SD-Karte.** Es gibt noch keinen
RO-Modus, RAM-Wetterpuffer oder täglichen Sicherungstimer. Pro Dienst gelten
128 MiB RAM, 32 Tasks und 1 GiB maximale Dateigröße; Speicherplatz und Monatsarchive
müssen beobachtet werden. Die [RO-/RAM-Umstellung](read-only-plan.md) folgt separat.

## Reproduzierbare Entwicklungsprüfung

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tools/test-live-service.py
PYTHONDONTWRITEBYTECODE=1 python3 tools/test-installer.py
PYTHONDONTWRITEBYTECODE=1 python3 tools/test-extension.py
```

Optional als root auf einem separaten Entwicklungsrechner:
`python3 tools/test-live-service.py --isolation`. Dieser Test verwendet eindeutige
temporäre Test-Unitnamen, prüft vorab Port 18090 und entfernt seine Units danach.
Die Testdatei nennt den Pfad zur lokal entpackten Lighttpd-Ausgabe; ohne diese
wird der Integrationsteil übersprungen. Kein ARM-Binary, echter Stationsport oder
Rechnerneustart wird dabei verwendet. Geprüft sind echter TCP-Empfang und Archiv,
exklusive Empfangssperre, geteilter flüchtiger PID-Bereich, HTTP-Authentifizierung,
Prozessabbruch/Wiederanlauf, Extension-Update ohne Logger-Neustart, gemeinsamer
Stop/Start, Ablehnung veränderter Units und Rückkehr zur privaten Webumgebung.
