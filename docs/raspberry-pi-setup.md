# Meteohub von Anfang an auf einem Raspberry Pi einrichten

Stand: **5. November 2026**. Zielgeräte: **Raspberry Pi 3 Model B** und
**Raspberry Pi 4 Model B, auch die Variante mit 1 GB RAM**.

## Zuerst den richtigen Installationsweg wählen

Es gibt zwei unterschiedliche Wege. Bitte nicht deren Schritte vermischen:

| Weg | Ergebnis | Pi 3 Model B | Pi 4 Model B |
| --- | --- | --- | --- |
| **A: Original-Meteohub-Image** | Hersteller-Meteohub auf seinem alten Betriebssystem; nach Aktivierung und Einrichtung der Wetterstation verwendbar. Keine Trixie-Migration, kein neues Dashboard. | Vom Hersteller für Image 5.0s aufgeführt. | Für dieses Image nicht als unterstützt aufgeführt. Nicht verwenden. |
| **B: Aktuelle Trixie-Basis** | Frisches Raspberry Pi OS Lite, Zugang und unsere Quellen/Tests. Die vollständige native Meteohub-Installation ist noch auszuarbeiten. | Vorbereitung möglich; Anwendung auf echter Hardware noch nicht abgenommen. | Vorbereitung möglich; vorgesehenes nächstes Testgerät mit 1 GB RAM. |

**Ein fertiges, geprüftes Trixie-Meteohub-Image für einen echten Pi kann dieses
Projekt derzeit noch nicht liefern.** Unser bisheriges Testsystem ist ein
emulierter ARM-Gast. Sein Kernel wird von QEMU außerhalb des Disk-Images geladen;
das Image besitzt nicht automatisch die für einen echten Pi nötige Bootstruktur.
Es darf deshalb nicht als fertiges Pi-Image auf eine SD-Karte geschrieben werden.

Weg A ist nach der Herstellerdokumentation beschrieben, nicht durch eine neue
Hardwareinstallation dieses Projekts abgenommen. Weg B kennzeichnet den Punkt,
bis zu dem die Anleitung ausführbar ist. Kein Abschnitt behauptet, dass ein
erfolgreicher Start von Linux bereits eine funktionierende Wetterstation ist.

[Grundlagen](#1-was-ist-meteohub) · [Vorbereitung](#2-was-du-brauchst) ·
[Original installieren](#weg-a-original-meteohub-auf-dem-pi-3) ·
[Trixie vorbereiten](#weg-b-trixie-für-pi-3-oder-pi-4-vorbereiten) ·
[Sicherung](#7-eine-fertige-sd-karte-als-image-sichern) ·
[Fehlersuche](#8-wenn-etwas-nicht-funktioniert)

## 1. Was ist Meteohub?

Die **Wetterstation** besteht aus Sensoren und meist einer Konsole oder einem
Empfänger. Sie misst zum Beispiel Temperatur, Wind und Regen. Der **Raspberry Pi**
ist der kleine Computer, der die Daten entgegennimmt und speichert.

**Meteohub** ist die darauf laufende Wettersoftware. Der Logger liest Messwerte;
die Weboberfläche dient zur Einrichtung, Kontrolle und Diagrammerzeugung. Ein
**CGI-Programm** erzeugt eine Webseite auf dem Pi, die du im Browser öffnest.

Ein **Image** ist eine komplette Abbildung eines Datenträgers, einschließlich
Partitionen und Betriebssystem. Eine `.img`-Datei einfach als Datei auf eine
formatierte SD-Karte zu kopieren genügt nicht: Ein Schreibprogramm muss ihren
Inhalt auf die gesamte Karte übertragen.

Unser Repository enthält neue Hilfsprogramme und eine Anzeige ohne Flash.
Die ursprüngliche Meteohub-Anwendung ist separat zu beziehen und zu lizenzieren.
Ein Download ersetzt keine Aktivierung. Siehe
[Originalsoftware und Lizenz](../README.md#originalsoftware-und-lizenz).

## 2. Was du brauchst

- Einen Pi des für den gewählten Weg geeigneten Modells und ein dazu passendes
  Netzteil. Den Modellnamen auf der Platine prüfen. Die Angabe „Pi 3“ ist keine
  pauschale Freigabe aller späteren Pi-3-Varianten für das alte Herstellerimage.
- Eine **leere bzw. entbehrliche microSD-Karte**, einen Kartenleser und einen
  PC. Beim Schreiben werden alle Daten der ausgewählten Karte gelöscht.
  Eine vorhandene funktionierende Stationskarte zunächst unverändert aufheben.
- Für Weg A nennt der Hersteller 8 oder 16 GB. Für Weg B ist eine 16-GB-Karte
  ein sinnvoller Ausgangspunkt; zusätzlichen Platz für Wetterarchive einplanen.
- Ein Netzwerkkabel und einen Router mit DHCP. DHCP bedeutet, dass der Router
  dem Pi automatisch eine Netzwerkadresse zuweist. Für diese Anleitung zunächst
  kabelgebunden arbeiten.
- Eine von Meteohub unterstützte Wetterstation und das passende Datenkabel bzw.
  Interface. Ohne Messquelle kann die Oberfläche laufen, aber keine echten
  Wetterwerte liefern. Das genaue Stationsmodell vor der Auswahl prüfen:
  [Meteohub-Übersicht](https://wiki.meteohub.de/wiki/index.php/Introduction).
- Zugriff auf die Routeroberfläche, um die Adresse des neuen Pi abzulesen.
  Monitor und Tastatur als Rückweg bereithalten, falls der Netzzugang ausfällt.

Für den Pi 4 mit 1 GB planen wir ohne grafischen Desktop. Ob der vollständige
Stationsbetrieb auf diesem Gerät langfristig stabil läuft, muss noch gemessen
werden; die RAM-Größe allein ist kein Abnahmenachweis.

### Wo werden Befehle ausgeführt?

**PC/Linux** bezeichnet ein Terminal auf einem Debian-/Ubuntu-Rechner. Wer
Windows verwendet, folgt den ausdrücklich genannten Browser-/Imager-Schritten.
Linux-Befehle nicht unverändert in die Windows-Eingabeaufforderung einfügen.

**PC/SSH** bezeichnet ein Terminal auf deinem PC, in dem du eine Verbindung zum
Pi öffnest. **Pi** bedeutet: Der Befehl wird erst nach der Anmeldung im Terminal
des Pi ausgeführt. `sudo` führt einen einzelnen Befehl mit Administratorrechten
aus. Bei der Passworteingabe erscheinen üblicherweise keine Zeichen.

Codeblöcke ohne vorangestellte Shell-Prompts kopieren. Jeden Block fertig
ausführen lassen. Bei Fehlern zuerst die Ursache klären; nicht einfach mit dem
nächsten Installationsschritt fortfahren.

## Weg A: Original-Meteohub auf dem Pi 3

### A1. Image am PC herunterladen und entpacken

Die [offizielle Downloadseite](https://wiki.meteohub.de/wiki/index.php/Images)
listet für den Raspberry Pi das Image **5.0s**. Es enthält die alte Anwendung
und das dazugehörige alte Betriebssystem. Es wird nicht durch unsere Helfer
automatisch zu Trixie.

**Windows/macOS:** Lade das [RAR-Archiv 5.0s](https://www.meteohub.de/files/mhrpi-v5.0s.rar)
im Browser herunter. Entpacke es mit einem RAR-fähigen Programm. Das Ergebnis
ist eine Datei mit der Endung `.img`; deren Namen und Speicherort merken.

**Alternativ PC/Linux, Debian oder Ubuntu:**

```sh
sudo apt-get update
sudo apt-get install --no-install-recommends curl unrar-free
mkdir -p "$HOME/meteohub-download"
cd "$HOME/meteohub-download"
curl --fail --location --output mhrpi-v5.0s.rar https://www.meteohub.de/files/mhrpi-v5.0s.rar
unrar-free -t mhrpi-v5.0s.rar
unrar-free -x mhrpi-v5.0s.rar
find . -maxdepth 3 -type f -name '*.img' -print
sha256sum mhrpi-v5.0s.rar > mhrpi-v5.0s.rar.sha256
```

`-t` listet bei `unrar-free` den Archivinhalt, `-x` entpackt ihn. Falls der
Entpacker das Archiv nicht unterstützt, nicht mit einer unvollständigen Datei
weiterarbeiten; einen RAR-fähigen Entpacker verwenden. Der lokale SHA256-Wert
dient dem späteren Wiedererkennen der Datei, nicht als unabhängiger Herkunftsnachweis.
Downloadverzeichnis und Image bleiben außerhalb von Git und Webroots.

### A2. Image auf die SD-Karte schreiben – am PC

1. [Raspberry Pi Imager](https://www.raspberrypi.com/software/) installieren und
   starten. Für diesen Weg verwendest du **Use custom / Eigenes Image** und
   wählst die gerade entpackte `.img`-Datei, nicht Raspberry Pi OS.
2. Als Speicher die entbehrliche SD-Karte auswählen. Kapazität und Gerät genau
   prüfen; keine interne PC-Festplatte oder Backup-Platte auswählen.
3. Falls der Imager Anpassungen von Benutzer, WLAN oder SSH anbietet, diese für
   das alte fremde Meteohub-Image **nicht anwenden**. Das Image verwendet seine
   eigene Ersteinrichtung.
4. Schreiben und die anschließende Überprüfung vollständig abwarten. Karte
   sicher auswerfen. Die Herstelleranleitung beschreibt denselben Grundablauf
   mit älteren Schreibwerkzeugen:
   [Setup RPI](https://wiki.meteohub.de/wiki/index.php/Setup_RPI).

### A3. Pi starten und Adresse finden

Pi ausschalten, Karte einsetzen, Netzwerkkabel und Wetterstationsinterface
anschließen, danach erst die Stromversorgung verbinden. Laut Hersteller kann
der erste Start samt Einrichtung der Datenpartition und automatischem Neustart
einige Minuten dauern. Währenddessen nicht den Strom abziehen.

Im Router die neue DHCP-Adresse ablesen. Im Folgenden steht **PI-ADRESSE** für
diese tatsächliche Adresse. Im Browser öffnen:

```text
http://PI-ADRESSE/cgi-bin/meteohub.cgi
```

Die vom Hersteller dokumentierte erste **Webanmeldung** lautet Benutzer
`meteohub`, Passwort `meteohub`. Dies sind öffentliche Auslieferungswerte,
keine Zugangsdaten deiner bisherigen Station. Unter **Maintenance / Wartung**
sofort ein eigenes Webpasswort vergeben. Nur im vertrauenswürdigen lokalen Netz
arbeiten; das alte Betriebssystem nicht per Portweiterleitung veröffentlichen.

Die zusätzliche Hersteller-Notfalladresse ist kein Ersatz für die normale
DHCP-Einrichtung. Wenn kein DHCP-Eintrag erscheint, zunächst Kabel, Link-LEDs,
Netzteil und Bootvorgang am Monitor prüfen. Nicht blind das gesamte Heimnetz
auf einen anderen Adressbereich umstellen.

### A4. Lizenz, Uhrzeit und Wetterstation einrichten

In der nativen Weboberfläche in dieser Reihenfolge vorgehen:

1. **License / Lizenz:** Bedingungen lesen und gegebenenfalls akzeptieren.
   Eine Meldung über abgelaufenen Testbetrieb ist kein Netzwerkfehler.
2. **System Info / Systeminformationen:** System-ID und Softwareversion
   notieren. Über die [Hersteller-Aktivierung](https://wiki.meteohub.de/wiki/index.php/Activation)
   einen zur Installation passenden Aktivierungscode beziehen und unter
   **Wartung** eintragen. Bei einer vorhandenen Lizenz vorher die Bedingungen
   der [Lizenzübertragung](https://wiki.meteohub.de/wiki/index.php/Transfer)
   prüfen: Der Hersteller weist darauf hin, dass die alte Aktivierung dabei
   gesperrt wird. Nicht versehentlich eine noch benötigte Station deaktivieren.
3. **Settings / Einstellungen:** Zeitzone, Uhrzeit und Standortwerte passend
   setzen. Keine Werte einer fremden Station übernehmen. Systemzeit gegen eine
   verlässliche Uhr prüfen; eine falsche Uhr verfälscht Archivzeitstempel.
4. **Weather Station / Wetterstation:** Das tatsächliche Stationsmodell und
   dessen Anschluss auswählen. Ein USB-Gerät in Linux ist noch kein Nachweis,
   dass das richtige Protokoll eingestellt ist.
5. **Sensors / Sensoren:** Empfangene Sensoren identifizieren und logisch
   zuordnen. Temperatur, Feuchte, Wind, Regen usw. mit der Stationskonsole
   vergleichen. Senderkennungen und logische Kennungen wie `t0` oder `wind0`
   sind nicht zwangsläufig identisch. Nicht unsere lokalen Sensor-IDs blind
   übernehmen.
6. Erfassung über die in der Oberfläche angebotene Loggersteuerung starten
   bzw. nach Änderungen übernehmen lassen. Unter Datenansicht und Logs prüfen,
   dass **neue Messwerte mit fortschreitendem Zeitstempel gespeichert** werden.
   Fehlende Sensoren als fehlend behandeln, nicht durch feste Nullwerte ersetzen.

Die Bezeichnungen können mit Sprache und Version etwas abweichen. Das
[deutsche Herstellerhandbuch](https://www.meteohub.de/files/meteohub-v4.7.pdf)
beschreibt Einstellungen, Wetterstation, Sensoren und Wartung ausführlicher.
Keine Wetterdienste-/FTP-Zugänge eintragen, bevor der lokale Empfang geprüft ist.

### A5. Optionale Diagnose per SSH

Normalerweise lässt sich die Originalinstallation über die Weboberfläche
einrichten. Falls eine Shell nötig ist, **am PC**:

```sh
ssh root@PI-ADRESSE
```

`PI-ADRESSE` ersetzen. Den angebotenen Hostschlüssel beim ersten Zugriff gegen
die lokale Konsole prüfen. Der Hersteller nennt für alte Auslieferungen auch
für root das anfängliche Passwort `meteohub`. Nach erfolgreichem Zugriff
**auf dem Pi** ein eigenes Passwort setzen:

```sh
passwd
```

SSH- und Webpasswort sind getrennt. Bei einem Fehler wegen veralteter
SSH-Algorithmen keine globalen Sicherheitsoptionen des PCs abschalten; die
lokale Konsole verwenden und die konkrete Fehlermeldung prüfen.

Lesende Diagnose **auf dem Original-Pi**:

```sh
date
df -h
ps -ef | grep '[l]oggerd'
ls -l /data/weather
find /data/weather -maxdepth 2 -type f -name raw -print
```

Ein in der letzten Ausgabe gefundenes aktuelles Rohdatenfile dann z. B. mit
`tail -n 10 /data/weather/JAHRMONAT/raw` ansehen. `JAHRMONAT` durch den wirklich
vorhandenen Monat ersetzen. Ältere Rohdaten können UTC-Zeitstempel tragen;
Zeitdifferenzen nicht ohne Prüfung als Ausfall interpretieren.

Kein pauschales `apt upgrade` über viele Debian-Generationen durchführen.
Dieser Weg richtet bewusst die alte Herstellerversion ein; die Trixie-Migration
ist ein separates Projekt.

### A6. Wann ist diese Installation tatsächlich fertig?

Die Oberfläche muss erreichbar und aktiviert sein. Zusätzlich müssen neue
Messwerte aller eingerichteten Sensoren ankommen und im Archiv stehen. Nach
einem kontrollierten Neustart muss dies erneut funktionieren. Die jeweiligen
Sensorintervalle berücksichtigen; ein Regenzähler muss bei Trockenheit nicht
steigen, sein Empfang lässt sich nicht allein an der Zahl ablesen.

Anschließend eine Nacht bzw. mindestens 24 Stunden laufen lassen und die
gespeicherten Daten auf Lücken und falsche Uhrzeiten prüfen. Erst dann die
Datenträgersicherung aus Abschnitt 7 erstellen. Das neue Dashboard dieses
Repositorys ist damit noch nicht installiert.

## Weg B: Trixie für Pi 3 oder Pi 4 vorbereiten

### B1. Aktuelles Betriebssystem mit Imager schreiben – am PC

Diese Schritte verwenden eine eigene Karte; nicht die funktionierende
Originalstation überschreiben.

1. Raspberry Pi Imager starten und das genaue Pi-Modell auswählen.
2. **Raspberry Pi OS Lite (32-bit), Trixie** auswählen. Lite bedeutet ohne
   grafischen Desktop. Nicht das alte Meteohub-Image und nicht versehentlich
   eine ältere Raspberry-Pi-OS-Version verwenden. Unsere ursprünglichen
   Programme sind ARM-32-Bit-Binaries; deshalb ist hier ein 32-Bit-Userspace
   vorgesehen. Ein 64-Bit-Kernel allein sagt nichts über den Userspace aus.
3. Hostname beispielsweise `meteohub`, Benutzername beispielsweise `wetter`,
   ein eigenes Passwort und die passende Zeitzone eintragen.
4. SSH aktivieren. Eigenen SSH-Schlüssel eintragen oder für die erste Einrichtung
   die Passwortanmeldung wählen. Es gibt bei diesem Weg kein automatisch
   gültiges Meteohub-Auslieferungspasswort.
5. SD-Karte auswählen, schreiben, verifizieren lassen und sicher auswerfen.
6. Karte in den stromlosen Pi einsetzen, Netzwerkkabel anschließen, einschalten.

Die [Raspberry-Pi-Anleitung](https://www.raspberrypi.com/documentation/computers/getting-started.html)
erläutert Imager und die Ersteinrichtung. Falls Imager bei deinem Modell keinen
passenden Trixie-/32-Bit-Eintrag anbietet, keine andere Architektur als vermeintlich
gleichwertigen Ersatz wählen; zuerst das ausgewählte Image klären.

### B2. Erste Anmeldung und System prüfen

**Am PC**, mit dem in Imager festgelegten Benutzernamen:

```sh
ssh wetter@meteohub.local
```

Falls die Namensauflösung nicht funktioniert, die DHCP-Adresse aus dem Router
verwenden: `ssh wetter@PI-ADRESSE`. Nach der Anmeldung **auf dem Pi**:

```sh
cat /etc/os-release
dpkg --print-architecture
tr -d '\000' < /proc/device-tree/model
printf '\n'
free -h
df -h /
ip -br address
ip route
timedatectl status
```

Erwartet sind Trixie als Versionsname, `armhf` als Paketarchitektur und das
tatsächlich verwendete Pi-Modell. `arm64` bedeutet, dass ein anderer
Userspace installiert wurde. Dann für diese Anleitung mit dem richtigen Image
neu beginnen. Bei 1 GB RAM erscheint wegen Reservierungen weniger nutzbarer
Speicher; kein Desktop wird benötigt.

### B3. Basissystem aktualisieren und neu starten

**Auf dem frisch installierten Pi**; Monitor/Routerzugriff als Rückweg verfügbar
halten. Noch läuft dort keine Wettererfassung:

```sh
sudo apt-get update
sudo apt-get upgrade
sudo timedatectl set-timezone Europe/Berlin
sudo timedatectl set-ntp true
sudo reboot
```

Paketplan vor Bestätigung lesen. `Europe/Berlin` bei anderem Standort passend
ersetzen. Ein Neustart trennt SSH. Nach dem Wiederanlauf **am PC** erneut
anmelden, dann **auf dem Pi** prüfen:

```sh
systemctl --failed --no-pager
timedatectl status
sudo dpkg --audit
```

Erwartet: keine fehlgeschlagenen Dienste, korrekte Uhrzeit und keine
unvollständige Paketinstallation. Eine neue erfolgreiche SSH-Anmeldung ist
wichtig; die alte Sitzung vor dem Neustart genügt nicht als Zugangsprüfung.

### B4. Projektquellen holen und lokale Tests ausführen

**Auf dem Pi**, als normaler Benutzer, nicht dauerhaft in einer Root-Shell:

```sh
sudo apt-get install --no-install-recommends git python3 ca-certificates
mkdir -p "$HOME/src"
cd "$HOME/src"
git clone https://github.com/dg8ygz/meteohub.git
cd meteohub
git rev-parse HEAD
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s dashboard -p 'test_weather*.py'
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s . -p 'test_normalize_native.py'
PYTHONDONTWRITEBYTECODE=1 python3 test-feed-process.py
```

Erwartet beim dokumentierten Stand: 13 Tests im ersten Lauf, vier im zweiten,
anschließend eine `PASS`-Zeile des Prozesstests. Dieser verwendet Testdaten und
benötigt keine Wetterstation. `git rev-parse HEAD` notiert die genaue Version,
damit ein späterer Fehlerbericht zugeordnet werden kann.

**Bis hier ist ein aktuelles Linux mit getesteten Projektquellen eingerichtet.
Noch keine Meteohub-Weboberfläche und noch kein Stationslogger.** Ein Browser-
Fehler auf Port 80 ist an diesem Punkt erwartbar. Es gibt hier noch keinen
universellen `install.sh`-Befehl.

### B5. Warum die native Meteohub-Installation noch eine offene Stufe ist

Die [Original-Binaries](../README.md#original-binaries-beschaffen) werden separat
benötigt. Einfach `/home/meteohub` und ein CGI in den Webroot zu kopieren reicht
für unsere Trixie-Migration nicht. Im emulierten Testgast wurden zusätzliche,
versionsabhängige Bibliotheksanpassungen, Webserverregeln, Verzeichnisse und
systemd-Dienste eingerichtet. Diese sind noch nicht als allgemeiner, auf Pi 3
oder Pi 4 geprüfter Installer verfügbar.

Vor einer Fortsetzung bis zur fertigen Pi-Wetterstation sind konkret nötig:

| Schritt | Erforderlicher Nachweis |
| --- | --- |
| Originalsoftware importieren | Version, ARM-ABI, alle Bibliotheken und Webressourcen erfasst; keine alten Systembibliotheken über Trixie kopieren. |
| Aktivierung | Gültige Aktivierung für die Zielhardware; keine Übernahme einer fremden Hardwareidentität. |
| Weboberfläche | Authentifizierung, CGI-Zuordnung, leere GET-Anfragen, historische Diagramme und native Einstellungen auf dem echten Pi geprüft. |
| Direkt angeschlossene Wetterstation | Gerätezuordnung, Zugriffsrechte, genau ein lesender Logger, Erfassung und Neustart geprüft. |
| Archiv und Dienste | Persistente Datenpfade, Aggregation, Export, Bootreihenfolge und kontrolliertes Stoppen vollständig eingerichtet. |
| Neue Anzeige | Anzeigeindex, Sensorzuordnung, Intervalle, API und SVG eingerichtet und gegen echte Messwerte geprüft. |
| Abnahme | Neuer SSH-Zugang nach Reboot, aktuelle Sensorwerte, gespeicherte Rohdaten, Diagramme, 24-Stunden-Lauf und Rückweg nachgewiesen. |

`prepare_logger.py` und `rcloggerd` aus diesem Repository sind ausdrücklich
**Laborhelfer für eine Plugin-Messwertkopie**. Sie erzwingen diese Quelle und
sperren Uploads. Sie dürfen in einer neuen direkt angeschlossenen Station nicht
als fertige universelle Loggerinstallation ausgegeben werden. Auch die Anzeige
verwendet derzeit teilweise feste Sensor-IDs, die zur eigenen Station passen
müssen.

Deshalb stehen hier keine geratenen Kopier-, Bibliotheks- oder Dienstbefehle,
die anschließend eine fertige Installation behaupten. Für den vorhandenen Pi 4
mit 1 GB ist **B1–B4** die konkrete Vorbereitung für den nächsten Hardwaretest.
Erst nach dieser nativen Abnahme lässt sich B5 durch eine belastbare Folge von
Installationsbefehlen ersetzen.

## 7. Eine fertige SD-Karte als Image sichern

Das gilt für eine geprüfte Originalinstallation nach A6. Bei Weg B enthält eine
Sicherung derzeit nur den erreichten Vorbereitungsstand, keine fertige
Trixie-Meteohub-Station.

Pi sauber herunterfahren: bei Weg A die Abschaltfunktion der Oberfläche oder
als root `poweroff`, bei Weg B in SSH `sudo poweroff` verwenden. Erst nach dem
Herunterfahren die Stromversorgung trennen und die Karte in den PC einsetzen.
Nicht das laufende, sich verändernde Root-Dateisystem als vollständige Sicherung
ausgeben.

**PC/Linux:** Erst die Karte anhand Modell, Größe und Anschluss identifizieren:

```sh
lsblk -o NAME,SIZE,MODEL,TRAN,TYPE,MOUNTPOINTS
```

Die folgende Sicherung liest das **gesamte Gerät**, nicht nur eine Partition.
`/dev/sdX` ist ein Platzhalter und muss ersetzt werden. Alle von der Karte
automatisch eingebundenen Partitionen zuvor im Dateimanager sicher aushängen.
Die Zieldatei muss auf einer anderen Platte mit genügend freiem Platz liegen.

```sh
mkdir -p "$HOME/meteohub-backup"
chmod 700 "$HOME/meteohub-backup"
umask 077
read -r -p 'Gesamtes SD-Geraet, z.B. /dev/sdX (keine Partition): ' card_device
lsblk -o NAME,SIZE,MODEL,TYPE,MOUNTPOINTS "$card_device"
```

Die Ausgabe erneut prüfen. Erst danach **im selben Terminal**:

```sh
backup_image="$HOME/meteohub-backup/meteohub-$(date +%Y%m%d-%H%M%S).img"
sudo dd if="$card_device" bs=4M status=progress > "$backup_image"
sync
sha256sum "$backup_image" > "$backup_image.sha256"
```

Bei einem Lesefehler ist die Sicherung nicht vollständig; nicht als erfolgreich
kennzeichnen. Die Datei enthält auch Kennwörter und Aktivierungsdaten und bleibt
privat. Für die Wiederherstellung das Backup im Imager als eigenes Image auf
eine zweite, mindestens gleich große Karte schreiben und verifizieren lassen.
Die Originalkarte aufheben. Danach Boot, Anmeldung und neue Messwerte erneut
prüfen; je nach Lizenzbindung kann eine erneute Aktivierung erforderlich sein.

Unter Windows ein Kartenleseprogramm mit Funktion **Read / Image erstellen**
verwenden. Raspberry Pi Imager schreibt Images; sein Schreibvorgang ersetzt
keine vorherige Sicherung der eingelegten Karte.

## 8. Wenn etwas nicht funktioniert

| Beobachtung | Nächster Schritt |
| --- | --- |
| Pi bootet nicht | Modell/Image-Zuordnung, abgeschlossene Schreibprüfung, Karte und Netzteil prüfen; Bildschirm anschließen. Das alte 5.0s-Image nicht auf dem Pi 4 voraussetzen. |
| Kein DHCP-Eintrag | LAN-Kabel, Routerport und Link-LEDs prüfen; Bootmeldungen lokal ansehen. |
| `meteohub.local` unbekannt | Im Router gefundene IP verwenden; `.local`-Namensauflösung ist nicht in jedem Netz verfügbar. |
| Browser meldet Verbindung abgelehnt | Bei Weg B bis B4 normal: noch kein Webserver installiert. Bei Weg A Boot abwarten und Adresse/CGI-Pfad prüfen. |
| Lizenz abgelaufen | System-ID und Aktivierungsstatus in der Oberfläche prüfen; nicht die Uhr zurückstellen. |
| Oberfläche da, aber keine Werte | Stationsmodell/Anschluss/Sensorzuordnung prüfen; Logger und Datenansicht kontrollieren. HTTP 200 allein ist kein Empfangsnachweis. |
| Werte stehen still | Zeitstempel und jeweiliges Sensorintervall prüfen, danach Logger-/USB-Meldungen untersuchen. |
| Neue SVG zeigt Striche | Rohdaten, Indexstatus, Sensor-IDs und Aktualität prüfen. Striche sind bewusst keine erfundenen Nullwerte. |

Bei einem Problem Gerätetyp, Installationsweg, Image-/Projektversion, Schritt
und genaue Fehlermeldung notieren. Keine Zugangsdaten, Aktivierungscodes oder
vollständigen privaten Konfigurationen in ein öffentliches Issue stellen.
