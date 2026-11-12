# Vorbereitung für den Morgen des 12.11.2026

Status am **12.11.2026, 08:13:34 MEZ**: vom Betreiber auf .50 installiert und
nach Rückkehr zum Host-Overlay geprüft. Dauerhafte SSH-/Zeit-Statusanzeige und
native Last-data-Anzeige sind nach dem Neustart bestätigt. Der erste manuelle
Freeze-Checkpoint im Installer war erfolgreich; der nächste automatische
6h-Lauf und seine Auswirkungen auf Messwertlücken bleiben **OFFEN**.

Die Zielnachweise stammen aus den vom Betreiber übermittelten Konsolen- und
CGI-Ausgaben, nicht aus einer eigenen aktuellen SSH-Abfrage. Die nächtliche
Vorbereitung änderte keine Dienste auf dem Pi.

## Zielabnahme am 12. November

- Download mit SHA256 geprüft; `prepare`, Wartungsboot, `apply` und erneuter
  Overlay-Boot durchgeführt. Rückwegsicherung:
  `/root/meteohub-morning-before-7jutpit6`.
- `apply`: private native PID-/ps-Sicht bestanden, Logger-PID unverändert,
  erster ruhiger Checkpoint erfolgreich. Der Original-Logger hatte bereits
  selbst `logger.dat` geschrieben (Alter 3,7s).
- `check` nach dem zweiten Boot: permanente Dateien einschließlich RO-Unterlage,
  Host-Overlay, Statuspfade, alle vier Anwendungen, Archivpräfix und 6h-Plan
  bestanden. Keine fehlgeschlagenen Units gemeldet. Aktive/gesicherte Generation
  `gen-5c2a7622b9444417bc196090681444d8`, RAM 6.959.104 von 335.544.320 Bytes,
  Sicherungsalter 61,2s. Die native Datei fehlte bei diesem frühen Check noch;
  die Ausgabe ließ deren Prüfung ausdrücklich offen.
- Folgeprüfung 08:11:18 MEZ: Statusverzeichnis UID/GID meteohub, Modus 0700;
  Datei enthält `1794467471` = 08:11:11 MEZ. Damit schreibt der Original-Logger
  die flüchtige Datei auch nach einem neuen Boot. Keine synthetischen Werte.
- Archivbeobachtung zu diesem Zeitpunkt: 1.554.305 Bytes, letzte Schreibung
  242s alt, keine Lesefehler. Der Index lag je Sensor noch bis 300s hinter dem
  Roharchiv, zuletzt 2.000 Datensätze hinzugefügt. Das passt zum Startimport;
  vollständiges Aufholen und lückenlose neue Archivierung sind damit allein
  noch nicht nachgewiesen.
- Native Systemseite um **08:13:34 MEZ**: `Weather Data Logging: running
  (last data: 9 sec)`, `SSH Login: running`, `Time Synchonization: running`,
  `SMB Shares: stopped`. Keine bisherigen PID-Datei-Fehlermeldungen, Aktivierung
  weiter `activated`. SMB bleibt korrekt gestoppt, da kein Dienst installiert ist.

### Noch offen

Der nächste planmäßige Lauf ist am 12.11. um **13:00 MEZ / 12:00 UTC**.
Danach sind Sicherungserfolg, Writer-PIDs/Verbindungsfortbestand, RO-Zustand und
Sensorabstände über den Sicherungszeitpunkt zu prüfen. Ein erfolgreicher
Installer-Checkpoint ersetzt diese Betriebsabnahme nicht. Keine automatische
Hintergrundbeobachtung eingerichtet oder zugesagt.

Die native Anzeige `WAN IP: no internet access` ist separat ungeklärt; sie
beweist allein keinen allgemeinen Internetausfall. Historische Diagramme,
Recomputation und Exporte sind mit dieser Statusprüfung nicht abgenommen.

## Änderungen

1. **Echte SSH-/NTP-Statusanzeige dauerhaft:** Der bisher temporäre Adapter wird
   als eigene persistente systemd-Unit installiert. Er veröffentlicht echte
   PIDs der Host-Dienste und nur einen höchstens 30 Sekunden alten Zustand
   desselben Boots. NTP gilt nur mit bestätigter Synchronisation als aktiv.
   Samba bleibt ohne Dienst `stopped`. `ProtectProc=invisible` bleibt bestehen;
   fremde Host-Prozesse werden nicht allgemein sichtbar. Ein Start-Hook der
   gemeinsamen Runtime erzeugt die benötigten symbolischen PID-Verweise nach
   jedem Boot neu. Der Adapter startet keine SSH-, SMB- oder NTP-Server.
2. **Native `last data`-Datei ermöglichen:** Ein fehlendes Verzeichnis
   `/run/meteohub-live-1000/meteohub` wird als UID/GID 1000, Modus 0700 erstellt
   und beim Boot erneut bereitgestellt. Der originale Logger schreibt seine
   eigene `logger.dat`; der Installer schreibt weder diese Datei noch einen
   künstlichen aktuellen Zeitstempel. Existierende native Werte bleiben erhalten.
3. **Sicherung ohne regulären Verbindungsabbau:** Die drei schreibenden
   Anwendungscgroups werden kurz eingefroren. Kopie, SQLite-WAL-Konsolidierung
   der Kopie, Hashvergleich und Veröffentlichung der Sicherung erfolgen bei
   angehaltenen Schreibern. Anschließend werden dieselben Prozesse fortgesetzt.
   Die bestehende TCP-Verbindung bleibt dabei auf Clientseite erhalten.
   Ein Gegenstellenabbruch ist damit nicht grundsätzlich ausgeschlossen.
   Das laufende Overlay wird nicht bei jedem Checkpoint neu aufgesetzt. Somit
   entfallen auch die dadurch ausgelösten vollständigen Index-Neuimporte.

Der unveränderte RAM-Helfer wird geladen, aber nicht ersetzt. Originale
ARM-Programme, Aktivierung, Stationskonfiguration und 6h-Zeitplan bleiben
unverändert. Nur für den regulären Checkpoint wird ein neuer ExecStart über
zusätzlichen Drop-in verwendet. Die normale Shutdown-Sicherung bleibt erhalten.

## Ursache der nativen Anzeige

Statische Prüfung der vorhandenen privaten 5.1e-Binaries:

- CGI SHA256 `88d3bea39a66756c258ad52e11b2f12da2fc50a74def88b09ab7e0f2b9c5d1a6`:
  ARM-Adresse `0x6e6b0` lädt den Pfad `/var/run/meteohub/logger.dat`, öffnet ihn
  lesend und liest `%ld`. Ohne Datei setzt der Code den Statuswert auf -1;
  ungültiger Inhalt ergibt 0. Die Systemseite formatiert daraus die letzte
  Datenzeit und verwendet bei fehlendem Wert `never`.
- Logger SHA256 `acc728deb3759fc45cce54cca0e6a5d40fe3f98ea8580d2e5296181ce29a0efb`:
  Pfadfunktion `0x15380` liefert standardmäßig denselben Dateipfad. Der
  Schreibpfad um `0x3bdcc` liest `time(NULL)`, öffnet mit `w`, schreibt `%ld`
  und schließt. Bei fehlgeschlagenem Öffnen springt er ohne diese Ausgabe
  zum Funktionsende (`0x3be0c` → `0x3be2c`).
- Die bisherige gemeinsame Runtime-Unit legt nur das äußere `/run`-Verzeichnis
  an. Ein frischer Boot kann daher den für den nativen Status benötigten
  Unterordner verlieren. Die Zielabnahme oben bestätigt nach Bereitstellung des Unterordners
  das Schreiben durch den Original-Logger und die korrekte CGI-Anzeige.

Keine native Binärdatei ist im Download oder Commit enthalten.

## Grenzen und Absicherung der ruhigen Sicherung

- Der Snapshot enthält den **bereits ins Dateisystem geschriebenen Zustand**.
  Userspace-Puffer des Loggers werden durch Freeze nicht geleert. Ein geordnetes
  Herunterfahren verwendet weiterhin den alten Stop-/Flush-Pfad. Die Sicherung
  garantiert daher nicht, dass jede schon empfangene, aber noch gepufferte
  Messung enthalten ist. Der beobachtete Archiv-Schreibrhythmus betrug Minuten.
- Ein unabhängiger systemd-Timer fordert nach 25 Sekunden das Auftauen an. Der
  Zeitpunkt ist kein Echtzeitversprechen; einzelne systemctl-Aufrufe haben
  ebenfalls begrenzte Wartezeiten. Ein Deadline-Marker verhindert danach die
  Veröffentlichung einer ungeprüften Sicherung. Ein ExecStopPost räumt auch
  nach SIGKILL des Kopierprozesses auf. Markerzugriffe sind separat verriegelt.
- Vor Veröffentlichung müssen alle Writer noch eingefroren sein und dieselbe
  PID besitzen. Die Dateikopie muss zum Ausgangsbestand passen, die kopierte
  SQLite-Datenbank konsistent sein. Fehlversuche überschreiben die letzte
  verifizierte Referenz nicht, sofern sie vor Veröffentlichung erkannt werden.
  Ein späterer Fehler beim Auftauen oder Nachprüfen kann dagegen trotz bereits
  gültiger neuer Sicherung einen fehlgeschlagenen Dienstlauf ergeben.
- `active_generation` und `saved_generation` dürfen jetzt verschieden sein:
  die erste bleibt die Unterlage laufender Prozesse, die zweite ist die neueste
  Sicherung. Die aktive Unterlage wird beim Pruning ausdrücklich behalten.
- Ab 60 % belegtem RAM erfolgt wieder die bewährte Stop-/Copy-/Rebase-Sicherung.
  Dabei entsteht bewusst erneut eine kurze Verbindungspause. Der vorhandene
  80%-Kapazitätsalarm bleibt unverändert. Ein 6h-Intervall ist keine Garantie,
  dass überraschend schnelles RAM-Wachstum erst nach sechs Stunden auffällt.
- Das Paket beseitigt keine schon entstandenen Archivlücken und behauptet
  keine lückenlose Übertragung vom alten Meteohub.

## Installation auf .50

Der Installer erwartet den geprüften RAM-Helfer SHA256
`d588b4cefdba8a5dea26d9f96420651e19a29922ad9187a5b77753f51d2023ad`
sowie die festgelegten Root-/Boot-/Persistenz-UUIDs. Abweichungen führen zum
Abbruch. Keine Paketinstallation und keine Änderung an Netzwerk oder SSH.

Es sind zwei kontrollierte Neustarts nötig: hinein in den Wartungsmodus und
zurück zum Host-Overlay. Grund: Die Unterlage eines aktiven OverlayFS darf
nicht währenddessen verändert werden. Siehe
[Kernel-Dokumentation](https://kernel.org/doc/html/latest/filesystems/overlayfs.html).

1. Das separat ausgelieferte `meteohub-morning.py` herunterladen und den
   mitgelieferten SHA256 prüfen. Dann als root:

   ```sh
   python3 /root/meteohub-morning.py prepare && systemctl reboot
   ```

   Der vollständige Installer sowie Journal/Archivnachweis werden vorher auf
   der Bootpartition abgelegt. Nur nach erfolgreicher Sicherung wird die
   Bootoption auf Wartung gesetzt. Ein fehlgeschlagener Schritt rebootet nicht.

2. Nach erneuter SSH-Anmeldung:

   ```sh
   python3 /boot/firmware/meteohub-morning-20261112.py apply && systemctl reboot
   ```

   Der Installer wartet nötigenfalls auf die bereits eingerichtete NTP-Sperre.
   Er verweigert existierende fremde Zieldateien, sichert die bisherigen Units,
   installiert zusätzliche Dateien, startet nur den Webdienst neu und prüft
   die echte CGI-Prozesssicht. Anschließend führt er einen ruhigen Checkpoint
   aus und prüft unveränderte Logger-PID und Archivpräfix. Erst dann wird der
   Overlay-Boot wieder eingerichtet. Der Rückbau wird bei fehlgeschlagener
   erster Checkpoint-Abnahme automatisch versucht; Wartungsmodus bleibt aktiv.

3. Nach erneutem Login:

   ```sh
   python3 /usr/local/libexec/meteohub-maintenance-v1/maintenance.py check
   ```

   Prüft neue Boot-ID, persistente Dateihashes auch in der RO-Unterlage,
   Anwendungen, Archivpräfix, 6h-Plan und Web-Prozesssicht. `logger.dat` wird
   mit tatsächlichem Zeitstempel und Alter berichtet. Fehlt sie weiterhin,
   bleibt die native Last-data-Anzeige ausdrücklich **OFFEN**. Native Seite
   und frische Rohdaten nach dem Boot sowie der nächste reguläre 6h-Checkpoint
   sind getrennt abzunehmen. Kein erneuter pauschaler Fünfminutentest.

## Rückweg

Im laufenden Host-Overlay zunächst:

```sh
python3 /usr/local/libexec/meteohub-maintenance-v1/maintenance.py maintenance && systemctl reboot
```

Nach dem Wartungsboot:

```sh
python3 /usr/local/libexec/meteohub-maintenance-v1/maintenance.py rollback
```

Der Rückbau entfernt ausschließlich die eigenen systemd-Ergänzungen und
PID-Symlinks. Der unveränderte ursprüngliche Checkpoint gilt anschließend
wieder. Paket/Manifest/Sicherungsverzeichnis bleiben für Diagnose erhalten.
Das native Statusverzeichnis wird nicht gelöscht. Keine automatische Rückkehr
zum Overlay, bevor der Betreiber die Ursache geprüft hat. Bei verlorenem
Bootzugang kann auf der SD-Bootpartition in `cmdline.txt` allein
`overlayroot=tmpfs:recurse=0` durch `overlayroot=disabled` ersetzt werden.

## Prüfungen auf dem Entwicklungsrechner

```sh
python3 tools/test-host-status.py --isolation
python3 tools/test-morning-maintenance.py
python3 tools/test-quiet-checkpoint.py
```

Bestanden:

- echter geschützter systemd-Web-Prozessraum; echte Host-PIDs, Verweigerung alter
  oder fremder Boot-Snapshots, weiterhin verborgene andere Root-Prozesse;
- Bootoptionsprüfung, veränderter Archivpräfix, keine künstliche `logger.dat`,
  fremde PID-Dateien, vollständiger Startgraph ohne Abhängigkeitszyklus;
- echte ext4-/RAM-/Overlay-Dateisysteme, SQLite im WAL-Modus, laufender eigener
  TCP-Sender und Schreiber: eine Verbindung, identische PID und fortlaufende
  Sequenz nach Freeze-Snapshot, Snapshot mit gültiger SQLite-Datenbank;
- injizierter Kopierfehler: letzte Sicherung erhalten, alle Writer fortgesetzt,
  Persistenz wieder RO;
- unabhängiger Deadline-Timer und SIGKILL des Kopierers: Writer fortgesetzt,
  keine Veröffentlichung des verworfenen Versuchs;
- RAM-Druck: alter Stop-/Rebase-Pfad verwendet, danach Anwendungen wieder aktiv.

Dies ersetzt **keine** Abnahme des nativen ARM-Loggers, des Quellservers, der
Pi-SD-Leistung oder eines echten Ziel-Reboots. Die Vorbereitung hat weder
Dienste noch Mounts auf .50 geändert. Private vollständige Testprotokolle:
`/var/local/meteohub-morning-evidence-20261112/`.

## Ausgeliefertes Paket

Download: `http://44.149.114.34/meteohub-morning.py`

SHA256: `72549ea03eadc159ff13bcb7c6666b9070352a1cb6fae96315ae4b2157b58de1`

Der Download enthält ausschließlich die drei eigenen Python-Helfer. Der Builder
`tools/build-morning-bundle.py` erzeugt ihn deterministisch; derselbe Dateistand
muss denselben Hash ergeben. HTTP-Download und Hash wurden auf dem
Entwicklungsrechner gegengeprüft. Download und Hashprüfung auf .50 wurden
am 12.11. durch die Betreiber-Ausgabe bestätigt.
