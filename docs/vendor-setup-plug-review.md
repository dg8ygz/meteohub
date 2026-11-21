# Herstellerdownload setup-plug.tgz: Prüfung vom 17. November 2026

Anlass: Ein öffentliches Basisimage soll die proprietäre Meteohub-Anwendung
nicht enthalten. Der Betreiber schlug vor, sie nachträglich über
`setup-plug.tgz` direkt vom Hersteller zu beziehen.

## Ergebnis

Der direkte Herstellerbezug ist als technische Trennung sinnvoll. Dieses
konkrete Paket ist aber kein geeigneter direkter Ersatz für die im aktuellen
Installer geprüften Raspberry-Pi-Dateien. Eine neue Lenny-/ARMEL-Laufzeit wurde
nicht installiert und kein Verteilungsimage als funktionsfähig abgenommen.

Der [Hersteller beschreibt SheevaPlug ausdrücklich mit Debian Lenny für
Kirkwood](https://wiki.meteohub.de/wiki/index.php/OS_Obligations#Meteohub_on_SheevaPlug).
Das Archiv wurde am 17. November über HTTPS bezogen und statisch untersucht;
keines seiner Installationsskripte oder Programme wurde ausgeführt.

- Quelle: <https://www.meteohub.de/files/setup-plug.tgz>
- Größe: 6.533.241 Byte.
- SHA-256: `9bff739751575478685d5e88c5f7bdd6dba5daaa37be50ba388c46438e4ab008`.
- Enthaltene Installationsdateien datieren laut Tar-Metadaten auf Juni/Juli 2009.
- `loggerd` und `meteohub.cgi` sind ARM-EABI4-Programme mit Interpreter
  `/lib/ld-linux.so.3`. Das CGI benötigt unter anderem `libssl.so.0.9.8`,
  `libcrypto.so.0.9.8` und `libgcgi.so.0`.
- Die mitgelieferte `inst-meteohub.conf` hat 38.692 Byte. Unsere geprüfte
  Raspberry-Pi-Vorbereitung erwartet das andere, 65.536 Byte große Format.
  Bloßes Auffüllen oder Austauschen ist keine geprüfte Konvertierung.
- Das enthaltene `update-new` enthält NSLU2-, PLUG- und X86-Markierungen,
  keine RPI-Markierung. Das separat geprüfte Update 5.1e enthält dagegen
  56 Einträge unter `rpi/`.
- Die alten Installationsskripte ersetzen unter anderem `/etc/fstab`, schreiben
  Benutzer-/Gruppeneinträge, installieren SysV-Dienste und übernehmen alte
  Netzwerk-, Samba- und Webserverkonfiguration. Sie dürfen nicht als Installer
  unseres Trixie-Images ausgeführt werden.
- Das verschachtelte Update enthält auch SSH-Authentifizierungsdateien.
  Diese werden weder übernommen noch veröffentlicht; ihr Inhalt ist für die
  Paketprüfung nicht erforderlich.

Die Feststellungen belegen eine andere Zielumgebung und fehlende Kompatibilität
zum bisherigen Vorbereitungspfad. Sie behaupten nicht, dass eine gesonderte
Portierung grundsätzlich unmöglich wäre.

## Vorgesehener Weg für ein öffentliches Basisimage

1. Frisches Raspberry Pi OS Lite Trixie arm64 als Ausgangspunkt; kein Klon der
   persönlichen Installation und keine kopierten freien SD-Blöcke.
2. Nur die eigenen Hilfsprogramme und benötigte Betriebssystempakete vorsehen.
   Vor Veröffentlichung deren jeweilige Lizenz-/Quellcodepflichten erfüllen.
3. Originalprogramme und Herstellerressourcen erst beim Empfänger beziehen.
   Der bestehende `install-pi.py prepare` lädt bereits `mhrpi-v5.0s.rar` und
   `update-v5.1e.upd` direkt über HTTPS vom Hersteller und prüft feste Hashes.
   Diese Dateien und die daraus gewonnenen Programme gehören nicht ins
   öffentliche Basisimage, Release oder Build-Cache.
4. Eigene Benutzerzugänge einrichten und SSH-Hostschlüssel/Machine-ID je Gerät
   neu erzeugen. Keine privaten Wetterarchive, Stationsdaten, Authentifizierungs-
   dateien, Kennungsanpassungen, Betriebslogs oder Fernwartungsfreigaben übernehmen.
5. Lizenzen nicht stellvertretend akzeptieren und keine Aktivierung erzeugen.
   Eine vorhandene Lizenz ist vom jeweiligen Nutzer passend zur Zielhardware
   einzurichten.
6. Erstinstallation, neue SSH-Anmeldung und anschließenden Neustart auf einer
   separaten Testkarte abnehmen, bevor das Image als Release veröffentlicht wird.

Das ist die Quellenentscheidung und Bauvorgabe, **noch kein gebautes oder
bootgeprüftes öffentliches Image**. Der vorhandene Installer deckt die
Anwendungsvorbereitung ab; ein vollständig automatisierter Imagebau und die
Ersteinrichtung sind damit nicht bereits nachgewiesen.

## Lizenzgrenze

Der Hersteller trennt Betriebssystem und proprietäre Anwendung. Ein Download
beim Empfänger vermeidet, dass wir diese Programme selbst im Image verteilen.
Er ist jedoch keine pauschale Erlaubnis für jede Anpassung oder Verwendung.
Die Anwendungsbedingungen gelten weiter, einschließlich der Einschränkungen
für Änderungen. Die bisherigen OpenSSL-Anpassungen sind ebenfalls gesondert
zu beurteilen. Siehe [Originalsoftware und Lizenz](originalsoftware.md).
