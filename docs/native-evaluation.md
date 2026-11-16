# Native Auswertung und WAN-IP auf Pi .50

Stand: 16. November 2026, Abnahme 21:07–21:12 MEZ.

## Ursache und Änderung

`Weather Data Recomputation: waiting` war ein echter unbearbeiteter Auftrag.
Das CGI prüft `pidof -x wmr928fulleval`, anschließend die Stage-Datei und bei
fehlendem Prozess die Datei `/home/meteohub/wmr928fulleval.conf`. Der Auftrag
bestand seit dem 11. November. In der migrierten Laufzeit fehlten der native
Auswerter und dessen regelmäßiger Aufruf; der Dashboard-Indexer ersetzt diese
native Berechnung nicht.

Installiert wurde das originale ARM-Programm `rpi/loggereval` aus dem bereits
vorhandenen Herstellerpaket `update-v5.1e.upd`, unter dem historischen Namen
`wmr928eval`. SHA-256 des unveränderten Programms:
`a9cb1c64843447d32af6e3fd8b67725c61b9f6ccdad2abcbefb5bd9eef974812`.
Es benötigt libc/libm, keine alte OpenSSL-Bibliothek. Herstellerbinärdateien und
Aktivierungsdaten werden nicht ins Repository aufgenommen.

Die Quellen der neuen Steuerung:

- `tools/native-eval.py`: serieller Worker, vollständige und laufende Auswertung.
- `tools/wmr928fulleval`: ausführbarer Shell-Einstieg, damit das Original-CGI den
  tatsächlich laufenden Vollauswertungsprozess mit `pidof -x` erkennt.
- `tools/meteohub-native-eval.service`: eigener unprivilegierter Dienst ohne
  Netzwerk, im Meteohub-RootDirectory, CPU-Limit 25 %, RAM-Limit 128 MiB.
- `tools/test-native-eval.py`: Fehler-/Wiederanlauf- und Auftragsübergabetests.

Installationsverzeichnis: `/usr/local/libexec/meteohub-native-eval`, im Dienst
nur lesbar als `/opt/meteohub-native-eval` eingebunden. Der Worker ist über
`meteohub-live.target.wants` dauerhaft aktiviert. Er verändert keine Roharchive
und baut keine weitere Stationsverbindung auf.

Minuten-Sequenzen werden etwa jede Minute aktualisiert; die übrigen Aggregate
und historischen Reihen alle fünf Minuten zuzüglich Laufzeit. Die nativen
Parameter entsprechen den mitgelieferten `wmr928fulleval`-/`histeval`-Skripten.
Ein Vollauftrag wird erst nach erfolgreichen Unterprozessen und nachgewiesenen
nichtleeren Fünf-Minuten-Aggregaten abgeschlossen. Bei Fehlern bleibt der
Auftrag erhalten. Ein neuer Auftrag während einer laufenden Berechnung wird
nicht durch deren Abschluss gelöscht. Nach Dienststart erfolgt ein Neuaufbau
der abgeleiteten Dateien aus den Rohdaten, auch nach einem eingefrorenen
Checkpoint mit noch ungeflushten Prozesspuffern.

`/data/native-eval-status.json` enthält den letzten erfolgreichen Lauf oder
Fehler. Das ist ein lokaler Status, keine eingerichtete externe Alarmierung.

## Einbindung in RAM-Sicherung

Der neue Dienst steht als fünfter Eintrag in `/etc/meteohub-ram.json` unter
`apps`; der Logger bleibt auf Index 2. Die geprüfte App-Anzahl im RAM-Helfer
wurde auf vier oder fünf erweitert, der registrierte Helfer-Hash aktualisiert.
Dadurch erfasst der vorhandene Freeze-Checkpoint auch den Worker samt Kindern;
der Stop/Rebase-Pfad stoppt und startet ihn ebenfalls. Der Dienst ist nach der
RAM-Unit geordnet und wird daher vor deren Abschaltsicherung beendet.

Nicht einfach die Unit deaktivieren und den fünften Eintrag stehen lassen:
Die Sicherung verlangt aktive Writer. Ein Rückbau muss Unit, App-Liste und
Helferstand zusammen behandeln.

Persistenz erfolgte mit dem distributionsseitigen `overlayroot-chroot` und
identischen Dateien im laufenden Overlay. Danach wurde die Root-Unterlage
wieder RO und die Bytegleichheit beider Ansichten geprüft. Kein Neustart des
Pi oder des Loggers war nötig. Sicherung der vorherigen Dateien:
`/root/meteohub-native-eval-before-20261116`, auch auf der Root-Unterlage.
`manifest.json` benennt vorhandene/neu angelegte Dateien. Der Rückbau muss auch
den neu angelegten WantedBy-Link entfernen; alte Dateien und Konfiguration
nicht einzeln während laufender Sicherung zurückkopieren.

## Quellen im Repository und Installationsgrenze

Diese Veröffentlichung enthält die Steuerung, Unit-Vorlage und den dafür
benötigten RAM-Helfer einschließlich seiner Testabhängigkeit
`tools/check-ram-reboot.py`. Sie ist kein neues Ein-Klick-Installationspaket.
Auf .50 bestehen bereits der RAM-Aufbau, der Wartungshelfer mit Freeze/Thaw
und die originale ARM-Laufzeit. Der Basis-RAM-Helfer allein ersetzt den
installierten Freeze-Checkpoint nicht; dessen vorhandener Service-Drop-in
bleibt erforderlich. Seine `apps`-Liste liefert die zu stoppenden bzw.
einzufrierenden Dienste.

Bei einer Übertragung müssen der originale Auswerter und der Shell-Einstieg
`wmr928fulleval` ausführbar installiert werden (0755). Unit, Bind-Pfade,
App-Liste, Helfer-Hash und Autostart sind gemeinsam abzugleichen. Ein
`git pull` installiert keine dieser Hoständerungen. Die beschriebene
Live-Abnahme gilt für .50; sie ist keine allgemeine Installationsfreigabe für
andere Systeme.

## WAN-IP

Der native Aufruf fragt
`http://www.meteohub.de/cgi-bin/showipnew.pl` ab und folgt dessen HTTPS-Redirect.
Die private DNS-Datei zeigte zuvor auf einen nicht vorhandenen DNS-Dienst an
127.0.0.1; außerdem durfte der Webdienst nur Loopback erreichen.

Der dauerhafte Drop-in
`/etc/systemd/system/meteohub-web-test.service.d/70-wan-ip.conf` bindet die
Host-DNS-Konfiguration ein und erlaubt DNS an `44.149.114.1` sowie den aktuell
aufgelösten Herstellerhost `65.108.64.76`. Übrige Netzbeschränkungen bleiben.
Vorlage: `tools/native-wan-pi50.conf`. Falls sich DNS-Server oder Hersteller-IP
ändern, diese Freigaben nach erneuter Auflösung aktualisieren. Es gibt dafür
keinen automatischen DNS-Refresh der Firewallfreigabe.

Die unveränderte Herstellerantwort enthält neben der öffentlichen IP weiteren
Payload. Dieser wurde weder durch eine erfundene Antwort ersetzt noch öffentlich
protokolliert. Tatsächliche CGI-Ausführung im Web-Mountnamespace, als UID 1000
und im Netzwerkfilter-Cgroup des Webdienstes zeigt `178.208.98.198` statt
`no internet access`. Nur der Webdienst wurde neu gestartet. LAN-Freigabe ist
separat beschrieben in [Webzugriff](web-access-pi50.md).

## Nachweise und Grenzen

- Isolierte Datenkopie: originale Programme erfolgreich ausgeführt, 84
  Aggregat-/Historiendateien erzeugt; vollständiger Testlauf rund 14 Sekunden
  bei 50 % CPU-Limit. Einzelne Dateien dürfen für noch nicht abgeschlossene
  Zeiträume leer sein, etwa der laufende Monat.
- Laufende Installation: Vollberechnung um 21:07:16 MEZ abgeschlossen; native
  Seite zuvor `in progress`, anschließend `completed`, Logger `last data: 3 sec`.
- Beispiele: 2.535 Wind-Fünf-Minuten-Werte, 215 Temperatur-Stundenwerte und
  neun Daten-Tageswerte. Keine synthetischen Erfolgsanzeigen.
- Roharchiv-Präfix von 3.247.604 Bytes vor/nach Auswertung identisch;
  SHA-256 `c4fc06aabee3a47f2927fc4e7916379d5791faaac4bb7387b41fac9f457a5aa2`.
- Testcheckpoint 21:05:38–21:05:42 MEZ: Freeze/Thaw des neuen Dienstes im Journal,
  Sicherung erfolgreich, Logger-PID unverändert 168089. Keine fehlgeschlagenen
  Units; Root-Unterlage/Boot/Persistenz RO. Sechs-Stunden-Takt unverändert.
- Abschlussprüfung 21:11:34: erneuter Checkpoint erfolgreich, fünf Apps aktiv,
  neuer Wind-Fünf-Minuten-Datensatz 20:00 UTC vorhanden (2.536 Zeilen),
  neue Rohdaten und Index ohne Rückstand. Testkopie anschließend entfernt.
- Vier gezielte Worker-Tests bestanden; RAM-Helfertests: drei bestanden, ein
  umgebungsabhängiger Test übersprungen. Dies ersetzt keinen Boot-Test.
- Dauerhafte Dateien/Autostart verifiziert; ein erneuter Pi-Boot wurde bei
  diesem Eingriff nicht durchgeführt und bleibt als Boot-Abnahme offen.
- **Separater Quelldatenbefund:** `thb0`-Aggregate bleiben beim Originalauswerter
  leer. Der anschließende [isolierte Vergleich um 21:35–21:38 MEZ](thb-analysis-2026-11-16.md)
  grenzt die Ablehnung auf das dritte THB-Messwertfeld ein, das der Auswerter
  als Taupunkt anders skaliert als das Temperaturfeld. Die ursprüngliche
  Temperaturvermutung allein ist damit widerlegt. Keine Testwerte wurden
  produktiv übernommen; eine Druckauswertung ohne erfundene Klimawerte bleibt
  offen. Siehe auch [Druckkanal](feed-recovery.md).

Private Installations-/Abnahmebelege auf .34:
`/var/local/meteohub-private/wan-recompute-20261116/`. Vollständige native
Konfiguration und Lizenzdaten bleiben privat.
