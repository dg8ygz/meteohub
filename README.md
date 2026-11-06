# Meteohub auf Debian Trixie

**Eine bestehende Meteohub-Wetterstation auf einer aktuellen Linux-Basis
weiterbetreiben und ihre Messwerte ohne Flash anzeigen.**

Dieses unabhängige Projekt sammelt die dafür entwickelten Kompatibilitätshelfer,
eine kompakte Wetteranzeige und reproduzierbare Tests. Ausgangspunkt ist eine
Raspberry-Pi-Station mit alter ARM-Meteohub-Software. Deren Anwendung und
historische Wetterdaten werden in einer getrennten Debian-Trixie-Testumgebung
erprobt, während die ursprüngliche Station weiter Messwerte liefert.

Es handelt sich um ein eigenständiges Wetterstationsprojekt, nicht um einen
Bestandteil der Webcam-Software. Das Projekt ist keine offizielle
Meteohub-Veröffentlichung und enthält weder die proprietären Originalprogramme
noch ein fertiges Installationsimage.

**Stand: 5. November 2026 – laufender Migrationstest, noch keine vollständige
Produktionsfreigabe.**

[Funktionen](#was-das-projekt-bereits-bietet) ·
[Projektstatus](#aktueller-projektstatus) ·
[Raspberry-Pi-Anleitung für Einsteiger](docs/raspberry-pi-setup.md) ·
[Originalsoftware beschaffen](#original-binaries-beschaffen) ·
[Wettergrafik einbetten](#anzeige-und-datenbehandlung) ·
[Tests](#prüfungen)

## Was das Projekt bereits bietet

- **Kompatibilität mit Trixie:** Hilfen für den Aufruf der alten CGI-Oberfläche,
  historische Diagramme mit neuerem gnuplot und die Steuerung des nativen Loggers.
- **Messwertkopie für den Testbetrieb:** Ein lesender Zubringer übernimmt die
  bestehende Stationsausgabe. Der Testlogger greift nicht parallel auf die
  physische USB-Wetterkonsole zu.
- **Wetteranzeige ohne Flash:** Kompaktes HTML-Dashboard mit Zeitverläufen,
  Sensoraktualität sowie Windrichtung, Mittelwind und Böen nach Richtungssektor.
- **Einbettbare Grafik:** Eine eigenständige SVG mit 600 × 180 Pixeln für die
  Verwendung als einfaches Bild auf anderen Webseiten.
- **Nachvollziehbare Datenbehandlung:** Herkunftsprotokoll, Prüfung auf veraltete
  Messwerte und ein abgeleiteter Anzeigeindex. Gültige Regenrate und Stationsdruck
  bleiben nutzbar, wenn andere Felder desselben Sensorpakets unplausibel sind.

## Aktueller Projektstatus

| Bereich | Belegter Stand |
| --- | --- |
| ARM-Anwendung im Trixie-Testgast | Native Oberfläche und historische PNG-Erzeugung getestet; Host-Neustart mit Wiederanlauf geprüft. |
| Neue Wetteranzeige | Dashboard, SVG-Einbettung, Authentifizierungsgrenzen und Datenkorrekturen im Testsystem geprüft. |
| Lokale Regressionstests | 17 Unit-Tests und ein realer Plugin-Prozesstest bestanden. |
| Langzeitbetrieb | Test eingerichtet; durchgehende 24-Stunden-Abnahme und vollständiger Datensatzabgleich noch offen. |
| Produktive Umstellung | Archiv-/Aggregat-/Exportintegration und vollständige Wartungsabnahme noch offen. |
| Allgemeine Installation | Noch kein universeller Installer; mehrere Helfer verwenden feste Laborpfade. |

Die Angaben beschreiben die dokumentierten Prüfungen zu diesem Stand, keine
automatisch aktualisierte Betriebsüberwachung. Weitere Einschränkungen stehen
unter [Bekannte Grenzen](#bekannte-grenzen-und-noch-ausstehende-arbeit).

## Einstieg

**Zum ersten Mal mit Meteohub?** Die
[Schritt-für-Schritt-Anleitung für Pi 3 und Pi 4](docs/raspberry-pi-setup.md)
erklärt Begriffe, benötigte Hardware, SD-Karte, Anmeldung, Stationskonfiguration,
Messwertkontrolle und Sicherung. Sie trennt den vollständigen Herstellerweg für
das alte Pi-3-Image von der aktuellen Trixie-Vorbereitung für Pi 3/Pi 4.
Die noch fehlende native Trixie-Installation wird ausdrücklich als offen
ausgewiesen; das QEMU-Testimage ist kein direkt bootfähiges Pi-Image.

Für eine eigene Erprobung zunächst die [Original-Binaries beschaffen](#original-binaries-beschaffen)
und eine getrennte ARM-Testumgebung vorbereiten. Auf x86 ist dafür eine passende
ARM-Emulation erforderlich. Ein Checkout dieses Repositorys allein installiert
keine Wetterstation und ersetzt keine bestehende Anwendung.

Die [Dateiübersicht](#bestand) erklärt die einzelnen Komponenten;
die [Testbefehle](#prüfungen) lassen sich ohne angeschlossene Wetterstation
ausführen. Wer nur die kompakte Anzeige nutzen möchte, findet das Bildformat
und das Einbettungsbeispiel unter [Anzeige und Datenbehandlung](#anzeige-und-datenbehandlung).

## Bestand

| Dateien | Aufgabe |
| --- | --- |
| `tools/inspect-original.py` | Liest ELF-Metadaten und Symlinks aus dem separat geöffneten Originalimage, ohne dessen Programme auszuführen. |
| `tools/stage-openssl3.py`, `tools/test-crypto-adaptation.py` | Erstellen private, hashgeprüfte OpenSSL-3-Testkopien aus dem Herstellerimage und prüfen die ELF-Änderungsgrenzen; kein Installer und keine allgemeine ABI-Garantie. |
| `cgi_compat.sh` | Ergänzt bei leerem GET des nativen Haupt-CGI die Startseite. |
| `gnuplot_compat.py` | Übersetzt alte Plot-Präambeln für das Distributions-gnuplot; verändert keine Roharchive. |
| `prepare_logger.py`, `rcloggerd` | Begrenzen den nativen Logger auf die isolierte Pluginquelle und steuern dessen systemd-Dienst. |
| `live-feed-relay.py`, `read-source-socket.sh` | Lesender Zubringer vom bestehenden Stationssocket über SSH zum authentifizierten Test-Endpunkt. |
| `live-feed.cgi`, `live_feed_plugin.py` | Übernahme der Messwertkopie mit Herkunftsprotokoll, Frischeprüfung und persistentem Cursor; Wind wartet beim Start auf eine echte Temperatur. |
| `live-status.cgi`, `live-test-monitor.py` | Statusabfrage und zeitlich begrenzter Labortest; keine automatische Alarmierung. |
| `normalize_native.py`, `verify-native-records.py` | Normalisierung und Abgleich von Plugin- und nativen Archivzeilen. |
| `stop_qemu.py` | Kontrolliertes Ausschalten des Testgasts über den QEMU-Monitor. |
| `dashboard/` | Abgeleiteter SQLite-Anzeigeindex, JSON-API, HTML-Dashboard und eigenständige SVG-Grafik. |

Die Skripte enthalten bewusst noch feste **Testgastpfade**. Sie sind keine
universellen Installationsprogramme. Insbesondere `verify-native-records.py`
bezieht sich auf den Labormonat November 2026 und dessen lokale Vergleichsbasis.

## Originalsoftware und Lizenz

Meteohub bietet ein [Raspberry-Pi-Image](https://wiki.meteohub.de/wiki/index.php/Images)
zum Download an. Betriebssystem und proprietäre Anwendung sind getrennt
lizenziert; dies erläutert der Hersteller unter
[OS Obligations](https://wiki.meteohub.de/wiki/index.php/OS_Obligations).

Die in der untersuchten Installation enthaltene `meteohub-license-5.txt` nennt
unter anderem `loggerd`, `meteohub.cgi` und `meteograph.cgi`. Im Abschnitt
"Evaluation and Registration" verlangt sie eine vorherige schriftliche Erlaubnis
für die Weiterverbreitung der Software/Dokumentation zusammen mit anderen
Produkten, auch nichtkommerziellen. Eine solche Erlaubnis liegt hier nicht vor.
Daher werden diese Programme und das Originalimage nicht mitgeliefert. Das
öffentliche Downloadangebot ist keine nachgewiesene Erlaubnis, die Programme
zusammen mit diesem Projekt neu zu veröffentlichen. Die eigenen Hilfsprogramme
ändern die Lizenz der ursprünglichen Anwendung nicht.

Für eine Installation sind die Originalsoftware vom Hersteller und eine dafür
gültige Nutzungslizenz separat erforderlich. Aktivierungscodes, private Schlüssel,
Stationskonfiguration, Messdaten, Datenbanken, Images und Sicherungen gehören
nicht in diesen Ordner oder dessen Git-Historie.

### Original-Binaries beschaffen

1. Die offizielle [Downloadseite, Abschnitt Raspberry PI](https://wiki.meteohub.de/wiki/index.php/Images)
   öffnen. Dort ist bei Prüfung am 05.11.2026 das
   [RPi-Image 5.0s (`mhrpi-v5.0s.rar`)](https://www.meteohub.de/files/mhrpi-v5.0s.rar)
   verlinkt. Falls der Direktlink später entfällt, die Downloadseite erneut
   prüfen. Das x86-/VMware-Image ist kein Ersatz für die benötigten ARM-Binaries.
2. Das Archiv in ein **privates Arbeitsverzeichnis außerhalb des Repositorys
   und Webroots** herunterladen. URL, Version und einen lokal berechneten
   SHA256-Hash für die spätere Zuordnung notieren. Ein selbst berechneter Hash
   bestätigt ohne unabhängig bezogenen Hersteller-Prüfwert nicht die Echtheit.
3. Das RAR-Archiv mit einem RAR-fähigen Entpacker entpacken. Laut
   [RPi-Anleitung des Herstellers](https://wiki.meteohub.de/wiki/index.php/Setup_RPI)
   entsteht ein mehrpartitioniges Disk-Image (`.img`). Für die reine
   Dateientnahme muss dieses **nicht auf eine SD-Karte geschrieben oder
   gebootet** werden: mit einem Image-Werkzeug schreibgeschützt öffnen und
   das Linux-Root-Dateisystem darin auswählen. Partitionsnummern nicht raten.
4. Die Anwendung samt zugehörigen Ressourcen aus dem Image in eine private
   Staging-Kopie übernehmen. In der untersuchten bestehenden RPi-Installation
   liegen wichtige Dateien an folgenden Stellen; die Pfade im heruntergeladenen
   Image vor der Übernahme prüfen:

   | Pfad innerhalb des Root-Dateisystems | Inhalt |
   | --- | --- |
   | `/home/meteohub/loggerd` | Nativer Messwertlogger |
   | `/home/meteohub/meteonet` | Anwendungsprogramm für Wetter-Netzdienste |
   | `/srv/www/cgi-bin/meteohub.cgi` | Native Verwaltungsoberfläche |
   | `/srv/www/meteograph.cgi`, `/srv/www/meteolog.cgi` | Weitere native CGI-Programme |
   | `/home/meteohub/meteohub-license-5.txt` | Mitgelieferte Anwendungs-Lizenzbedingungen |

   Diese Liste ist eine Orientierung, keine vollständige Installationsliste.
   Webressourcen, Hilfsprogramme, Dateirechte und Symlinks müssen mit betrachtet
   werden. `/etc/init.d/loggerd` ist ein Startskript, nicht das Logger-Binary.
5. Vor Einsatz Architektur und Bibliotheksbedarf beispielsweise mit `file`
   und `readelf -l -d` prüfen. Die alten Betriebssystembibliotheken nicht
   pauschal über die Trixie-Bibliotheken kopieren. Lizenz/Aktivierung für die
   Zielinstallation separat über den Hersteller klären:
   [Aktivierung](https://wiki.meteohub.de/wiki/index.php/Activation),
   [Lizenzübertragung](https://wiki.meteohub.de/wiki/index.php/Transfer).

Alternativ kann eine eigene vorhandene Installation als Quelle dienen, wenn
Version, Lizenz und Vollständigkeit passen. Dabei nur die benötigten
Anwendungsdateien übernehmen: keine fremden Stationszugänge, SSH-Schlüssel oder
Aktivierungsdaten ins Repository kopieren. Ein Image-Download allein ist noch
keine geprüfte Trixie-Installation; die Kompatibilitäts- und Betriebsprüfungen
dieses Projekts bleiben erforderlich. Der hier verlinkte Download wurde für
diese Dokumentation nicht vollständig heruntergeladen oder neu abgenommen.

## Anzeige und Datenbehandlung

Die kompakte SVG ist 600 × 180 Pixel groß. Nach einer passenden Webserver-
Einrichtung kann sie beispielsweise so eingebettet werden:

```html
<a href="/weather.svg"><img src="/weather.svg" width="600" height="180"
  alt="Aktuelle Wetterwerte und Windrichtung"></a>
```

Der Bildabruf erzeugt eine neue Darstellung, ein einfaches `img` aktualisiert
sich jedoch nicht selbstständig. Für HTTPS-Seiten muss auch der Bildpfad über
HTTPS erreichbar sein. Dashboard/API bleiben authentifiziert; im Test ist nur
der genaue SVG-Pfad öffentlich. `.htaccess` sperrt diesen Quellordner selbst
gegen Webzugriffe, sofern Apache die Datei auswertet. Für andere Webserver ist
die entsprechende Zugriffssperre separat einzurichten.

Das Dashboard benötigt Python 3, SQLite und Browser-JavaScript, die SVG nur einen
Bildbetrachter. Der Labormonitor benötigt zusätzlich Python `requests`, die
nativen Kompatibilitätshilfen unter anderem systemd, Lighttpd und gnuplot.
ARM-Binaries benötigen eine passende ARM-Laufzeit; ein x86-Host allein genügt nicht.

- Roharchive bleiben maßgeblich; der Anzeigeindex ist davon abgeleitet.
- Vom auffälligen THB-Kombisensor wird ausschließlich plausibler Stationsdruck
  übernommen. Temperatur, Feuchte und daraus abgeleiteter Meeresspiegeldruck
  werden nicht angezeigt.
- Eine gültige Regenrate wird auch bei negativem Gesamtzähler übernommen.
  Der negative Gesamtzähler wird verworfen, ohne eine Zählerkorrektur zu erfinden.
  Dadurch bleibt der Zeitstempel der aktuellen Regenrate erhalten.
- Fehlende oder veraltete aktuelle Werte erscheinen als fehlend, nicht als Null.
- Windvektoren zeigen den 24-Stunden-Mittelwind und die maximale Böe je Sektor.

Zugangsdateien für Relay/Monitor werden nur in einem privaten Laufzeitverzeichnis
angelegt. Die Skripte laden sie relativ zu ihrem eigenen Standort; deshalb
Laufzeitkopien außerhalb des Webroots verwenden. Keine echten Zugangswerte in
Beispiele übernehmen. Dienste und Authentifizierung müssen getrennt eingerichtet
werden; dieser Ordner führt bei einem Checkout keine Installation aus.

## Prüfungen

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

## Bekannte Grenzen und noch ausstehende Arbeit

Hinweise zum sicheren Mitlesen und zum behobenen Pipe-Hänger stehen in
[Feed und Logger-Wiederanlauf](docs/feed-recovery.md).

- Die durchgehende 24-Stunden-Abnahme und der vollständige Datensatzabgleich
  sind noch nicht abgeschlossen. Frühere Punktprüfungen ersetzen dies nicht.
- Produktive Archiv-/Aggregat-/Exportintegration, vollständige Wartungsabnahme
  und die endgültige Stationszuführung bleiben offen.
- Der negative Regen-Gesamtzähler ist noch ungeklärt; nur dessen Auswirkung auf
  die Anzeige der gültigen Regenrate wurde behoben.
- Der aktive Feed verwendet das Pluginformat. Der ältere `recorded`-Fallback
  in `live_feed_plugin.py` ist für Regen-/UV-Konvertierungen nicht freigegeben.
- `live-status.cgi` liest Zeit und Feed nicht atomar; ein knapp negativer
  Heartbeat-Abstand kann eine falsche Aktualitätswarnung verursachen.
- Langzeittest-Dienste haben im Labor eine Laufzeitbegrenzung; daraus folgt
  keine dauerhafte Überwachung oder Alarmierung.

Dieses Projekt wird unabhängig von Webcam- und SDR-Software versioniert.
Standortbezogene Betriebsbelege liegen außerhalb dieses Repositorys in einem
privaten Verzeichnis. Sie enthalten interne Angaben und gehören nicht auf
GitHub. Commits erfolgen zunächst lokal; eine Veröffentlichung ist ein
getrennter Schritt.
