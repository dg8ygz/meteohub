# Originalsoftware beschaffen

Für ein öffentliches Basisimage wurde auch das SheevaPlug-Paket untersucht:
[Ergebnis und vorgesehener Herstellerdownload](vendor-setup-plug-review.md).
Es ersetzt die geprüfte Raspberry-Pi-Quelle nicht direkt.

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

**Die Trixie-Installation soll mit Meteohub 5.1e abgeschlossen werden.**
Zusätzlich zum Basisimage ist das Hersteller-Update erforderlich; Download und
Prüfstatus stehen in [Abschnitt B5q der Pi-Anleitung](raspberry-pi-setup.md#b5q-zielversion-51e-vom-hersteller-beziehen).

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
