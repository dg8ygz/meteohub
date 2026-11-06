# Meteohub von Anfang an auf einem Raspberry Pi einrichten

Stand: **6. November 2026**. Zielgeräte: **Raspberry Pi 3 Model B** und
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

**Ausgangsbasis des laufenden Pi-4-Aufbaus (6. November 2026):** Der Anwender
hat Raspberry Pi OS Lite heruntergeladen, auf dem Pi installiert und vor der
Meteohub-Einrichtung auf den aktuellen Paketstand gebracht. Geprüft wurden
Trixie mit Paketarchitektur `arm64`, Kernel `6.18.60+rpt-rpi-v8` nach Neustart,
ein unauffälliges `dpkg --audit` und keine fehlgeschlagenen systemd-Dienste.
Es wurde kein altes Meteohub-Komplettimage als Betriebssystembasis verwendet.
Der folgende Bestandsweg für eine vorhandene 64-Bit-Installation beschreibt
diesen Aufbau; B1 beschreibt dagegen die alternative Neuinstallation auf einer
eigenen Karte. Diese Basisprüfung ist noch keine Meteohub-Funktionsabnahme.

### B1. Aktuelles Betriebssystem mit Imager schreiben – am PC

**Ist Trixie bereits installiert und bootfähig, direkt mit B2 beginnen.**
Eine vorhandene 64-Bit-Installation nicht vorsorglich überschreiben. Zuerst
Modell, Paketarchitektur und die Laufzeitbedingungen der alten ARM-Programme
prüfen. Der unten beschriebene 32-Bit-Weg ist eine Vorbereitungsempfehlung für
eine neue Karte, kein Grund zum Löschen einer bestehenden Installation.

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
uname -m
dpkg --print-architecture
dpkg --print-foreign-architectures
tr -d '\000' < /proc/device-tree/model
printf '\n'
free -h
df -h /
ip -br address
ip route
timedatectl status
```

Erwartet sind Trixie als Versionsname und das tatsächlich verwendete Pi-Modell.
Bei einer Installation nach B1 ist die Paketarchitektur `armhf`. Bei `arm64`
bleibt das bestehende System zunächst erhalten: Die Laufzeit für die alten
32-Bit-Programme muss gesondert vorbereitet und geprüft werden. Beim untersuchten
Original-Logger handelt es sich um ein ARM-32-Bit-Programm mit dem Loader
`/lib/ld-linux-armhf.so.3`. Daraus folgt noch keine erfolgreiche Ausführung auf
einem konkreten 64-Bit-Pi. Kernel-Unterstützung, Bibliotheken und die übrigen
Programme sind vor der Installation einzeln zu prüfen. Noch keine fremden
Bibliotheken in Systemverzeichnisse kopieren.

Bei 1 GB RAM erscheint wegen Reservierungen weniger nutzbarer Speicher; kein
Desktop wird benötigt. Ein erfolgreicher Test auf dem Pi 4 ersetzt die spätere
Boot- und Empfangsabnahme auf dem Pi 3 nicht.

### B2a. Fernzugriff auf einen neu installierten Pi identifizieren

Wird eine bisher anderweitig verwendete IP-Adresse neu vergeben, gehört der
gespeicherte SSH-Hostschlüssel möglicherweise noch zum vorherigen Gerät.
Vor einer Passwortanmeldung den Fingerprint über die lokale Konsole oder eine
bereits vertrauenswürdig aufgebaute Sitzung auf dem neuen Pi ablesen:

```sh
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

Mit dem vom SSH-Client angezeigten Fingerprint vergleichen. Ein bloßer
`ssh-keyscan` über das Netzwerk bestätigt die Geräteidentität nicht.
Hostschlüsselwarnungen daher nicht durch Abschalten der Prüfung umgehen.
Persönliche Zugangsdaten gehören nicht in dieses Repository.

### B2b. ARM-32-Bit-Laufzeit auf bestehendem arm64-Trixie vorbereiten

Dieser Abschnitt gilt nur bei Paketarchitektur `arm64`. Alle Befehle führt der
Anwender auf dem neuen Pi aus. Nach jedem Schritt die Ausgabe prüfen, bevor der
nächste folgt. Die bestehende Wetterstation bleibt dabei unverändert.

Zuerst die Voraussetzungen prüfen:

```sh
dpkg --print-architecture
dpkg --print-foreign-architectures
grep '^CONFIG_COMPAT=' "/boot/config-$(uname -r)"
```

Beim vorbereiteten Pi 4 wurden `arm64`, die zusätzliche Architektur `armhf`
und `CONFIG_COMPAT=y` festgestellt. Fehlt die Kernel-Konfigurationsdatei,
ist das allein kein Beweis für fehlende Unterstützung; diese zunächst gesondert
prüfen. Fehlt nur die zusätzliche Architektur, diese eintragen und Paketlisten
aktualisieren:

```sh
sudo dpkg --add-architecture armhf
sudo apt-get update
```

Paketplan zunächst ohne Installation ansehen:

```sh
apt-get -s --no-install-recommends install libc6:armhf
```

Am 6. November 2026 zeigte die Simulation auf dem Pi 4 genau drei neue Pakete:
`gcc-14-base:armhf`, `libgcc-s1:armhf` und `libc6:armhf`, ohne Aktualisierungen
oder Entfernungen. Der eigene Paketplan kann abweichen und muss geprüft werden.
Bei unerwarteten Entfernungen oder Architekturkonflikten nicht fortfahren.

Nach Prüfung des Plans installieren:

```sh
sudo apt-get install --no-install-recommends libc6:armhf
/lib/ld-linux-armhf.so.3 --version
sudo dpkg --audit
```

In einer bereits geöffneten Root-Shell kann `sudo` entfallen. Erwartet werden
eine Versionsausgabe des 32-Bit-Loaders und keine Meldung von `dpkg --audit`.
Das prüft die grundlegende 32-Bit-Ausführung, noch nicht die Meteohub-Anwendung
oder deren vollständige Bibliotheksabhängigkeiten. Am 6. November 2026 hat der
Anwender die drei geplanten Pakete auf dem echten Pi 4 installiert. Der Loader
gab `GLIBC 2.41-12+rpt1+deb13u4` aus; `dpkg --audit` blieb ohne Ausgabe.

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

Beim Pi-4-Aufbau am 6. November 2026 wurden nach der Paketinstallation folgende
Werkzeugversionen vom Anwender geprüft: Git 2.47.3, Python 3.13.5, file 5.46 und
GNU readelf 2.44. Git brachte zusätzlich `git-man` und `liberror-perl` mit;
es wurden keine Pakete entfernt. Diese Versionsangaben dokumentieren den Test,
sie sind keine Aufforderung, später neuere Sicherheitsupdates zurückzusetzen.

**Auf dem Pi**, als normaler Benutzer, nicht dauerhaft in einer Root-Shell:

```sh
sudo apt-get install --no-install-recommends git python3 ca-certificates file binutils
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
anschließend zwei `PASS`-Zeilen des Prozesstests. Dieser verwendet Testdaten und
benötigt keine Wetterstation. `git rev-parse HEAD` notiert die genaue Version,
damit ein späterer Fehlerbericht zugeordnet werden kann.

**Auf echter Hardware bestätigt (6. November 2026):** Der Anwender klonte auf
dem Pi 4 den veröffentlichten Stand
`b2c30785411986e85272051ddad058fe3ef72960`. Alle 13 Dashboard-Tests, vier
Normalisierungstests und der damalige Plugin-Prozesstest bestanden. Dieser
Quellstand enthält noch nicht die spätere Korrektur für eine geschlossene
Logger-Pipe (`efff9ee539e7263d93c7dbba9683cc23f6f736e1`). Die damalige
Prüfung dieses Stands ist daher kein Nachweis für diesen zusätzlichen Fehlerfall.
Der anschließend auf demselben Pi angewendete Fix bestand auch den erweiterten
Prozesstest; neue Installationen beziehen ihn direkt aus GitHub (siehe unten).

`file` und `readelf` (aus `binutils`) werden anschließend zur Prüfung der
originalen ARM-Programme benötigt. Sie analysieren deren Format und
Bibliotheksanforderungen, ohne den Stationslogger starten zu müssen.
Ein GitHub-Klon enthält nur veröffentlichte Commits. Noch ausschließlich lokal
vorhandene Korrekturen sind darin nicht enthalten; vor einer Installation den
vorgesehenen Quellstand mit `git rev-parse HEAD` abgleichen.

Wer bisher als root gearbeitet hat, kann nach der Paketinstallation mit
`su - BENUTZERNAME` zum eigenen normalen Benutzer wechseln. Anschließend die
obigen Befehle ab `mkdir -p "$HOME/src"` ausführen. Existiert das Zielverzeichnis
`$HOME/src/meteohub` bereits, nicht löschen oder blind überschreiben, sondern
zunächst dessen Git-Status und Herkunft prüfen. Die Tests laufen ohne
Root-Rechte und ohne angeschlossene Wetterkonsole; sie starten keinen
produktiven Stationsdienst.

#### Aktualisierungen vollständig aus GitHub beziehen

Die Pipe-Korrektur ist Bestandteil dieses Repositorys (Commit `efff9ee`). Ein
separater Patchserver ist für die Installation nicht erforderlich. Neue Klone
enthalten den Fix; bei einem unveränderten bestehenden Klon aktualisieren:

```sh
cd "$HOME/src/meteohub"
git status --short
git pull --ff-only
PYTHONDONTWRITEBYTECODE=1 python3 test-feed-process.py
```

Bei lokalen Änderungen vor dem Pull deren Zweck prüfen und sie sichern.
Erwartet sind mit dem Fix zwei `PASS`-Zeilen, einschließlich
`closed reader exits promptly without false delivery or checkpoint`.
Am 6. November 2026 wurden beide Prozessprüfungen nach Anwendung derselben
Korrektur durch den Anwender auf dem echten Pi 4 erfolgreich ausgeführt.

**Nur für den frühen Pi-Testaufbau mit bereits manuell angewendetem Patch:**
Die Änderungen an den beiden Dateien vor dem Aktualisieren in einem lokalen
Git-Stash sichern. Nach dem Pull mit dem gesicherten Zustand vergleichen:

```sh
cd "$HOME/src/meteohub"
git stash push -m "Pipe-Fix vor GitHub-Abgleich" -- live_feed_plugin.py test-feed-process.py
git pull --ff-only
git diff --exit-code 'stash@{0}' HEAD -- live_feed_plugin.py test-feed-process.py
PYTHONDONTWRITEBYTECODE=1 python3 test-feed-process.py
```

Diese Folge setzt voraus, dass die beiden Dateien noch den manuell angewendeten
Patch als lokale Änderungen enthalten und der Stash tatsächlich neu angelegt
wird. Bei einem Fehler nicht mit dem nächsten Befehl fortfahren. Der Vergleich
muss ohne Ausgabe mit Exitcode 0 enden. Der Stash bleibt als Sicherung erhalten;
kein `stash pop`, denn der Fix ist bereits im aktualisierten Git-Stand enthalten.
Bei Abweichungen die Sicherung behalten und den Unterschied prüfen.

Der Anwender hat diesen Abgleich auf dem Pi 4 am 6. November 2026 bis zum
GitHub-Stand `c8a59b6` durchgeführt: Fast-forward erfolgreich, kein Unterschied
zwischen gesichertem Patch und übernommenem Fix, beide Prozessprüfungen
bestanden und Arbeitsverzeichnis sauber.

**Bis hier ist ein aktuelles Linux mit getesteten Projektquellen eingerichtet.
Noch keine Meteohub-Weboberfläche und noch kein Stationslogger.** Ein Browser-
Fehler auf Port 80 ist an diesem Punkt erwartbar. Es gibt hier noch keinen
universellen `install.sh`-Befehl.

### B5. Originalprogramme aus dem Herstellerimage vorbereiten

Für einen nachbaubaren Aufbau die Originalsoftware direkt vom Hersteller
beziehen. Ein privater Patch- oder Backupserver ist hierfür nicht erforderlich.
Die offizielle [Imageliste](https://wiki.meteohub.de/wiki/index.php/Images)
verlinkt das RPi-Image 5.0s. Am 6. November 2026 lieferte dessen HTTPS-Adresse
HTTP 200 und eine Archivgröße von 393194245 Bytes (rund 375 MiB).

**Auf dem neuen Pi als normaler Benutzer:** Entpacker installieren, Archiv in
einem privaten Verzeichnis außerhalb des Git-Klons speichern und zunächst nur
den Inhalt auflisten. Der Archivname darf dabei nicht schon eine aufbewahrte
andere Datei bezeichnen; bei einem bereits vorhandenen Download diesen zuerst
prüfen.

```sh
sudo apt-get install --no-install-recommends unrar-free
(
set -e
umask 077
mkdir -p "$HOME/meteohub-original"
cd "$HOME/meteohub-original"
wget -O mhrpi-v5.0s.rar https://www.meteohub.de/files/mhrpi-v5.0s.rar
sha256sum mhrpi-v5.0s.rar | tee mhrpi-v5.0s.rar.sha256
unrar-free -t mhrpi-v5.0s.rar
)
```

`unrar-free -t` listet den Inhalt; es ist kein vollständiger Entpack- oder
Integritätstest. Anhand der Ausgabe zunächst Namen und entpackte Größe des
Disk-Images feststellen. Die lokal erzeugte Prüfsumme dokumentiert den Download,
ersetzt aber keinen unabhängigen Hersteller-Prüfwert. Das Image wird später nur
zur Dateientnahme schreibgeschützt geöffnet, nicht über die Trixie-SD-Karte
geschrieben. Originalprogramme aus dem Image müssen vor ihrer Verwendung gegen
die im Labor untersuchte Version und deren Abhängigkeiten geprüft werden.

#### B5a. Image entpacken und Partitionstabelle lesen

Beim Download auf dem Pi 4 am 6. November 2026 meldete der Anwender diese
SHA256-Prüfsumme für das RAR-Archiv:

```text
eb0ba98acc31580de9416d1b3609ab38287aadb9af4edf1935edcbdff0ef11b2
```

Die Inhaltsliste enthielt genau `mhrpi-v5.0s.img` mit 1970274304 Bytes
(rund 1,97 GB). Das ist ein dokumentierter Downloadbefund, keine vom Hersteller
veröffentlichte Signatur oder Prüfsumme. Vor dem Entpacken ausreichend freien
Platz prüfen; zusätzlich zum Archiv werden etwa 2 GB für das Image benötigt.

Als normaler Benutzer ausführen:

```sh
(
set -e
umask 077
cd "$HOME/meteohub-original"
df -h .
test ! -e mhrpi-v5.0s.img
unrar-free -x mhrpi-v5.0s.rar
stat -c '%n: %s Bytes' mhrpi-v5.0s.img
file mhrpi-v5.0s.img
sudo fdisk -l mhrpi-v5.0s.img
)
```

Existiert das Image bereits, stoppt `test` den Block vor dem Entpacken. Eine
vorhandene Datei zunächst prüfen, statt sie zu überschreiben. Falls `fdisk`
fehlt, das Paket `fdisk` installieren und nur den letzten Befehl wiederholen.
`fdisk -l` liest die Partitionstabelle der angegebenen Image-Datei; es schreibt
weder diese Datei noch eine SD-Karte. Sektorgröße, Partitionsanfänge und Größen
aus der Ausgabe festhalten. Noch keine Partitionsnummer oder Mount-Offsets
annehmen. Das spätere Öffnen muss schreibgeschützt erfolgen.

#### B5b. Image schreibgeschützt als Loop-Gerät öffnen

Der Anwender bestätigte erfolgreiches Entpacken (`All OK`) und exakt
1970274304 Bytes. Die ausgelesene MBR-Partitionstabelle hat 512-Byte-Sektoren:

| Partition | Startsektor | Sektoren | Typ |
| --- | ---: | ---: | --- |
| 1 | 2048 | 102400 | FAT32, 50 MiB |
| 2 | 104448 | 3481600 | Linux |
| 3 | 3586048 | 262144 | Swap, 128 MiB |

Für dieses geprüfte Image ist Partition 2 der Kandidat für das Linux-Root-
Dateisystem. Der Partitionstyp allein sagt noch nicht, ob es beispielsweise
ext3 oder ext4 ist. Vor dem Mounten den Dateisystemtyp lesen:

```sh
(
set -e
umask 077
cd "$HOME/meteohub-original"
test ! -e image-loop.device
meteohub_loop=$(sudo losetup --find --show --read-only --partscan "$PWD/mhrpi-v5.0s.img")
printf '%s\n' "$meteohub_loop" > image-loop.device
sudo udevadm settle
sudo lsblk -o NAME,SIZE,RO,FSTYPE,MOUNTPOINTS "$meteohub_loop"
sudo blkid "${meteohub_loop}p2"
)
```

`image-loop.device` merkt sich das zugeteilte Gerät, etwa `/dev/loop0`. Die
Nummer nicht voraussetzen. Die Spalte `RO` muss für das Loop-Gerät und seine
Partitionen `1` zeigen. Dieser Schritt mountet noch kein Dateisystem und
aktiviert die Swap-Partition nicht. Existiert die Merkerdatei bereits, zunächst
das bestehende Mapping prüfen, statt ein weiteres anzulegen. Nach einem Reboot
kann die Merkerdatei veraltet sein; vor Wiederverwendung immer die Zuordnung
zur Image-Datei mit `sudo losetup --list` kontrollieren.

Zum späteren Rückbau zuerst eventuell eingehängte Image-Partitionen aushängen,
danach ausschließlich das überprüfte zugehörige Loop-Gerät mit
`sudo losetup --detach /dev/loopN` lösen (`loopN` durch die ermittelte Nummer
ersetzen). Erst anschließend die Merkerdatei entfernen. Kein `--detach-all`
verwenden. Der Anwender bestätigte anschließend `/dev/loop1` mit `RO=1` für
Gerät und alle drei Partitionen; Partition 2 ist ext3, UUID
`136bbacc-bdec-4347-823a-a3eb4178aa9e`. Diese Loop-Nummer gilt nur für diese
Sitzung, nicht für andere Installationen oder nach einem Reboot.

#### B5c. Linux-Partition ohne Journal-Wiederherstellung mounten

Zuerst die gespeicherte Gerätezuordnung und den Schreibschutz prüfen. Danach
die Image-Partition mit `ro,noload,nodev,nosuid,noexec` einhängen. `noload`
verhindert die Journal-Wiederherstellung; siehe die
[Kernel-Dokumentation](https://www.kernel.org/doc/html/latest/admin-guide/ext4.html#options).
Bei Hinweisen auf ein inkonsistentes Dateisystem nicht schreibbar remounten
oder das Originalimage reparieren, sondern den Befund zuerst klären.

```sh
(
set -e
cd "$HOME/meteohub-original"
meteohub_loop=$(cat image-loop.device)
test "$(sudo losetup --noheadings --raw --output BACK-FILE "$meteohub_loop")" = "$PWD/mhrpi-v5.0s.img"
test "$(sudo blockdev --getro "$meteohub_loop")" = 1
sudo mkdir -p /mnt/meteohub-original
if mountpoint -q /mnt/meteohub-original; then
  echo "STOP: Image-Verzeichnis ist bereits gemountet."
  exit 1
fi
test -z "$(ls -A /mnt/meteohub-original)"
sudo mount -t ext3 -o ro,noload,nodev,nosuid,noexec "${meteohub_loop}p2" /mnt/meteohub-original
findmnt /mnt/meteohub-original
sudo ls -ld /mnt/meteohub-original/home/meteohub /mnt/meteohub-original/srv/www
sudo file /mnt/meteohub-original/home/meteohub/loggerd
sudo readelf -h /mnt/meteohub-original/home/meteohub/loggerd
sudo readelf -l /mnt/meteohub-original/home/meteohub/loggerd | grep interpreter
sudo readelf -d /mnt/meteohub-original/home/meteohub/loggerd | grep NEEDED
)
```

Dies liest ELF-Metadaten; der Logger wird nicht gestartet. Bei abweichenden
Pfaden die Image-Verzeichnisse prüfen, nicht Dateien aus dem laufenden System
als Ersatz verwenden. Auf dem Pi 4 bestätigt: Mount `ro,nosuid,nodev,noexec`
mit `norecovery`, beide Anwendungsverzeichnisse vorhanden. Der Image-Logger ist
ELF32 ARM EABI5 mit Interpreter `/lib/ld-linux-armhf.so.3` und den direkten
Abhängigkeiten `libm.so.6` und `libc.so.6`. Seine Build-ID ist
`918ce211ae1010bd9eb24c3360ffeab8c4ebf3e0`; sie unterscheidet sich von der zuvor
untersuchten Stationskopie. Dieser Metadatenbefund ist noch kein Laufzeittest.
Zum späteren
Aushängen `sudo umount /mnt/meteohub-original` verwenden, dann das zugehörige
Loop-Gerät wie oben beschrieben lösen.

#### B5d. Programme und Symlinks vollständig in den Anwendungsverzeichnissen erfassen

Das Werkzeug `tools/inspect-original.py` liest unter `home/meteohub` und
`srv/www` die ELF-Metadaten aller regulären Binärdateien, deren Prüfsummen,
Dateianzahlen und Symlink-Ziele. Es folgt keinen Symlinks innerhalb dieser
Verzeichnisbäume und startet keine Image-Programme. Textkonfigurationen werden
nicht ausgegeben. Die Untersuchung umfasst weder sämtliche Systemprogramme
des Images noch die von Shellskripten dynamisch aufgerufenen Werkzeuge; deren
Prüfung folgt vor der eigentlichen Installation.

Als Benutzer auf dem Pi ausführen:

```sh
(
set -e
set -o pipefail
umask 077
cd "$HOME/src/meteohub"
git pull --ff-only
sudo python3 tools/inspect-original.py /mnt/meteohub-original |
  tee "$HOME/meteohub-original/original-inventory.txt"
)
```

Vor dem Aufruf muss das zuvor geprüfte Image weiterhin an diesem Mountpunkt
schreibgeschützt eingehängt sein. Bei einem zwischenzeitlichen Reboot den
Loop-/Mount-Aufbau erneut prüfen. Die Berichtdatei bleibt außerhalb von Git.
Am Ende wird die Anzahl der ELF-Dateien und Lesefehler ausgegeben. Ein Fehler
oder null gefundene Programme liefert einen Fehlerstatus. Das Werkzeug wurde
am Vorbereitungsrechner an der zuvor gesicherten Stationskopie geprüft:
39 ELF-Dateien, keine Fehler. Das Ergebnis des Herstellerimages auf dem Pi
steht noch aus und kann davon abweichen.

### B6. Noch offene native Installation und Abnahme

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
Erst nach dieser nativen Abnahme lässt sich B6 durch eine belastbare Folge von
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
