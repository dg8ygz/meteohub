# Meteohub von Anfang an auf einem Raspberry Pi einrichten

**Neu: [Installer und separates Dashboard-/SVG-Update](installer.md)** bündeln die
nachfolgend dokumentierten Vorbereitungsschritte. Vorhandene 5.1e-Verzeichnisse
werden geprüft und wiederverwendet. Produktionsabnahme und Autostart bleiben offen.


Stand: **7. November 2026**. Zielgeräte: **Raspberry Pi 3 Model B** und
**Raspberry Pi 4 Model B, auch die Variante mit 1 GB RAM**.

**Verbindlicher Zielstand für Weg B: Meteohub 5.1e.** Das Image 5.0s dient
als Quelle für die Grunddateien und für die ersten Verträglichkeitsprüfungen.
Vor Logger-Abnahme und produktivem Betrieb folgt zwingend das
[5.1e-Update in B5q](#b5q-zielversion-51e-vom-hersteller-beziehen).

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
39 ELF-Dateien, keine Fehler. Auch der Anwenderlauf auf dem Pi fand im
Herstellerimage 39 ELF-Dateien und keine Fehler. Dort wurden 68 reguläre
Dateien (2977089 Bytes) unter `home/meteohub` und 34 (1891614 Bytes) unter
`srv/www` erfasst.

#### B5e. Zusätzliche Bibliotheken und OpenSSL-Kompatibilität prüfen

Die Inventur des Images 5.0s ergab folgende zusätzliche Anforderungen:

| Programme | Direkte zusätzliche Anforderungen |
| --- | --- |
| `meteohub.cgi` | `libgcgi.so.0`, `libssl.so.1.0.0`, `libcrypto.so.1.0.0` |
| `meteonet`, `meteoschedule` | `libssl.so.1.0.0`, `libcrypto.so.1.0.0` |
| `meteometar` | `libssl.so.1.0.0` |
| Weitere native CGI-Programme | teilweise `libgcgi.so.0` |
| `hidlog`, `em1010`, `wsxxx`, `wsyyy` | je nach Programm alte USB-/FTDI-ABI |
| `lju3` | `liblabjackusb.so` |

Die USB-Helfer sind nicht alle für jede Wetterstation nötig. Die vorhandene
Station verwendet beispielsweise eine serielle Pluginquelle. Die endgültige
Hardwarekonfiguration muss vor Auswahl der dafür nötigen Helfer feststehen.

Im vorherigen Trixie-Labor wurden die OpenSSL-Abhängigkeiten ausgewählter
Programme auf OpenSSL 3 angepasst, nach Prüfung ihrer importierten Funktionen.
Wegen abweichender Binaries im Herstellerimage diesen Nachweis nicht ungeprüft
übertragen. Kein Symlink von `libssl.so.1.0.0` auf eine neue Bibliothek und keine
alten OpenSSL-Pakete über das Trixie-System installieren. Auch eine erfolgreiche
Auflösung aller Symbole allein ist noch kein vollständiger ABI-/Funktionstest.

Zunächst nur die betreffenden Funktionsimporte und die CGI-Bibliotheksdateien
anzeigen, danach den Paketplan für die moderne ARM-Laufzeit simulieren:

```sh
(
set -e
set -o pipefail
for name in home/meteohub/meteometar home/meteohub/meteonet \
  home/meteohub/meteoschedule srv/www/cgi-bin/meteohub.cgi; do
  printf '\nPROGRAMM: %s\n' "$name"
  readelf -W --dyn-syms "/mnt/meteohub-original/$name" |
    awk '/ UND / && /OPENSSL_|BIO_|EVP_|RSA_|PEM_|MD5|SSL_|CRYPTO_/'
done
sudo find /mnt/meteohub-original/usr/local/lib -maxdepth 1 -name 'libgcgi.so*' -ls
apt-get -s --no-install-recommends install libssl3t64:armhf python3-pyelftools
)
```

Dieser Schritt installiert noch keine Pakete und verändert keine Binaries.
`python3-pyelftools` ist ein Analysewerkzeug für die folgende ELF-Prüfung;
`libssl3t64:armhf` stellt die aktuelle 32-Bit-OpenSSL-Laufzeit bereit. Die
konkrete Paketauflösung und Funktionsliste müssen auf dem Ziel-Pi geprüft werden.

Auf dem Pi 4 bestätigte der Anwender am 6. November 2026:

- `meteometar`: keine Treffer im oben verwendeten Symbolfilter, trotz direkter
  `libssl.so.1.0.0`-Abhängigkeit. Daraus allein folgt nicht, dass sämtliche
  dynamischen Bibliothekszugriffe ausgeschlossen sind.
- `meteonet` und `meteoschedule`: jeweils `MD5@OPENSSL_1.0.0`.
- `meteohub.cgi`: 16 versionierte Funktionsimporte aus den BIO-, EVP-, PEM- und
  RSA-APIs. Diese passen zur bisher untersuchten Funktionsmenge; das ist noch
  kein Nachweis für die Laufzeitkompatibilität des neuen Programmbuilds.
- `usr/local/lib/libgcgi.so.0.0.0`: vorhanden, 111327 Bytes; die beiden
  Bibliothekssymlinks zeigen relativ auf diese Datei.
- Paketplan: fünf neue Pakete (`libatomic1:armhf`, `libzstd1:armhf`,
  `zlib1g:armhf`, `libssl3t64:armhf`, `python3-pyelftools`), keine
  Aktualisierungen oder Entfernungen. OpenSSL-Kandidat
  `3.5.7-1~deb13u3+rpt1`, pyelftools `0.32-1`. Keine zusätzlichen Serverdienste
  in diesem Paketplan.

Nach Prüfung dieses Plans die Pakete installieren und den Zustand prüfen:

```sh
sudo apt-get install --no-install-recommends libssl3t64:armhf python3-pyelftools
dpkg-query -W libssl3t64:armhf python3-pyelftools
python3 -c 'import elftools; print("pyelftools", elftools.__version__)'
sudo dpkg --audit
```

Erwartet sind installierte Paketversionen, eine erfolgreiche Python-
Importprüfung und ein leeres dpkg-Audit. Wenn der reale Paketplan unerwartet
abweicht, vor der Bestätigung neu prüfen. Der Anwender bestätigte die Installation
aller fünf Pakete, OpenSSL `3.5.7-1~deb13u3+rpt1`, pyelftools `0.32-1`, den
erfolgreichen Import (`pyelftools 0.32`) und ein leeres dpkg-Audit. Sie passt noch keine Originalprogramme
an, startet keinen Meteohub-Dienst und ersetzt keine Aktivierung. Eine spätere
ELF-Anpassung muss mit unverändertem Original und nachvollziehbaren Änderungen
in einer separaten Arbeitskopie erfolgen; Bibliotheksauflösung und tatsächliche
Funktionen sind danach getrennt zu testen.

Außerdem wichtig für die folgende Übernahme: Das Image erwartet Programme
unter `/home/meteohub`, das auf dem neuen Pi bereits das persönliche
Benutzerverzeichnis ist. Diesen Pfad nicht pauschal mit dem Image-Verzeichnis
überschreiben. Anwendung, persönliche Dateien, Datenpfade und Symlinks sind
vor dem Einrichten der Dienste getrennt zu behandeln.

#### B5f. Exportierte Funktionen der neuen Bibliothek abgleichen

Als Nächstes die installierte ARM-Bibliothek und die mitgelieferte CGI-
Bibliothek statisch untersuchen. Die folgende Liste umfasst die 17 verschiedenen
OpenSSL-Funktionsnamen aus B5e. Erwartet werden definierte Exporte mit
`OPENSSL_3.0.0`; fehlende oder anders versionierte Funktionen vor jeder Anpassung
klären. Die Ausgabe ist ein Symbolabgleich, kein Beleg für identische ABI oder
Semantik. Die Bibliotheken werden hierbei nicht geladen oder ausgeführt.

```sh
(
set -e
set -o pipefail
meteohub_crypto=/usr/lib/arm-linux-gnueabihf/libcrypto.so.3
meteohub_gcgi=/mnt/meteohub-original/usr/local/lib/libgcgi.so.0.0.0
test -f "$meteohub_crypto"
test -f "$meteohub_gcgi"
file -L "$meteohub_crypto" "$meteohub_gcgi"
readelf -W --dyn-syms "$meteohub_crypto" |
  awk '
  BEGIN {
    names = "MD5|BIO_ctrl|BIO_f_base64|BIO_free|BIO_free_all"
    names = names "|BIO_new|BIO_new_mem_buf|BIO_push|BIO_read"
    names = names "|BIO_s_mem|BIO_set_flags|BIO_write"
    names = names "|EVP_PKEY_free|EVP_PKEY_get1_RSA"
    names = names "|PEM_read_bio_PUBKEY|RSA_new|RSA_public_decrypt"
    pattern = "^(" names ")@"
  }
  $7 != "UND" && $8 ~ pattern {print}'
sha256sum "$meteohub_gcgi"
readelf -W -d "$meteohub_gcgi" |
  awk '/NEEDED|SONAME|RPATH|RUNPATH/'
readelf -W --version-info "$meteohub_gcgi"
)
```

Die Prüfung von `libgcgi` erfasst die konkrete Originaldatei samt Hash,
Abhängigkeiten und Versionsanforderungen für eine spätere private Übernahme.
Noch keine Bibliothek nach `/usr/lib` kopieren und keine Kompatibilitätssymlinks
im System anlegen. Der Anwender bestätigte alle 17 Exporte mit
`OPENSSL_3.0.0`. Die originale CGI-Bibliothek hat SHA256
`b8c22c56b978e7a66e050a1c0ff4aaf74dce95d79661a535b767e0cd80042ec6`,
SONAME `libgcgi.so.0`, benötigt nur `libm.so.6` und `libc.so.6` und fordert
von beiden `GLIBC_2.4` an. Beide untersuchten Bibliotheken sind ELF32 ARM.

#### B5g. Separate OpenSSL-3-Testkopien vorbereiten

Das Werkzeug `tools/stage-openssl3.py` akzeptiert ausschließlich die sechs
anhand der obigen Herstellerimage-Inventur festgelegten SHA256-Werte. Es legt
ein neues privates Verzeichnis an. Logger und CGI-Bibliothek werden unverändert
kopiert; bei den vier Programmen mit OpenSSL-Verweisen werden ausschließlich
die Bibliotheks-/Versionsnamen und zugehörigen ELF-Versionshashes angepasst.
Die Dateigröße und sämtliche ausführbaren ELF-Abschnitte bleiben unverändert.
Ein Manifest protokolliert Quell-/Zielhashes und jede Änderung mit Offset und
Bytes. Kein Image-Programm wird dabei ausgeführt, kein Dienst eingerichtet.

**Das ist ein experimenteller Anpassungsversuch für diese Binaries.**
OpenSSL garantiert keine allgemeine Binärkompatibilität über diesen
Versionssprung; siehe den
[OpenSSL-Migrationsleitfaden](https://docs.openssl.org/3.5/man7/ossl-guide-migration/).
Symbolnamen allein belegen weder identische Datenstrukturen noch Semantik.
Die späteren Tests müssen insbesondere CGI, Crypto-Aufrufe und Fehlerpfade
abdecken. Die Anpassung ersetzt keine gültige Aktivierung.

Als normaler Benutzer auf dem Ziel-Pi:

```sh
(
set -e
cd "$HOME/src/meteohub"
git pull --ff-only
PYTHONDONTWRITEBYTECODE=1 python3 tools/test-crypto-adaptation.py \
  /mnt/meteohub-original
python3 tools/stage-openssl3.py \
  /mnt/meteohub-original \
  "$HOME/meteohub-staging/5.0s-openssl3"
)
```

Die Tests benötigen separat beschaffte Originaldateien; solche Dateien sind
nicht im Repository enthalten. Lokaler Entwicklungsnachweis: drei Testmethoden
mit vier echten ARM-Binaries aus der früheren Stationskopie bestanden,
einschließlich unveränderter ausführbarer Abschnitte, Manifestabgleich,
unbekannter Importe, erneuter Anpassung, Hashfehler, Symlinks und belegtem
Zielverzeichnis. Diese Stationskopie unterscheidet sich vom Herstellerimage;
der eigentliche Import verweigerte sie erwartungsgemäß wegen Hashabweichung,
bevor ein Zielverzeichnis entstand. Der Anwender bestätigte anschließend auch
den nativen Lauf mit dem konkreten 5.0s-Image: drei Testmethoden bestanden,
sechs Dateien erfolgreich vorbereitet. Logger und `libgcgi` blieben bytegleich;
bei `meteometar` wurde ein Metadateneintrag geändert, bei `meteonet`,
`meteoschedule` und `meteohub.cgi` jeweils vier.

Das Zielverzeichnis muss neu sein. Bei einem Abbruch nicht blind löschen oder
denselben Kandidaten überschreiben; zuerst die Ursache und das Manifest prüfen.
Die Testkopien gehören nicht in Git und werden noch nicht nach `/home/meteohub`
oder `/srv/www` installiert. `libgcgi.so.0` ist eine private reguläre Kopie;
es werden keine globalen Bibliothekslinks oder Suchpfade geändert.

Nach erfolgreicher Vorbereitung die Auflösung der Bibliotheken und deren
Versionen mit dem ARM-Loader prüfen:

```sh
(
set -e
candidate="$HOME/meteohub-staging/5.0s-openssl3"
for name in loggerd meteometar meteonet meteoschedule meteohub.cgi; do
  printf '\nBIBLIOTHEKEN: %s\n' "$name"
  env -u LD_PRELOAD -u LD_AUDIT -u LD_LIBRARY_PATH \
    /lib/ld-linux-armhf.so.3 \
    --library-path "$candidate/lib:/usr/lib/arm-linux-gnueabihf" \
    --list "$candidate/bin/$name"
done
)
```

`--list` zeigt die dynamische Bibliotheksauflösung, ohne die Anwendung zu
starten. Fehlende Bibliotheken oder Symbolversionen stoppen diesen Block.
Dies ist weder eine vollständige Prüfung aller Funktionsaufrufe noch ein
Meteohub-Betriebstest. Diesen Schritt nicht durch einen direkten Programmstart
ersetzen: Betriebsverzeichnisse, Konfiguration, Rechte und Dienstisolation sind
erst noch einzurichten.

Der Anwender bestätigte die erfolgreiche Loader-Prüfung aller fünf Programme.
OpenSSL 3 und die weiteren ARM-Bibliotheken werden aus
`/usr/lib/arm-linux-gnueabihf` geladen; nur `libgcgi.so.0` kommt aus dem privaten
Kandidatenverzeichnis. Keine fehlenden Bibliotheken oder Versionsfehler in der
Ausgabe. Ein versehentlich mitkopierter Erklärungssatz verursachte lediglich
`Wenn: Kommando nicht gefunden`; die beiden Befehlsblöcke liefen erfolgreich.
Nur Inhalte der Befehlsblöcke ins Terminal kopieren.

#### B5h. Einmaliger CGI-Probelauf in einer abgeschirmten Umgebung

`tools/probe-cgi.py` prüft zuerst die Hashes der vorbereiteten Dateien gegen
ihr Manifest. Anschließend startet es über `sudo systemd-run` einen kurzlebigen
Testdienst unter der normalen Benutzer-ID. Das wirkliche Homeverzeichnis wird
ausgeblendet; nur der Kandidat erscheint schreibgeschützt unter
`/home/meteohub`. Netzwerk und Geräte werden getrennt, Host-Laufzeitsockets
ausgeblendet und Änderungen am Systemdateibaum gesperrt. Laufzeitlimit 30 s,
Speicherlimit 128 MiB, keine dauerhafte Unit und kein Autostart.

Ein harmloser Python-Prozess prüft zunächst in derselben Umgebung Benutzer-ID,
sichtbares Home, Schreibschutz, fehlende Host-Sockets/USB-Geräte und fehlende
ausgehende Route. Nur wenn diese Prüfung besteht, folgt ein CGI-Aufruf mit
`GET page=0` und `LD_BIND_NOW=1`. Letzteres erzwingt die sofortige Auflösung
der regulären dynamischen Funktionsverweise; tatsächlich benutzte Funktionen
und nachgeladene Bibliotheken müssen trotzdem gesondert geprüft werden.

```sh
(
set -e
cd "$HOME/src/meteohub"
git pull --ff-only
python3 tools/probe-cgi.py \
  "$HOME/meteohub-staging/5.0s-openssl3"
)
```

Als normaler Benutzer starten, nicht mit `sudo python3`. Das Werkzeug fragt
selbst nach sudo für die zeitlich begrenzten Dienste. Berichte entstehen in
einem neuen privaten `cgi-probe-*`-Verzeichnis neben dem Kandidaten: vollständige
CGI-Ausgabe, Fehlerausgabe, Isolationstest und (nach CGI-Ausführung) Ergebnis.
Ein Fehler im Isolationstest verhindert den CGI-Aufruf. Ein Prozessfehler oder
Timeout ist ein Diagnosebefund, kein bestandener Funktionstest.

Hier fehlen absichtlich noch die Anwendungs-Konfiguration und Webressourcen.
Eine Meldung über fehlende Dateien oder Aktivierung kann daher auftreten. Es
wird keine Lizenz angenommen, keine Hardwareidentität ersetzt und noch kein
Logger gestartet. Der GET-Probelauf allein testet insbesondere nicht sämtliche
RSA-/BIO-/MD5-Pfade, Archivfunktionen oder Exportziele.

Entwicklungsnachweis: Die tatsächliche systemd-Isolationsprüfung lief auf dem
x86-Vorbereitungsrechner mit systemd 257 erfolgreich. Dabei wurde ein Konflikt
mit `InaccessiblePaths=/run` gefunden und vor Veröffentlichung durch eine
leere schreibgeschützte `/run`-Ansicht ersetzt. Die verwendeten Mechanismen sind in
[systemd.exec](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html)
und [systemd-run](https://www.freedesktop.org/software/systemd/man/latest/systemd-run.html)
beschrieben.

Der Anwender bestätigte anschließend auf dem Pi:

- Isolationstest erfolgreich, Exit 0, Laufzeit 209 ms.
- ARM-CGI ausgeführt, 9142 Bytes HTML einschließlich `Content-Type` und
  Lizenzseite erzeugt; Exit 1, Laufzeit 425 ms. Kein Loader-/Symbolfehler oder
  Absturz in der gezeigten Ausgabe. Das ist ein erfolgreicher Startnachweis,
  aber noch keine bestandene Anwendungsabnahme.
- Fehlend gemeldet: `/etc/network/interfaces`, `/data`, `/etc/thttpd.conf`,
  `/opt/etc/ntp/ntp.conf`, `/etc/samba/smb.conf`, die Anwendungskonfiguration
  `/home/meteohub/meteohub.conf` und Lizenztext-Ressourcen.
- `/proc/net/route` ist durch `ProcSubset=pid` absichtlich ausgeblendet; außerdem
  hat der Test sein eigenes Netz ohne externe Route. `No gateway found` ist
  hier keine Diagnose der tatsächlichen Pi-Netzverbindung.
- Das CGI kündigt das Erzeugen einer Standardkonfiguration an, meldet danach
  aber einen Dateifehler. Der Kandidat ist schreibgeschützt; eine erfolgreiche
  Konfigurationserzeugung ist damit nicht nachgewiesen.

#### B5i. Ressourcen für eine eigene Anwendungsumgebung erfassen

Als nächstes die im Herstellerimage vorhandenen Pfade erfassen. Das bestehende
Inventurwerkzeug unterstützt dazu `--runtime-files`: Es zeigt ausschließlich
Dateitypen, Größen, Rechte, Linkziele und Lizenzdateinamen. Konfigurationsinhalte,
Kennwörter und Aktivierungswerte werden nicht gelesen oder ausgegeben.
Auch Symlinks in übergeordneten Verzeichnissen werden nicht verfolgt, damit
ein absoluter Link im Image nicht versehentlich auf Dateien des neuen Pi führt.

```sh
(
set -e
set -o pipefail
umask 077
cd "$HOME/src/meteohub"
git pull --ff-only
findmnt /mnt/meteohub-original
sudo python3 tools/inspect-original.py --runtime-files \
  /mnt/meteohub-original |
  tee "$HOME/meteohub-original/runtime-files.txt"
)
```

Der ursprüngliche Mount muss weiterhin schreibgeschützt sein. `MISSING` ist
bei dieser Bestandsaufnahme ein Befund, keine Aufforderung, eine Datei im
laufenden System anzulegen. `SYMLINK ... [not followed]` bedeutet, dass die
angezeigte Zielstruktur separat innerhalb des Images aufgelöst werden muss.
Zugriffsfehler werden als `ERROR` mit Fehlerstatus gemeldet.

Die nächste Testumgebung benötigt eigene beschreibbare Konfigurations- und
Datenverzeichnisse sowie die passenden Herstellertexte/Webressourcen.
Alte Netzwerk-, NTP-, Samba- oder thttpd-Dateien dürfen dafür nicht über die
Host-Konfiguration kopiert werden. Etwaige Kompatibilitätsdateien gehören nur
in die getrennte Anwendungssicht. Lizenztexte und eine spätere bewusste Annahme
der Bedingungen werden von Aktivierung und Hardwarebindung unterschieden;
vorhandene Annahmemarker aus einer anderen Installation werden nicht übernommen.
Die Bestandsaufnahme auf dem Ziel-Pi ist bestätigt: Originalimage weiterhin
ext3 `ro,nosuid,nodev,noexec,norecovery`; keine Lesefehler. Die Anwendungskonfiguration
ist 65536 Bytes groß, `interfaces` 703 Bytes, `thttpd.conf` 82 Bytes und
`smb.conf` 384 Bytes. `/data` ist ein echtes Verzeichnis, `/root/data` fehlt.
Vorhanden sind die drei Lizenztexte `meteohub-license-5.txt` (7026 Bytes),
`meteohub-license.txt` (6151 Bytes) und `weather-display-live-license.txt`
(6050 Bytes). Es wurden keine `.lic`-Annahmemarker aufgelistet.

Die Links müssen korrekt eingeordnet werden: `opt/etc/ntp/ntp.conf` verweist
absolut auf `/etc/ntp.conf`; `var/run` auf `/run`. `opt/share -> ../usr/share`
bezieht sich relativ auf **`/opt/usr/share`** im Image, nicht auf das
Host-Verzeichnis `/usr/share`. Die neue Testumgebung verwendet bewusst die
aktuellen Trixie-Zeitzonendateien statt dieser alten Linkstruktur.

#### B5j. Eigenes Test-Root mit Konfiguration, Datenordnern und Ressourcen

Das neue Werkzeug `tools/stage-runtime.py` liest zunächst alle benötigten
Dateien ein und prüft die Original-Binary-Hashes sowie das vorhandene
Kandidatenmanifest. Erst dann erzeugt es ein neues Verzeichnis
`$HOME/meteohub-staging/5.0s-runtime`. Darin liegt ein eigener `root`-Baum:

- Originale 64-KiB-Anwendungskonfiguration und drei Lizenztexte unter
  `root/home/meteohub`. Keine Aktivierungsschlüssel und keine Annahmemarker.
- Leere Ordner `root/data/{weather,graphs,export,myweb,log}`. Es werden keine
  vorhandenen Stationsarchive kopiert oder als neue Messwerte ausgegeben.
- Ausgewählte alte Netzwerk-/thttpd-/NTP-/Samba-Dateien unter `root/etc`, nur
  für die kompatible Dateiansicht im isolierten CGI-Test. Sie repräsentieren
  **nicht die tatsächliche Netz- oder Dienstkonfiguration des neuen Pi**.
- Statische HTML-/JS-/CSS-/Bild-/Textressourcen aus dem Hersteller-Webroot;
  keine alten `.cgi`, Shellskripte, `.htpasswd`, Symlinks oder Flash-Dateien.
- Kleine generierte Benutzer-/Gruppendateien ohne Passwörter und die aktuelle
  Host-Zeitzone. Trixies `/usr` und SSL-Konfiguration werden erst im Testdienst
  schreibgeschützt eingebunden, nicht als altes Betriebssystem kopiert.

Als normaler Benutzer ausführen; der Probelauf fragt selbst nach sudo:

```sh
(
set -e
cd "$HOME/src/meteohub"
git pull --ff-only
python3 tools/stage-runtime.py \
  /mnt/meteohub-original \
  "$HOME/meteohub-staging/5.0s-openssl3" \
  "$HOME/meteohub-staging/5.0s-runtime"
python3 tools/probe-cgi.py \
  "$HOME/meteohub-staging/5.0s-openssl3" \
  --runtime "$HOME/meteohub-staging/5.0s-runtime"
)
```

Das Ziel muss neu sein. Bei einem bereits vorhandenen Runtime-Verzeichnis
zunächst dessen Stand prüfen; nicht blind löschen und den Import wiederholen.
Ein erneuter CGI-Test benötigt nur den zweiten Python-Aufruf. Vor jedem Lauf
wird die Anwendungskonfiguration als `meteohub.conf.before` im privaten
Berichtverzeichnis gesichert. Das Runtime-Manifest dokumentiert die beim Import
gelesenen Dateien mit SHA256; die Anwendungskonfiguration darf sich im Test
anschließend ändern. Die Originaldatei im Image bleibt unverändert.

`probe-cgi.py --runtime` setzt systemds `RootDirectory` auf diesen privaten
Baum. `ProtectSystem=strict` hält ihn grundsätzlich schreibgeschützt;
`ReadWritePaths=+/home/meteohub +/data` erlaubt nur die vorgesehenen dauerhaften
Schreibbereiche innerhalb dieses Roots. Binärdateien und `libgcgi` werden
zusätzlich schreibgeschützt eingebunden. Private temporäre Verzeichnisse bleiben
für normale Programmarbeit verfügbar. Root-Rechte, USB-Zugriff, ausgehendes Netz
und Host-Laufzeitsockets werden weiterhin nicht an das CGI gegeben.

Die vorgeschaltete Isolationsprüfung testet jetzt zusätzlich echte Schreibzugriffe
in die privaten Verzeichnisse, Schreibschutz der Netzwerk-Testdatei sowie
Vorhandensein von NTP-Datei, Zeitzonen und Lizenztext. Erst danach wird wie zuvor
genau `GET page=0` ausgeführt. Es werden keine Bedingungen automatisch angenommen,
kein Webserver gestartet und keine Stationsaufnahme eingerichtet. Die fehlende
Route bleibt wegen der Isolation erwartbar. Weitere Anwendungsfehler werden
anhand der vollständigen Ausgabe getrennt bearbeitet.

Entwicklungsnachweis: `python3 tools/test-runtime.py --isolation` bestand lokal
unter systemd 257 mit drei Tests einschließlich eines tatsächlich gestarteten
unprivilegierten Testdienstes. Geprüft wurden Dateiauswahl, Ausschluss von
Passwort-/CGI-/Annahmedateien und Links, abweichende Konfigurationsgröße,
Verweigerung eines vorhandenen Ziels sowie die tatsächlichen Schreib- und
Isolationsgrenzen. Ohne `--isolation` laufen die beiden Dateitests ohne root;
der systemd-Test wird dann explizit übersprungen. Alle Fixtures sind synthetisch,
keine proprietären Dateien gehören zu den Tests. Der ARM-CGI-Lauf mit dem
Hersteller-Konfigurationsbestand wurde danach auf dem Ziel-Pi ausgeführt:
22 Dateien übernommen, Isolation einschließlich privater Schreibbereiche
bestanden (262 ms). Das CGI erzeugte 15780 Bytes einschließlich der tatsächlichen
Lizenztexte (209 ms), Exit 1. Die vorherigen Fehler für Anwendungskonfiguration,
`/data`, thttpd, NTP, Samba und Lizenztexte erschienen nicht mehr in der gezeigten
Ausgabe. Offen blieben eine fehlende private `/etc/resolv.conf`, die ausgeblendete
Routingtabelle und erwartungsgemäß keine Wetterstation/kein Gateway im Test.
Eine vollständige Anwendungsabnahme ist das weiterhin nicht.

#### B5k. Private Resolver-Datei ergänzen und isolierte Routingtabelle lesen

Neu erzeugte Runtime-Verzeichnisse enthalten jetzt bereits eine minimale
`etc/resolv.conf`. Für den oben erprobten älteren Stand ergänzt der folgende
Aufruf **nur diese fehlende Datei im privaten Runtime-Baum**. Eine vorhandene
abweichende Datei oder ein Symlink wird nicht überschrieben. Die
Anwendungskonfiguration wird dabei nicht zurückgesetzt.

```sh
(
set -e
cd "$HOME/src/meteohub"
git pull --ff-only
python3 tools/stage-runtime.py --ensure-resolver \
  "$HOME/meteohub-staging/5.0s-runtime"
python3 tools/probe-cgi.py \
  "$HOME/meteohub-staging/5.0s-openssl3" \
  --runtime "$HOME/meteohub-staging/5.0s-runtime"
)
```

Die Datei verwendet `127.0.0.1` mit kurzem Timeout als ausdrücklich markierten
Testplatzhalter. Es wird kein DNS-Dienst gestartet und kein externer DNS-Zugriff
freigegeben. Diese Datei ist keine Empfehlung für die produktive DNS-Konfiguration.
Die echte `/etc/resolv.conf` des Pi bleibt unverändert.

Im Runtime-Modus blendet der Probelauf die nicht-prozessbezogenen `/proc`-
Einträge nicht mehr aus. Dadurch kann das CGI `/proc/net/route` lesen, jedoch
nur die Routingtabelle seines weiterhin getrennten Netzwerk-Namensraums.
Die Isolationsprüfung verlangt ausdrücklich eine lesbare **leere** Routingtabelle
und prüft weiter, dass keine ausgehende Route existiert. Ein fehlendes Gateway
ist daher weiterhin erwartbar und wird nicht durch eine erfundene Route kaschiert.
`ProtectProc=invisible`, Geräteabschirmung, private Root-Ansicht und die übrigen
Schutzmaßnahmen bleiben aktiv. Der erste Probelauf ohne `--runtime` behält seine
bisherige eingeschränkte `/proc`-Ansicht.

Vier lokale Tests einschließlich tatsächlichem systemd-Testdienst bestanden:
Resolver-Ergänzung/wiederholter Aufruf, Erhalt abweichender Dateien,
Symlink-Verweigerung, unveränderte Anwendungskonfiguration sowie lesbare leere
Routingtabelle und bestehende Isolationsgrenzen. Die Ziel-Pi-Wiederholung dieses
Schrittes ist nun bestätigt: Resolver-Datei ergänzt, gesamte Isolation bestanden
(269 ms). Das CGI erzeugte 15945 Bytes (196 ms) und zeigte die Lizenztexte ohne
die vorherigen Dateifehler. Die CGI-Fehlerausgabe selbst enthielt keine Meldung;
systemd meldete weiterhin Exit 1. Dieser Rückgabewert ist noch nicht abschließend
erklärt und wird nicht als erfolgreiche Vollabnahme gewertet.

Statt der fehlenden Routingdatei zeigt die Seite nun eine Warnung über eine
nicht korrekt konfigurierte Netzwerkschnittstelle mit Hinweis auf die historische
Fallback-IP `192.168.1.77`. Das CGI sieht hier die Original-Konfigurationskopie
und sein isoliertes Netz. Die Warnung belegt keine Fehlkonfiguration der echten
Pi-Adresse. Weder die Host-IP ändern noch eine künstliche Default-Route in den
Test einbauen, um die Warnung zu unterdrücken. Die Lizenzbedingungen werden
durch den GET-Aufruf weiterhin nicht angenommen; das erfolgt später bewusst
durch den Anwender in der Oberfläche.

#### B5l. Paketplan für die Browser-Testoberfläche prüfen

Der nächste Schritt ist eine eigene Browser-Testoberfläche für dieselbe private
Anwendungsumgebung. Dafür ist lighttpd vorgesehen; das Paket unterstützt CGI,
siehe [Debians Paketbeschreibung](https://packages.debian.org/trixie/lighttpd).
`apache2-utils` liefert das Werkzeug `htpasswd` für einen separat gewählten
Webzugang, installiert selbst aber keinen Apache-Server. `curl` dient den
HTTP- und Authentifizierungsprüfungen. Keine alten Webkennwörter übernehmen.

Zunächst nur den Paketplan und bereits belegte TCP-Ports erfassen:

```sh
(
set -e
apt-cache policy lighttpd apache2-utils curl
apt-get -s --no-install-recommends install lighttpd apache2-utils curl
sudo ss -ltnp
)
```

Dies installiert noch nichts und verändert keine Dienste. Der reale Plan muss
auf zusätzliche Abhängigkeiten, Aktualisierungen, Entfernungen und Platzbedarf
geprüft werden. Vor der tatsächlichen Installation ist ein ungewollter Start
des Distributions-Webservers zu behandeln; die Testoberfläche erhält eine eigene
Konfiguration und bleibt von den alten Netzwerk-/Dienstdateien getrennt.
Die vorgesehene erste Erreichbarkeit ist über Loopback und SSH-Portweiterleitung;
ein Aufruf im Browser sowie Zugangsschutz, CGI-GET/POST und die bewusste Annahme
der Bedingungen sind noch zu prüfen. Eine produktive Freigabe oder ein Zugriff
auf die USB-Wetterstation ist damit noch nicht verbunden.

Der Anwender bestätigte folgenden Plan auf dem Pi: vier neue Pakete
`lighttpd` (1.4.79-2), `apache2-utils` (2.4.69-1~deb13u1), `libapr1t64`
(1.7.5-1) und `libaprutil1t64` (1.6.3-3+deb13u1). `curl`
(8.14.1-2+deb13u7) ist bereits aktuell. Keine Aktualisierungen oder Entfernungen.
Die beiden APR-Bibliotheken werden für `apache2-utils` benötigt. PHP und die
zusätzlich empfohlenen lighttpd-Module gehören nicht zum geprüften Plan.
Die Portprüfung zeigte ausschließlich SSH auf TCP 22, IPv4 und IPv6.

#### B5m. Webwerkzeuge installieren, Standarddienste gesperrt halten

Vor der Installation die mitgelieferten Standard-Units gezielt maskieren.
Neben `lighttpd.service` enthält das Paket einen Wartungsdienst mit Timer.
Die geprüften ARM64-Installationsskripte von lighttpd 1.4.79-2 verwenden
`invoke-rc.d --skip-systemd-native` und `deb-systemd-invoke`; die von Hand
angelegten systemd-Maskierungen werden durch `deb-systemd-helper unmask` nicht
aufgehoben, solange sie nicht von diesem Helper selbst verwaltet wurden.
Auf dem neu aufgebauten Pi ist lighttpd bisher nicht installiert.

```sh
(
set -e
sudo systemctl mask lighttpd.service \
  lighttpd-maint.service lighttpd-maint.timer

sudo apt-get install --no-install-recommends \
  lighttpd apache2-utils curl

sudo dpkg --audit
/usr/sbin/lighttpd -v
command -v htpasswd
systemctl show lighttpd.service lighttpd-maint.service \
  lighttpd-maint.timer -p Id -p LoadState -p ActiveState
sudo ss -ltnp
)
```

Beim Maskieren noch nicht installierter Units kann systemd darauf hinweisen,
dass die Unit noch nicht existiert, und legt trotzdem die `/dev/null`-Links an.
Ein anderer Fehler, insbesondere eine bereits vorhandene eigene Unit-Datei,
ist vor der Paketinstallation zu klären; nicht mit `--force` überschreiben.
APT vor Bestätigung erneut gegen den obigen Paketplan prüfen. Keine
unangeforderten automatischen Paketentfernungen ausführen.

Erwartet: leeres dpkg-Audit, lighttpd-Versionsausgabe und ein vorhandenes
`htpasswd`, alle drei Units `LoadState=masked`, `ActiveState=inactive`,
weiterhin kein Web-Listener. Die Installation kann Hinweise ausgeben, dass die
maskierten Units nicht aktiviert oder gestartet werden; das ist hier beabsichtigt.
Den tatsächlichen Paketstatus und die Listener trotzdem separat prüfen.

Die Maskierungen bleiben für diese Installation bestehen, weil die eigene
Testoberfläche später andere Unit-Namen verwendet. Sie gelten nur für die drei
genannten Units; weder SSH noch andere Dienstneustarts werden unterdrückt.
Ein späterer bewusster Wechsel auf den Distributions-Standarddienst kann sie
mit `sudo systemctl unmask lighttpd.service lighttpd-maint.service lighttpd-maint.timer`
entfernen; vorher muss dessen Konfiguration geprüft werden. Das Entsperren
gehört **nicht** zum nächsten Testschritt. Installation und Nachprüfung auf dem
Ziel-Pi sind bestätigt: alle vier Pakete eingerichtet, leeres dpkg-Audit,
`lighttpd/1.4.79`, `/usr/bin/htpasswd` vorhanden, alle drei Units maskiert/inaktiv
und weiterhin ausschließlich SSH als TCP-Listener. Die ausgegebenen
`Failed to preset unit`-Meldungen entstanden durch die vorgesehenen Maskierungen;
die Paketinstallation selbst wurde abgeschlossen.

#### B5n. Passwortgeschützte Browser-Testoberfläche über SSH

`tools/web-test.py` verwendet die bereits geprüften Kandidaten und den privaten
Runtime-Baum. Die Vorbereitung fragt interaktiv zweimal nach einem **neuen
Webpasswort** für den Benutzernamen `meteohub`. Das ist unabhängig vom SSH-Konto.
Das Passwort nicht in Befehlsargumente, Git oder Chat schreiben. Nur sein
bcrypt-Hash wird privat unter `root/opt/meteohub-web/users.htpasswd` gespeichert.
Eine bereits vorhandene Vorbereitung wird nicht überschrieben.

```sh
(
set -e
cd "$HOME/src/meteohub"
git pull --ff-only
python3 tools/web-test.py prepare \
  "$HOME/meteohub-staging/5.0s-openssl3" \
  "$HOME/meteohub-staging/5.0s-runtime"
python3 tools/web-test.py start \
  "$HOME/meteohub-staging/5.0s-openssl3" \
  "$HOME/meteohub-staging/5.0s-runtime"
)
```

`start` prüft zuerst Hashes, Runtime-Eigentümer, Passwortdateirechte, unveränderte
Webkonfiguration und die tatsächliche Isolation. Danach folgen lighttpds
Konfigurations-/Modulprüfung und eine private Sicherung der aktuellen
Meteohub-Konfiguration. Erst dann wird die temporäre Socket-/Dienstkombination
`meteohub-web-test` gestartet. Der abschließende lokale Abruf **ohne** Anmeldung
muss HTTP 401 liefern; sonst stoppt das Werkzeug Socket und Dienst wieder.

Nur systemd lauscht auf **127.0.0.1:18090** und reicht den bereits geöffneten
Socket an lighttpd weiter. Der Webprozess läuft als normaler Benutzer im
privaten Root und weiterhin in seinem isolierten Netz ohne ausgehende Route.
Die Browser-Verbindung funktioniert über diesen übergebenen Socket; dafür wird
das Netz des CGI nicht mit dem Host-Netz zusammengelegt. Programme/Bibliotheken
bleiben schreibgeschützt; Schreibzugriff besteht nur auf die privaten
Anwendungs-/Datenverzeichnisse und temporäre Dateien. Authentifizierung gilt
auch für statische Ressourcen. Der CGI-Launcher führt ausschließlich das
vorbereitete `meteohub.cgi` aus und ergänzt beim leeren GET `page=0`.

Nach `READY` auf dem **eigenen PC**, nicht in der Pi-Shell, eine zweite
SSH-Verbindung mit lokaler Portweiterleitung öffnen. Beispiel bei funktionierender
Namensauflösung (sonst `raspberrypi.local` durch die bekannte Pi-IP ersetzen):

```sh
ssh -o ExitOnForwardFailure=yes -N \
  -L 18090:127.0.0.1:18090 meteohub@raspberrypi.local
```

Dieses Terminal offen lassen. Bei PuTTY stattdessen unter
**Connection → SSH → Tunnels** `Source port: 18090`,
`Destination: 127.0.0.1:18090`, Typ **Local**, dann **Add** und **Apply** in der
bestehenden Sitzung einstellen. Keine Freigabe lokaler Ports für andere Hosts
aktivieren. Der Hostschlüssel muss dem vorher geprüften Pi entsprechen.

Im Browser auf dem PC öffnen:

```text
http://127.0.0.1:18090/cgi-bin/meteohub.cgi
```

Mit Webbenutzer `meteohub` und dem gerade gewählten **Webpasswort** anmelden.
Den SSH-Tunnel mit dem SSH-Kennwort beziehungsweise Schlüssel authentifizieren,
nicht mit diesem Webpasswort. HTTP bleibt innerhalb der lokalen Endpunkte;
der Transport zwischen PC und Pi läuft durch SSH.

Die Bedingungen in der Oberfläche selbst lesen und nur bei Einverständnis
bestätigen. Das Werkzeug nimmt nichts automatisch an und importiert keine
Aktivierung. Diese erste Testoberfläche ist keine produktive Wetterstation.
Insbesondere spiegeln die alten Netzwerk-/NTP-/Samba-Einstellungsseiten nicht
die tatsächlichen Hostdienste wider; Änderungen dort nicht als Hostkonfiguration
ausgeben. Der bisherige Netzwerkhinweis im isolierten Test kann weiterhin
erscheinen. Stationsaufnahme, Datenübernahme, Aktivierung und dauerhafter
Bootbetrieb bleiben eigene Abnahmeschritte.

Stoppen auf dem Pi:

```sh
sudo systemctl stop meteohub-web-test.socket meteohub-web-test.service
```

Die Units sind temporär, nicht für Boot aktiviert. Sie laufen bis zum Stoppen
oder Neustart; es gilt kein 30-Sekunden-Limit wie beim einzelnen CGI-Probelauf.
Zum erneuten Start nur `web-test.py start` mit denselben Pfaden ausführen, nicht
die Passwort-/Konfigurationsvorbereitung wiederholen. Bei einem Startfehler:

```sh
sudo systemctl status meteohub-web-test.socket meteohub-web-test.service --no-pager
sudo journalctl -u meteohub-web-test.service -n 60 --no-pager
```

Entwicklungsnachweis: Zehn tatsächliche HTTP-Fälle mit lighttpd 1.4.79 auf x86
bestanden: fehlende/falsche Anmeldung, authentifizierte GETs inklusive leerer
Query, POST, statische Datei sowie Abweisung anderer CGI-/privater Pfade.
Das synthetische CGI liefert absichtlich Exit 1 nach gültigen CGI-Headern; die
HTTP-Antwort wird trotzdem vollständig mit Status 200 übertragen. Das erklärt
noch nicht den internen Rückgabewert des proprietären CGI, zeigt aber, dass
dieser allein den Browserbetrieb nicht verhindern muss. Socket-Aktivierung
und getrenntes Netz wurden mit einem tatsächlich gestarteten Testdienst geprüft.
Die optionale Wiederholung heißt `sudo python3 tools/test-web.py`; sie verwendet
zufällige lokale Testports, temporäre Testkennwörter und keine Original-Binaries.
Der erste echte ARM-Browserlauf wurde am 06.11.2026 um 22:48 CET vom Betreiber
bestätigt: Die authentifizierte Oberfläche zeigte „System Information“,
Meteohub 5.0s Build 180 und den aktuellen Kernel. Dies belegt die Ausgabe
dieser CGI-Seite, noch nicht Stationsaufnahme, Archivierung oder Aktivierung.

Die Seite meldete fehlende PID-Dateien für loggerd, Dropbear und Samba sowie
inaktive Netzwerkeinstellungen. Im isolierten Test sind diese Dienste nicht
gestartet; der tatsächliche SSH-Zugang des Pi läuft außerhalb dieser Umgebung.
Keine künstlichen PID-Dateien anlegen und nicht anhand dieser alten Statusseite
Hostdienste nachinstallieren. Die Anzeige „x86“ widerspricht den nachgewiesenen
ARM-Binaries; ihre Hardwareerkennung ist noch zu untersuchen. Eine leere
System-ID mit dem Zusatz „activated“ ist kein belastbarer Aktivierungsnachweis.

Für den späteren Hardwarewechsel beschreibt der Hersteller einen
[Lizenztransfer](https://wiki.meteohub.de/wiki/index.php/Transfer).
Laut dieser Anleitung wird dabei der alte Aktivierungscode gesperrt. Deshalb
erst bei vorbereitetem Umstieg durchführen, nicht während der parallelen
Erprobung. Zuvor muss eine korrekte, stabile System-ID des Zielgeräts vorliegen.
Ob der Transferdienst aktuell erfolgreich arbeitet, ist noch nicht getestet;
die Dokumentation allein ist kein Nachweis einer erfolgreichen Übertragung.

#### B5o. Vorhandene Station als TCP-Messwertquelle prüfen

Wenn die vorhandene Station bereits einen TCP-Kopierstrom der Plugin-Daten
bereitstellt, kann der neue Pi diesen mitlesen. Im geprüften Aufbau war dies
Port **5500**, mit Zeilen wie `wind0 70 67 30` und `data0 600`.
Den Port am eigenen Quellsystem prüfen; nicht beliebige Stations- oder
Steuerports anschreiben. Der neue Zubringer sendet keinerlei Anwendungsdaten
oder Befehle an diesen Port und öffnet keine serielle Schnittstelle.

Auf dem neuen Pi als normaler Benutzer:

```sh
(
set -e
umask 077
cd "$HOME/src/meteohub"
git pull --ff-only
PYTHONDONTWRITEBYTECODE=1 python3 tools/test-tcp-feed.py
read -r -p 'IP oder DNS-Name der bisherigen Station: ' source_host
python3 tools/tcp-feed.py \
  --host "$source_host" --port 5500 --duration 90 \
  --output "$HOME/meteohub-staging/tcp-feed/feed.json"
)
```

Der Empfang läuft 90 Sekunden und endet dann. Die Ausgabe nennt Datensätze je
Sensor, zuletzt empfangene Werte, verworfene Formate und Verbindungsanzahl.
Ein Exitcode 2 bedeutet, dass kein gültiger Datensatz empfangen wurde.
Ein seltener sendender Sensor muss innerhalb dieses kurzen Fensters nicht
auftreten; das ist kein Nachweis für seinen Ausfall.

`feed.json` enthält höchstens die letzten 300 formal gültigen Plugin-Zeilen;
`feed.status.json` enthält die Abschlussstatistik. Beide Dateien bleiben privat.
Der Zubringer überschreibt einen vorhandenen Snapshot beim Start zunächst mit
einem leeren Stand, damit keine alten Messwerte wieder eingespielt werden.
Angebrochene Zeilen werden bei Verbindungsabbruch verworfen, nicht mit einer
späteren Verbindung zusammengefügt. Ein Wiederanlauf erfolgt nach fünf Sekunden;
nach 60 Sekunden ohne Bytes wird die Verbindung neu aufgebaut.

Der TCP-Kopierstrom enthält **keine Quellzeitstempel**. Die vorangestellten
UTC-Zeitstempel sind Empfangszeiten auf dem neuen Pi, keine nachgewiesenen
Messzeitpunkte. Netzwerkpuffer können verzögern; unveränderte Zahlen dürfen
nicht pauschal als Duplikate verworfen werden. Die Datei kennzeichnet diese
Zeitbasis ausdrücklich. Die bestehende Temperatur-Plausibilitätsprüfung des
Spiegel-Plugins ist ein separater Verarbeitungsschritt; der TCP-Zubringer
verändert oder korrigiert die empfangenen Zahlen nicht.

Plugin-Zeilen und archivierte Zeilen haben nicht immer dieselbe Feldzahl:
Beim Live-Abgleich lieferte der TCP-Socket beispielsweise `sol0 17` mit einem
Solarwert. Der Zubringer akzeptiert deshalb wie der bestehende Plugin-Parser
bekannte Sensor-IDs mit ein bis sechs Ganzzahlen. Das ist eine Formatprüfung,
keine Bestätigung der fachlichen Plausibilität durch den nativen Logger.

Dieser Schritt prüft nur den Zubringer. Er startet noch keinen nativen Logger
und belegt keine Archivierung oder vollständige Sensorversorgung. Für den
späteren laufenden Zubringer ist `--duration 0` vorgesehen; dessen Dienst und
die schreibgeschützte Übergabe in die isolierte Loggerumgebung werden gesondert
eingerichtet. Die Netzwerkisolation der Web-Testoberfläche bleibt bestehen.

Entwicklungsprüfung: Drei Tests mit tatsächlichen lokalen TCP-Verbindungen
prüfen Teilzeilen, fehlerhafte/überlange Eingaben, ausbleibende Sendebefehle,
Verbindungswiederaufnahme, das Verwerfen alter Snapshots sowie die Übergabe an
den vorhandenen Plugin-Parser. Die zugehörigen Testdaten sind synthetisch.

Native Abnahme des reinen Zubringers am 06.11.2026 auf dem neuen Pi:
90,19 Sekunden, 15 Datensätze, eine Verbindung, keine Formatverwerfungen,
keine unvollständigen Zeilen und kein Überlauf. Empfangen wurden Wind,
Außentemperatur, Solarstrahlung, UV, generische Daten sowie die weiteren
Temperatur-/Kombisensoren. Regen wurde in diesem kurzen Fenster nicht
empfangen; daraus folgt kein Ausfallnachweis. Der native Logger lief dabei
noch nicht.

Von THB-Kombisensoren wird der vollständige ursprüngliche Datensatz an den
nativen Logger weitergegeben. Im Anzeigeindex wird nur Druck übernommen;
auch eine plausible THB-Temperatur wird dort nicht als Ersatzquelle genutzt.
Details und Abgrenzung zum nativen Roharchiv stehen in
[feed-recovery.md](feed-recovery.md#druck-aus-dem-kombisensor-getrennt-übernehmen).

#### B5p. Native Logger-Konfiguration vorbereiten

Vor dem Start muss die aktuelle native Konfiguration geprüft werden. Dazu
führt der bestehende Probelauf das vorbereitete CGI einmal mit `-1` aus.
Das geschieht mit denselben Datei-, Geräte- und Netzwerkgrenzen wie der
CGI-Probelauf. Der gesamte private Ordner `root/home/meteohub` wird zuvor
als `home-before` im privaten Berichtverzeichnis gesichert, da der native
Generator mehrere Konfigurationsdateien schreibt. Symlinks werden als Links
gesichert und nicht verfolgt. Währenddessen keine
Einstellungen in der Browseroberfläche ändern.

Als normaler Benutzer auf dem Pi (Pfade auf die tatsächlich verwendete
Testkopie anpassen):

```sh
(
set -e
cd "$HOME/src/meteohub"
git pull --ff-only
PYTHONDONTWRITEBYTECODE=1 python3 test-feed-process.py
python3 tools/probe-cgi.py \
  "$HOME/meteohub-staging/5.0s-openssl3" \
  --runtime "$HOME/meteohub-staging/5.0s-runtime" \
  --generate-logger-config
)
```

Erwartet werden ein erfolgreicher Generatorlauf und `GENERATED: logger.conf`.
Die Ausgabe zeigt nur Daten-/Logpfade und numerische Stationskennungen;
weitere Stationsparameter und Zugangsdaten bleiben privat. Eine alte, nicht
neu erzeugte Konfiguration wird ausdrücklich abgewiesen. Dieser Schritt
startet noch keinen Logger und installiert keinen Bootdienst.

Die Stationsart muss vor dem eigentlichen Spiegelbetrieb zum Plugin-Eingang
passen; vorhandene Direkt-USB-Einstellungen dürfen nicht ungeprüft übernommen
werden. Die dauerhafte TCP-Aufnahme, der Dateizugriff aus der isolierten
Loggerumgebung und die tatsächliche native Archivierung werden danach geprüft.

Entwicklungstest: Ein synthetisches CGI hat unter den tatsächlichen
systemd-Isolationsregeln `-1` und die bereinigte Umgebung geprüft und seine
Konfiguration ausschließlich im privaten Testbaum geschrieben. Zwei weitere
Tests prüfen die begrenzte Ausgabe und das Zurückweisen ungeeigneter Dateien.
Die native Generierung auf dem Ziel-Pi ist noch separat abzunehmen.

Der erste native Versuch am 06.11.2026 bestand die Isolation und beendete das
CGI mit Exit 0, schrieb aber nur zwei Antwortbytes. `logger.conf`,
`logger.conf.new` und `wmr928eval.conf` fehlten tatsächlich. Ursache war der
falsch übernommene Parameter `-2`: In einem lokal untersuchten älteren
ARM-Referenzbinary gibt dieser einen Zahlenwert aus; `-1` ruft dagegen die
Konfigurationsschreiber einschließlich `logger.conf` auf. Diese Untersuchung
ist kein Ausführungsnachweis für das konkrete 5.0s-Binary auf dem Ziel-Pi.
Der korrigierte native Lauf muss dort noch erfolgreich abgenommen werden.
Das anschließend untersuchte Herstellerpaket 5.1e bestätigt den Aufruf
zusätzlich direkt: Sein Skript `onboot` führt das CGI mit `-1` aus; dieses
Skript wird bei unserer Vorbereitung ausschließlich gelesen, nicht ausgeführt.

Die bisherigen synthetischen Tests prüften die Isolation und Aufrufübergabe,
aber bestätigten den irrtümlich vorausgesetzten Parameter. Die Testattrappe
unterscheidet nun Zahlenabfrage und Konfigurationsgenerierung. Zusätzlich
werden die vollständige private Sicherung ohne Symlink-Verfolgung sowie
Exit 0 ohne Datei und eine unveränderte Altdatei geprüft. Das Werkzeug
wertet diese Fälle als Fehler; eine leere Konfiguration darf nicht als
Ersatz angelegt werden. Es wurde bislang kein Logger gestartet.

#### B5q. Zielversion 5.1e vom Hersteller beziehen

Das [offizielle Update-Verzeichnis](https://wiki.meteohub.de/wiki/index.php/Updates)
führt 5.1e als neuestes Update. Das zuvor verwendete vollständige RPi-Image
enthält hingegen 5.0s. Für eine Installation mit Zielstand 5.1e wird zusätzlich
[update-v5.1e.upd](https://www.meteohub.de/files/update-v5.1e.upd) benötigt.
Laut Hersteller enthalten die Updates die vorherigen Änderungen; eine Kette
aller Zwischenversionen ist nicht erforderlich.

Als normaler Benutzer zunächst ausschließlich herunterladen und prüfen:

```sh
(
set -e
umask 077
mkdir -p "$HOME/meteohub-original"
cd "$HOME/meteohub-original"
test ! -e update-v5.1e.upd
curl --fail --location --output update-v5.1e.upd \
  https://www.meteohub.de/files/update-v5.1e.upd
printf '%s  %s\n' \
  725bf80186fe2e426e0caad80d6b5994c013fe7f918506fbfb62f5aef2826ad4 \
  update-v5.1e.upd | sha256sum -c -
file update-v5.1e.upd
)
```

Am 06.11.2026 heruntergeladen und lokal untersucht: 18584769 Bytes,
gzip-komprimiertes Tar-Archiv mit 404 Einträgen, darunter `rpi/loggerd`,
`rpi/meteohub.cgi` und weitere Raspberry-Pi-Programme. Der SHA256-Wert oben
ist unser Vergleichswert des über HTTPS bezogenen Downloads, keine separat
vom Hersteller veröffentlichte Signatur.

Das Paket enthält auch alte Betriebssystemdateien, eine Bash-Binärdatei,
Debian-Pakete und Startskripte. Deshalb den historischen Updateablauf nicht
ungeprüft auf Trixie ausführen und das Archiv nicht über das Host-Dateisystem
entpacken. Unser Update-Schritt bereitet zuerst die fünf aktuell genutzten
Kernprogramme aus dem `rpi/`-Zweig vor: `loggerd`, `meteometar`, `meteonet`,
`meteoschedule` und `meteohub.cgi`. Die hashgeprüfte `libgcgi` bleibt aus dem
Basiskandidaten erhalten. Es werden keine Betriebssystemdateien, vorgegebenen
SSH-Schlüssel, Konfigurationen oder Update-Skripte übernommen.

**1. Quellen aktualisieren, Update prüfen und neuen Kandidaten erzeugen:**

```sh
(
set -e
cd "$HOME/src/meteohub"
git pull --ff-only
PYTHONDONTWRITEBYTECODE=1 python3 tools/test-update.py \
  "$HOME/meteohub-original/update-v5.1e.upd" \
  "$HOME/meteohub-staging/5.0s-openssl3/lib/libgcgi.so.0"
python3 tools/stage-update.py \
  "$HOME/meteohub-original/update-v5.1e.upd" \
  "$HOME/meteohub-staging/5.0s-openssl3" \
  "$HOME/meteohub-staging/5.1e-openssl3"
)
```

Das Ziel muss neu sein; bei einem vorhandenen Ziel bricht das Werkzeug ab.
Ein fehlgeschlagener oder bereits erzeugter Kandidat wird nicht automatisch
überschrieben. Der bestehende Kandidat und die laufende Oberfläche bleiben
unverändert. `manifest.json` hält Herkunft, Version, Prüfsummen und einzelne
ELF-Metadatenänderungen fest. Ausführbare Sektionen bleiben bytegleich.

**2. Auf dem Pi die Bibliotheksauflösung der neuen Dateien prüfen:**

```sh
(
set -e
candidate="$HOME/meteohub-staging/5.1e-openssl3"
for name in loggerd meteometar meteonet meteoschedule meteohub.cgi; do
  printf '\nBIBLIOTHEKEN 5.1e: %s\n' "$name"
  env -u LD_PRELOAD -u LD_AUDIT -u LD_LIBRARY_PATH \
    /lib/ld-linux-armhf.so.3 \
    --library-path "$candidate/lib:/usr/lib/arm-linux-gnueabihf" \
    --list "$candidate/bin/$name"
done
)
```

**3. Eigene 5.1e-Laufzeitumgebung und einmaliger CGI-Test:**

Die laufende Browser-Testoberfläche bleibt währenddessen bestehen. Für diesen
Probelauf wird ein neuer, leerer privater Konfigurations-/Datenbaum aus dem
schreibgeschützt eingebundenen Basisimage angelegt. Einstellungen und Daten
einer bestehenden Testinstallation werden dabei nicht überschrieben. Die
statischen Grundressourcen stammen weiterhin aus dem Image; dies prüft zuerst
den Start des neuen Haupt-CGI, noch nicht sämtliche Webfunktionen.

```sh
(
set -e
cd "$HOME/src/meteohub"
git pull --ff-only
python3 tools/stage-runtime.py \
  /mnt/meteohub-original \
  "$HOME/meteohub-staging/5.1e-openssl3" \
  "$HOME/meteohub-staging/5.1e-runtime"
python3 tools/probe-cgi.py \
  "$HOME/meteohub-staging/5.1e-openssl3" \
  --runtime "$HOME/meteohub-staging/5.1e-runtime"
)
```

Der Probelauf führt nach der Isolationsprüfung genau einen CGI-Aufruf aus,
mit 30 Sekunden Laufzeitgrenze und ohne Loggerstart. Im neuen Testbaum wurden
noch keine Lizenzbedingungen bestätigt und keine Wetterstation eingerichtet;
eine entsprechende Seite ist daher möglich. Auch eine Gateway-Warnung ist
wegen der Netzwerkisolation zu erwarten. Exit 1 allein ist weder Beweis für
einen Absturz noch eine erfolgreiche Funktionsabnahme: Antwortinhalt und
Fehlerausgabe gemeinsam auswerten. Bei einer Wiederholung nur den Probelauf
aufrufen; `stage-runtime.py` verweigert ein bereits vorhandenes Ziel.

**Nachweise und noch offene Schritte:** Fünf lokale Tests mit dem echten
Herstellerpaket bestanden am 06.11.2026: ARM-Dateien/Abhängigkeiten und
unveränderte ausführbare Sektionen, erhaltene Quellen, Ablehnung vorhandener
oder verschachtelter Ziele, beschädigter Archive, abweichender Bibliotheken
sowie problematischer Archivpfade/Links/Duplikate. Kein Herstellerprogramm
wurde dabei ausgeführt. Auf dem echten Raspberry Pi 4 hat der Betreiber
anschließend mit Repository-Stand `5cb594d` dieselben fünf Tests erfolgreich
ausgeführt (4,015 Sekunden) und den Kandidaten `5.1e-openssl3` erstellt.
Paket-/Komponentenprüfsummen und unveränderte ausführbare Sektionen wurden
dabei erneut bestätigt. Danach löste der native ARM-Lader auf dem Pi für alle
fünf Programme sämtliche aufgeführten Bibliotheken auf, einschließlich
`libssl.so.3`, `libcrypto.so.3` und der privaten `libgcgi.so.0`. Es wurden keine
fehlenden Bibliotheken oder Versionsanforderungen gemeldet. `--list` allein
führt ihre Anwendungslogik nicht aus.

Am 07.11.2026 um 00:20 CET folgte auf dem Pi der echte CGI-Probelauf
(Bericht `cgi-probe-awzogl3m`): alle Isolationsprüfungen bestanden, 15945 Bytes
HTML-Antwort mit Lizenzbedingungen, kein Ladefehler oder Signalabbruch in
der gelieferten Ausgabe. Das CGI endete mit Status 1 nach 237 ms.
Die unkonfigurierte Station und Netzwerkisolation wurden in der Seite
gemeldet. Das belegt den nativen Start und die Ausgabe dieses CGI-Pfades,
noch keine vollständige OpenSSL-, Aktivierungs- oder Logger-Abnahme. Die
Laufzeitumgebung war bereits vorhanden; deshalb wurde ihre Neuanlage korrekt
verweigert und nur der Probelauf wiederholt.

**4. Native Logger-Konfiguration in der 5.1e-Testumgebung erzeugen:**

```sh
(
set -e
cd "$HOME/src/meteohub"
git pull --ff-only
python3 tools/probe-cgi.py \
  "$HOME/meteohub-staging/5.1e-openssl3" \
  --runtime "$HOME/meteohub-staging/5.1e-runtime" \
  --generate-logger-config
)
```

Der Helfer sichert vor dem Aufruf den privaten Anwendungskonfigurationsordner
unter `home-before` im neuen Berichtverzeichnis und ruft danach das CGI mit
`-1` auf. Erwartet wird `GENERATED: logger.conf` mit den begrenzt ausgegebenen
Daten-/Logpfaden und gegebenenfalls Stationskennungen. Eine fehlende Datei
oder unveränderte Altdatei zählt trotz Exit 0 als Fehler. In dieser frischen
Testumgebung ist noch keine Station eingerichtet; auch eine erzeugte Datei
muss vor dem Loggerstart auf den vorgesehenen Plugin-Eingang eingestellt und
geprüft werden. Dieser Befehl startet keinen Logger und schaltet die laufende
Browseroberfläche nicht um.

Am 07.11.2026 wurde dieser Lauf auf dem Pi bestätigt (Bericht
`cgi-probe-epi7arc2`): Isolation bestanden, CGI-Exit 0, neue `logger.conf`
mit 276 Bytes, `@DATAPATH /data/weather/` und
`@ERRORLOG /data/log/meteohub.log`. Es wurde keine `@WEATHERSTATION`-Zeile
ausgegeben. Damit ist die Generierung nachgewiesen, die Stationsauswahl
bleibt offen; kein Logger wurde gestartet.

**5. Browser-Testoberfläche für 5.1e vorbereiten und umstellen:**

Zuerst die neue Oberfläche vorbereiten. Dabei wird noch kein Dienst gestoppt
oder gestartet. Das Webkennwort zweimal interaktiv eingeben; nicht in Befehle,
Git oder Protokolle schreiben.

```sh
cd "$HOME/src/meteohub"
python3 tools/web-test.py prepare \
  "$HOME/meteohub-staging/5.1e-openssl3" \
  "$HOME/meteohub-staging/5.1e-runtime"
```

Für den folgenden Wechsel die Pfade des tatsächlich bisher verwendeten
Kandidaten und Laufzeitordners als Rückweg bereithalten. Die beiden Variablen
unten gelten für den ursprünglichen 5.0s-Test aus dieser Anleitung; bei einer
abweichenden Testkopie müssen beide auf deren wirkliche Pfade zeigen. Die
vorhandenen Verzeichnisse werden bei diesem Wechsel nicht entfernt.

```sh
(
set -e
cd "$HOME/src/meteohub"
previous_candidate="$HOME/meteohub-staging/5.0s-openssl3"
previous_runtime="$HOME/meteohub-staging/5.0s-runtime"
test -f "$previous_candidate/manifest.json"
test -f "$previous_runtime/root/opt/meteohub-web/prepared.json"
sudo systemctl stop meteohub-web-test.socket meteohub-web-test.service
if ! python3 tools/web-test.py start \
  "$HOME/meteohub-staging/5.1e-openssl3" \
  "$HOME/meteohub-staging/5.1e-runtime"
then
  sudo systemctl stop meteohub-web-test.socket meteohub-web-test.service
  python3 tools/web-test.py start "$previous_candidate" "$previous_runtime"
  exit 1
fi
)
```

Der bestehende SSH-Tunnel auf Port 18090 kann weiterverwendet werden.
Im Browser `http://127.0.0.1:18090/cgi-bin/meteohub.cgi` neu laden und mit
Benutzer `meteohub` sowie dem neuen Webkennwort anmelden. Die Lizenzbedingungen
der neuen Testkopie selbst lesen und gegebenenfalls bestätigen. Danach unter
System Information die tatsächlich angezeigte Version und Buildnummer prüfen.
Eine Aktivierungsanzeige ersetzt die Prüfung des Loggerbetriebs nicht. In der
neuen Kopie ist weiterhin noch keine Station ausgewählt.

**Native Browserabnahme, 07.11.2026, 00:24 CET:** Der Betreiber bestätigte
auf dem Raspberry Pi 4 die erfolgreiche Umstellung mit Isolationsprüfung,
lighttpd-Konfigurationstest und HTTP 401 für nicht authentifizierte Anfragen.
Die authentifiziert aufgerufene Systemseite zeigte **5.1e (Build 277)**,
Kernel `6.18.60+rpt` und 927 MB RAM. Das ist die beobachtete Buildnummer des
oben per Hash festgelegten Herstellerpakets; sie wurde nicht aus dem
Paketnamen oder älteren Forenbeiträgen abgeleitet.

Die alte Plattformanzeige meldete dabei `x86`, obwohl die eingespielten und
nativ geladenen Programme ARM-ELF32 sind. Plattform-Erkennung, leere System-ID
und ungültige MAC bleiben daher offen. Das Wort `activated` neben einer leeren
System-ID gilt nicht als erfolgreiche Aktivierungsprüfung. Die Netzwerkhinweise
entsprechen der isolierten Umgebung. Fehlende `loggerd.pid`, `dropbear.pid`
und `smbd.pid` betreffen dort nicht laufende Legacy-Dienste; insbesondere ist
die Dropbear-Prüfung kein Statusnachweis für den tatsächlichen OpenSSH-Dienst
des Pi. Loggerstart, Stationsauswahl und Messwertarchivierung sind weiterhin
nicht abgenommen.

**6. Station als Plug-in konfigurieren und den Adapter vorbereiten:**

In der Weboberfläche unter Weather Station eine benutzerdefinierte Station
anlegen und Anschlussart **Plug-in** mit Pfad `/home/meteohub/plugin.sh`
einstellen. Name, tatsächliche Standorthöhe und Berechnungseinstellungen sind
stationsbezogen zu wählen. Für diesen Spiegeltest ist genau eine Station mit
Index 0 vorgesehen. Eine Meldung „Data Logging restarted“ in der Oberfläche
ist kein Nachweis für einen laufenden Logger in der isolierten Testumgebung.
Keine USB-Schnittstelle öffnen: Die Originalstation bleibt alleiniger Leser
ihrer angeschlossenen Konsole.

Am 07.11.2026 meldete der Betreiber Station 0 (User-defined), Anschlussart
Plug-in und den vorgesehenen Plugin-Pfad; Data Logging stand weiterhin auf
stopped. Noch keine Sensorzuweisung. Die Anzeige ist ein UI-Befund; im nächsten
Schritt muss die daraus generierte native Konfiguration dazu passen.

Nach dem Speichern während der folgenden Befehle keine parallelen
Web-Konfigurationsänderungen vornehmen:

```sh
(
set -e
cd "$HOME/src/meteohub"
git pull --ff-only
PYTHONDONTWRITEBYTECODE=1 python3 tools/test-tcp-plugin-prepare.py
python3 tools/probe-cgi.py \
  "$HOME/meteohub-staging/5.1e-openssl3" \
  --runtime "$HOME/meteohub-staging/5.1e-runtime" \
  --generate-logger-config
python3 tools/prepare-tcp-plugin.py \
  "$HOME/meteohub-staging/5.1e-runtime"
)
```

Der neue Helfer akzeptiert ausschließlich eine native Stationszeile mit
`@WEATHERSTATION 0 9 5 /home/meteohub/plugin.sh` sowie die privaten Daten- und
Logpfade aus Schritt 4. Er erzeugt den Wrapper und die geprüfte Python-Datei
nur im privaten `runtime/root/home/meteohub`, nicht im wirklichen Login-Home.
Vorhandene Dateien werden nicht überschrieben. Das native `logger.conf` wird
bei diesem Vorbereitungsschritt nicht umgeschrieben.

Der spätere TCP-Zubringer schreibt auf dem Host nach
`5.1e-runtime/root/data/tcp-feed/feed.json`; das isolierte Plugin liest dieselbe
Datei als `/data/tcp-feed/feed.json`. Es benötigt dafür weder einen eigenen
Netzwerkzugang noch USB-Geräte. Sein Zustand und seine Herkunftsnachweise
liegen unter `/data/tcp-feed/state`. Noch wird kein TCP-Zubringer oder Logger
gestartet; eine fehlende `feed.json` ist in diesem Zustand normal.

Die korrigierte Druckregel: vollständiges ursprüngliches THB an den nativen
Logger, ausschließlich Druck für Dashboard/SVG. Ältere Installationen mit
separaten `pressure_only`-Nachweisen benötigen das
[Plugin-Update](installer.md#native-thb-druckaufzeichnung-aktualisieren).
Native Archivierung verlangt zusätzlich die Zuordnung auf der Sensors-Seite.

Vier lokale Vorbereitungstests bestanden: tatsächliche Plugin-Datei und
unveränderte Konfiguration, Ablehnung falscher/fehlender/mehrerer Stationen,
abweichender Pfade, bestehender Ziele und Symlinks. Die vorhandenen echten
Prozesstests prüfen zusätzlich Temperatur-vor-Wind, Wiederanlauf ohne Replay,
Drucktrennung samt Index sowie das Beenden nach geschlossenem Leser. Der
Produktionsnachweis mit frischem TCP-Eingang und nativem Logger bleibt offen.

**7. Begrenzter Test: TCP-Empfang bis zur echten Plug-in-Ausgabe:**

Auf dem Ziel-Pi wurden am 07.11.2026 die vier Vorbereitungstests bestätigt.
Die native Generierung schrieb nun 361 Bytes `logger.conf`, einschließlich
`@WEATHERSTATION 0 9 5`; der Adapter wurde erfolgreich im privaten Testbaum
vorbereitet (Bericht `cgi-probe-gq0dg5mp`). Noch läuft kein Logger.

Für den folgenden Test darf noch kein anderer Zubringer oder Logger dieselbe
Testumgebung benutzen. Während der Prüfung keine Stationskonfiguration im
Browser ändern. `SOURCE_HOST` durch die Adresse der vorhandenen Station mit
bereits bereitgestelltem Plugin-Kopierstrom ersetzen. Der TCP-Dienst muss
bereits vorhanden sein; die Quelle und deren USB-Zugriff werden nicht geändert.

```sh
(
set -e
cd "$HOME/src/meteohub"
git pull --ff-only
sudo -v
python3 tools/tcp-feed.py \
  --host SOURCE_HOST --port 5500 --duration 120 \
  --output "$HOME/meteohub-staging/5.1e-runtime/root/data/tcp-feed/feed.json"
python3 tools/probe-cgi.py \
  "$HOME/meteohub-staging/5.1e-openssl3" \
  --runtime "$HOME/meteohub-staging/5.1e-runtime" \
  --probe-plugin
)
```

Zuerst werden 120 Sekunden lang Daten ausschließlich empfangen. Unmittelbar
danach liest der tatsächlich vorbereitete Wrapper die Momentaufnahme in der
bereits geprüften Dateisystem-/Netzwerkisolation für maximal 15 Sekunden.
`sudo -v` steht bewusst vor dem Empfang, damit eine spätere Passwortabfrage
die Messwerte nicht unnötig altern lässt. Die bestehenden Frischegrenzen
bleiben unverändert: höchstens 45 Sekunden seit der letzten Quelllesung und
höchstens 180 Sekunden je Empfangszeitstempel. Der TCP-Dienst liefert selbst
keine Messzeitstempel.

Erwartet werden empfangene Datensätze beim Zubringer und anschließend
`"plugin_probe_passed": true`, Sensorzähler und gegebenenfalls separat erfasste
Druckwerte. `SYSTEMD_RUN_EXIT: 124` bedeutet in diesem speziellen Modus den
vorgesehenen 15-Sekunden-Abbruch durch `timeout`. Der Helfer akzeptiert ihn
nur mit syntaktisch gültiger, nicht leerer Plug-in-Ausgabe. THB-Ausgaben müssen
drei Zahlenfelder und einen Druck zwischen 3000 und 12000 Zehntel-hPa haben.
Ein äußeres Zeitlimit, ein anderer Exitcode oder eine leere Ausgabe ist kein
Erfolg. Fehlt in diesem kurzen Fenster ein Druckwert oder `t2`, darf daraus
kein dauerhafter Sensorausfall abgeleitet werden; Wind bleibt beim Start bis
zum ersten echten `t2` zurückgestellt.

Der Bericht enthält `plugin-result.json`, private Standardausgabe und
Fehlerausgabe. Der Herkunftsnachweis und der Cursor des Test-Plugins liegen
unter `runtime/root/data/tcp-feed/state`. Nur neu hinzugekommene Druck- und
Ablehnungseinträge zählen zum Bericht. Der Test erzeugt keine nativen
Wetterarchive. Er ist keine Hintergrundüberwachung: TCP-Zubringer und Plugin
enden beide; Dauerbetrieb und nativer Logger folgen als eigene Schritte.

Entwicklungsnachweis der früheren Version vor der THB-Korrektur:
Ein echter lokaler TCP-Testserver sendete synthetische
Temperatur-, Wind- und THB-Daten an den tatsächlichen Zubringer. Danach lief
der installierte Wrapper als unprivilegierter Benutzer in der tatsächlichen
systemd-Isolation: Temperatur und Wind wurden ausgegeben, nur Druck wurde
separat gehalten und das 15-Sekunden-Limit beendete den Prozess. Zusätzlich
wurden leere/THB-Ausgaben und unerwartete Exitcodes als Fehler geprüft.
Die neue Fassung erlaubt vollständiges THB und verwirft fehlerhafte THB-Formate;
ihre Nachweise sind in der aktuellen Installer-Anleitung dokumentiert.
Der Nachweis mit realen Quelldaten auf dem Ziel-Pi erfolgte inzwischen am
7. November 2026: 17 empfangene Datensätze, 16 Plugin-Ausgaben und ein separater
Druckwert; keine Verwerfungen. Siehe [Zielprüfung](installer.md#pi-4-zielprüfung-am-7-november-2026).

Die Vorbereitung ist noch kein vollständig installiertes 5.1e-System.
Vor dem Umschalten sind eine gesicherte private Laufzeitkopie, CGI-Aufruf,
Versions- und Buildanzeige, generierte Logger-Konfiguration und echte
Messwertarchivierung zu prüfen. Weitere Anwendungsprogramme und Ressourcen
für Diagramme, Export und zusätzliche Stationsarten müssen passend eingebunden
werden, bevor diese Funktionen als verfügbar gelten. Die Hersteller-Builds
242 und 276 werden im [5.1e-Release-Thread](https://forum.meteohub.de/viewtopic.php?t=15410)
unterschieden; aus dem Dateinamen allein wird keine Buildnummer abgeleitet.
Die bestehende Installation dient bis zur Abnahme als Rückweg.

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
| **Update auf 5.1e** | B5q durchführen; native Versions-/Buildanzeige und tatsächlich verwendete Dateien prüfen. 5.0s ist kein produktiver Abschlussstand. |
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
mit 1 GB führen **B1–B5n** bis zur isolierten Browser-Testoberfläche.
Die produktive Stationsaufnahme ist damit noch nicht eingerichtet. Die offenen
Schritte werden nach ihrer nativen Prüfung als Installationsbefehle ergänzt.

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
