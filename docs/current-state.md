# Arbeitsstand und Fortsetzung – 9. November 2026

**Betriebsnachweis unserer Beispielstation, keine allgemeine Installationsvorgabe.**
Diese Notiz hält den zuletzt vom Betreiber gemeldeten Stand fest. Sie ist keine
automatisch aktualisierte Überwachung. Allgemeine Schritte stehen im
[Installer](installer.md), die individuellen Sensorentscheidungen im
[Stationsbeispiel](station-example.md).

## Fortsetzung 9. November morgens: RAM auf dem Pi installiert

**RAM-Installation auf dem Pi belegt; Host-Root und Boot weiterhin RW.**
Der neue Meteohub-Pi ist 44.149.114.50, Quelle weiterhin 44.149.114.9:5500.
Der Betreiber fuehrt alle Zielbefehle selbst aus. Lokale Commits erlaubt,
weiterhin **kein GitHub-Push**.

Neuester Betreiberbeleg nach Installation (Statusalter etwa vier Sekunden):

- Uebertragene `ram-storage.py` gegen SHA256
  `c59e978afc1eaa7164db7c802e1437d49154cd00417fbb98963da677caa9cbdf` geprueft.
- `installed=true`, `root_ro_changed=false`; aktive und gesicherte Generation
  `gen-a0557598d211441997b6ccad9a9be568` identisch.
- RAM-Belegung 2772992 von 335544320 Bytes; `needs_attention=false`.
  Datenpartition RO, alle vier Anwendungsunits aktiv.
- Beide RAM-Timer gelistet; Kalenderdarstellung im Terminal abgeschnitten.
  Vollstaendige naechste Ausloesezeiten noch ausgeben lassen.
- Noch OFFEN: echte neue Archivwerte nach RAM-Umschaltung, manueller Checkpoint
  mit Wiederanlauf, Wiederherstellung nach Pi-Reboot und Host-Root-/Boot-RO.
  Installationsstatus ersetzt keinen Empfangs- oder Wiederherstellungsnachweis.

Vorherige Nachweise vom Vorabend / etwa 00:05 CET:

- Offline-SD-Image auf Proxmox .60: `/root/meteohub-sd-vor-ro-juN2kxBj/karte.img`,
  31914983424 Bytes, SHA256
  `89148f69b230f0a8237d3eb3d2066a30738a19a8d27d4c301680ea21d452b47f`.
  Abbild gegen vollstaendig erneut gelesene Karte verglichen. Kein Image-Restoreboot getestet.
- Root ext4 auf 12 GiB verkleinert, geprueft und mehrfach erfolgreich gebootet.
  Boot- und Root-Kennungen unveraendert; Root und Boot weiterhin RW.
- Neue Datenpartition 17,2 GiB, UUID `6d332cf5-8a19-4fc5-bcaa-5156ab2dad54`,
  unter `/srv/meteohub-persist` RO gemountet. fstab geprueft und eingetragen;
  Sicherung `/root/meteohub-mount-before-7i3Nc6mZ/fstab`.
- Zeit-Startsperre installiert: Logger nach NTP statt davor. Echter Bootbeleg:
  Zeitsynchronisation bei 36,629 s, Loggerstart bei 36,642 s, keine Neustarts.
- Ausgangssicherung mit echtem Restore und SQLite-Pruefung:
  `/srv/meteohub-persist/snapshots/initial-F2ffNYMd`.
- Neueste Betreiberstatusausgabe etwa 00:05 CET: alle Anwendungsdienste aktiv,
  NRestarts=0, 4161 Datensaetze seit Live-Installation, keine ungueltigen Zeilen
  oder Ersetzungen. Frische Wind-/Druck-/Temperatur-/sonstige Messwerte nach
  Sicherungspause, rain0 um 23:38:46 CET noch im stundenweisen Intervall.
  Keine neue Live-Pruefung zum Zeitpunkt dieses Dokumentationscommits.
- RAM: 905 MiB gesamt, 733 MiB verfuegbar; ZRAM ohne SD-Backing, Swap unbenutzt.
  Runtime-Daten etwa 6,8 MiB. `auto_initramfs=1`, initramfs-tools
  `0.148.4+rpt2`, raspi-config `20261026+2`; overlayroot nicht installiert.

Werkzeugstand und lokale Vorpruefung:

- `tools/ram-storage.py`: begrenztes RAM-Overlay, gepruefte Generationen,
  taegliche Sicherung 04:15 Europe/Berlin, Shutdown-Sicherung, Rebase,
  Kapazitaetspruefung und Rueckbau. Details: [RAM-Sicherung](ram-storage.md).
- Echte lokale Mount-/systemd-Tests einschliesslich vollem RAM, Fehlerpfaden,
  schlechter Sicherung, Shutdown/Restore und Rueckbau bestanden. Kein nativer
  ARM-Empfangs-/Pi-Rebootnachweis durch diese Tests.
- Aktualisierter Live-Helfer verhindert `live-remove` bei installierter
  RAM-Speicherung; dieser Helferstand ist auf dem Pi noch nicht nachgewiesen.
  Dort kein `live-remove` verwenden. Keine neuen Skripte per git pull voraussetzen.

Am Morgen wurde zusaetzlich die vollstaendige Installationstransaktion lokal
ausgefuehrt: injizierter Fehler beim Start der RAM-Unit mit Ruecknahme der
Konfiguration und Wiederanlauf der Anwendungen, danach erfolgreiche Installation
einschliesslich Timer und erneuter vollstaendiger Rueckbau. Echte temporaere
ext4-/tmpfs-/Overlay-Mounts und systemd-Units; nur Pi-spezifische Hardware-
Vorpruefung und Stationsanwendungen durch Testfixtures ersetzt. Zusaetzlich
verhindert die Speicher-Sperre einen faelschlichen Gesundheitsfehler, wenn
Sicherung und periodischer Check gleichzeitig starten: Check wird explizit
ausgelassen. Keine Aenderung am Pi durch diese Laeufe.

**Naechster Schritt:** Echte neue Aufzeichnung im RAM abnehmen.
Manuellen Checkpoint, RO-Datenmount, frische Daten danach und
Wiederherstellung nach Reboot nachweisen. Erst anschliessend Host-Root-/Boot-RO
vorbereiten; vorher APT-Simulation fuer fehlendes overlayroot und dessen
Trixie-Konfiguration pruefen. Datenpartition muss ausserhalb des Host-Overlays
bleiben. Sicherungstimer ist installiert; ein automatisch ausgefuehrter
taeglicher Lauf ist noch nicht belegt.

## Historischer Nachweis: Regenübernahme am 8. November, Nachkontrolle 14:51 MEZ

Der Betreiber hat die gespeicherte Regenzuordnung über echten Empfangstest
in den neuen Dauerbetrieb übernommen. Der 302,15-s-Test schrieb 44 gültige
neue Roharchivzeilen aller acht Sensoren, darunter **rain0 um 14:38:47 MEZ**.
Das Anzeigeintervall ist jetzt 3600 s (Altersgrenze 7260 s). Anschließend liefen
Logger, Web und Indexer mit aktiviertem Autostart und ohne Neustarts.

Nachkontrolle des Betreibers um **14:51:30 MEZ**: 50 neue gültige native
Zeilen seit dieser Installation, 1463 zusätzliche Bytes, keine Formatfehler
oder Archiv-Ersetzungen. Alle Dienste aktiv, keine Neustarts. Der Index ist
bei allen acht Sensoren einschließlich `rain0` mit dem Roharchiv gleichauf
(jeweils 0 s Rückstand), ohne Indexfehler; letzter Indexlauf 2,7 s alt.

Der Betreiber bestätigt anschließend auf Nachfrage zu Dashboard und SVG:
**„ja, regenrate 0,0“**. Damit ist der Fehler bei der Regenübernahme einschließlich
Index und Anzeige behoben. Eine Rate von 0,0 ist ein gültiger Messwert.

Separat ausstehend bleibt der nächste stündliche Regenwert im Dauerbetrieb.
Der bisherige Regenwert
stammt um 14:38:47 MEZ aus dem Test; sein Alter von rund 13 Minuten ist bei
dieser stündlichen Quelle erwartbar. Nächster Wert ungefähr 15:38 MEZ,
zuzüglich Archivpufferung. Keine automatische Beobachtung eingerichtet.
Der begrenzte Test endete planmäßig mit Timeout; kein Dauerlogger-Absturz.

Diese Nachweise stammen aus der Betreiber-Ausgabe. Kein neuer Ferncheck,
Reboot oder lückenloser Langzeitnachweis. Details und aktuelle Sicherungen
stehen im [Stationsbeispiel](station-example.md#regen-ergänzung-am-08112026-nur-diese-station).
Die nachfolgenden älteren Abnahmezahlen stammen vom 7. November.

## Jetzt beibehalten

Der neue Pi 4 Model B mit 1 GB RAM läuft auf Raspberry Pi OS Lite Trixie ARM64
mit zusätzlicher ARMHF-Laufzeit. Die originale Meteohub-Anwendung ist **5.1e,
Build 277**. Der alte Stations-Pi bleibt die Datenquelle und wird nicht verändert.
Der Betreiber führt die Befehle auf dem neuen Pi selbst aus.

Der Empfang läuft dauerhaft und soll weiterlaufen:

```text
alter Meteohub / TCP-Stationsport → originaler loggerd → natives Roharchiv
                                                          ↓
                                                    Dashboard / SVG
```

Kein JSON-Collector und kein eigenes Eingangsplugin im aktuellen Datenweg.
Die früheren Plugin-/Feed-Dateien sind für diesen Weg unbenutzt. Keine parallelen
Leser am Stationsport und insbesondere kein zweiter `cat` an der alten seriellen
Konsole starten. `direct-test` und `native-test` während der Live-Installation
nicht ausführen; die Helfer blockieren diesen Parallelbetrieb.

## Installierter Stand

- Live-Installer: Commit `fdb2e7d`; Dokumentationsnachträge erfolgten danach.
- `meteohub-live.target`: für Boot aktiviert.
- `meteohub-live-logger.service`: nativer direkter TCP-Empfänger.
- `meteohub-live-runtime.service`: geteilter flüchtiger Prozesszustand in `/run`.
- `meteohub-web-test.socket` / `.service`: trotz des beibehaltenen Namens jetzt
  dauerhafte Units, Weblistener ausschließlich `127.0.0.1:18090`.
- `meteohub-dashboard-index.service`: dauerhafter abgeleiteter Indexer.
- Roharchive, Konfiguration, native Logs und SQLite liegen weiterhin auf SD.
  **Kein RO-System, kein RAM-Wetterarchiv und kein täglicher Sicherungstimer.**
- ZRAM ohne SD-Backing wurde zuvor nach Neustart nachgewiesen.

Die wesentlichen Pfade, relativ zum Homeverzeichnis des Anwendungsbenutzers:

| Pfad | Zweck |
| --- | --- |
| `src/meteohub` | Git-Checkout; Benutzerbefehle hier ausführen. |
| `meteohub-staging/5.1e-openssl3` | Geprüfte private ARM-Anwendungsdateien. |
| `meteohub-staging/5.1e-runtime/root` | Private Laufzeitumgebung. |
| `meteohub-staging/5.1e-runtime/root/data/weather/YYYYMM/raw` | Maßgebliches natives Monatsarchiv. |
| `meteohub-staging/5.1e-runtime/root/data/log/meteohub.log` | Natives Loggerprotokoll. |
| `meteohub-staging/5.1e-runtime/root/data/dashboard` | Abgeleitete SQLite-Daten und Indexstatus. |
| `meteohub-staging/5.1e-runtime/live/logger.conf` | Feste aktive Logger-Konfigurationskopie; CGI-Save ersetzt sie nicht. |
| `meteohub-staging/5.1e-runtime/live-install.json` | Installationsnachweis, Unit-Prüfsummen und Archiv-Ausgangsstand. |
| `meteohub-staging/live-before-rtn3ctii` | Bei dieser Station gemeldete Sicherung vor Live-Installation. |

Eine Sicherung vor dem Neustart wurde angewiesen; deren erzeugter Verzeichnisname
wurde nicht zurückgemeldet. Bei Bedarf auf dem Ziel nach
`/root/meteohub-before-reboot-*` sehen und den Inhalt prüfen, nicht deren Existenz
oder Vollständigkeit voraussetzen. Private Sicherungen und Zugangsdaten gehören
nicht in Git.

## Was tatsächlich bestätigt ist

1. Direkter ARM-Test mit frischen nativen Daten aller sieben zugeordneten IDs.
   THB ist vollständig im Roharchiv enthalten; die geprüfte Zeile enthielt
   981,6 hPa Stationsdruck und 1021,1 hPa reduzierten Druck.
2. Nach Live-Installation aktive Dienste und 23 neue native Archivzeilen,
   ohne Formatfehler oder unerwartete Archiv-Ersetzungen.
3. **Echter Pi-Neustart am 7. November um 14:59:47 CET.** Loggerstart im Journal
   zum selben Zeitpunkt. Danach waren Logger, Web und Indexer aktiv,
   `NRestarts=0`, Boot weiterhin aktiviert und keine fehlgeschlagenen Units.
4. Status danach: 77 Zeilen seit Installation, nicht seit Boot. Wind sowie
   `data0`, Solar, UV und `t2` hatten ausdrücklich Archivzeitstempel nach Boot.
5. Die späteren Daten der zuvor ausstehenden Sensoren `t1`/THB bestätigte der
   Betreiber mit „daten sind da“. Dafür wurde kein zusätzlicher Statusdump oder
   Roharchivzeitstempel vorgelegt. Beim nächsten Check konkret nachprüfen.

Vollständige Ausgaben und Grenzen sind im
[Dauerbetriebsprotokoll](continuous-operation.md#erster-dauerbetriebsbefund-unserer-beispielstation)
beschrieben. Kein Nachweis eines lückenlosen 24-Stunden-Betriebs bislang.

## Als Nächstes – ohne erneute Installation

Nachtrag zur Druckanzeige: Bei etwa vier Minuten alten Werten meldete der
Betreiber am 7. November fehlenden Luftdruck in Dashboard/SVG. Die Anzeige
verwendet ohne Sensorintervallkonfiguration eine Drei-Minuten-Grenze; dieses
Verhalten wurde mit echten API-/SVG-Aufrufen und synthetischen Archivdaten
reproduziert. `tools/dashboard-interval.py` erlaubt die gemeinsame Einstellung
für beide Ansichten. Für unsere Station ist `--sensor thb0 --interval 300`
vorgeschlagen; auf dem Pi noch nicht angewendet/bestätigt. Details im
[Installer](installer.md#messintervalle-für-dashboard-und-svg). Ein reiner
Anzeigefix ersetzt nicht die ausstehende Prüfung der Archivverzögerung.

### 1. Weiterlauf und Langzeitdaten prüfen

Als normaler Anwendungsbenutzer:

```bash
cd "$HOME/src/meteohub"
python3 install-pi.py live-status
```

Alternativ aus der Root-Shell unserer Beispielstation:

```bash
sudo -H -u meteohub -- /bin/bash --noprofile --norc -c '
set -e
cd "$HOME/src/meteohub"
python3 install-pi.py live-status
'
systemctl --failed --no-pager
journalctl -b -u meteohub-live-logger.service --no-pager -o short-iso -n 80
```

Kein `live-install` und kein `live-resume` nötig, solange der bestehende Dienst
läuft. Den SSH-Tunnel für Browserzugriffe wie in der Betriebsanleitung öffnen;
Dashboard und SVG bleiben authentifiziert.

Für eine vollständige 24-Stunden-Betrachtung ab dem geprüften Boot frühestens
am **8. November 2026 um 14:59:47 CET** auswerten. Nicht nur Summenzähler oder
letzte Zeilen ansehen: den gesamten Prüfzeitraum anhand der echten
Sensorintervalle mit dem nativen Archiv vergleichen. Dienstneustarts,
Verbindungsfehler, Lücken und die eingeplante Reboot-Unterbrechung unterscheiden.
Aktuelle Werte und Quellen im Dashboard/SVG ebenfalls abgleichen. Es läuft
keine automatische Alarmierung oder vollständige Lückenüberwachung.

### 2. Verzögerung zwischen Liveansicht und Roharchiv eingrenzen

Die native Sensors-Seite zeigte Werte im Sekundenbereich; die Statusabfragen
zeigten Archiv-Alter von etwa 86–205 Sekunden, später bis 375–376 Sekunden für
`t1`/THB. Ursache offen: mögliche Archivpufferung, tatsächliche Sensorintervalle
und Empfangslücken nicht gleichsetzen. Zeitgleich Live-Alter, native
Archivfortschritte und Logs aufnehmen; erst daraus eine Änderung ableiten.
`records_added=0` im Indexstatus betrifft nur den letzten Indexdurchlauf und
ist allein kein Beleg für ausgefallenen Empfang.

Später meldete der Betreiber gleichzeitiges Ausblenden von Wind, Temperatur,
Solar und UV nach drei Minuten. Ein davor gelieferter Status zeigte weiterhin
Archivwachstum (534 Zeilen seit Installation), aber nicht diesen Fehlerzustand.
Mit `python3 tools/observe-archive.py "$HOME/meteohub-staging/5.1e-runtime"`
vier Minuten lang Archivgröße, letzte Rohzeitstempel und Indexzeitstempel
gleichzeitig lesen. Kein weiterer Stationsport-Leser, keine Änderungen am
Logger. `index_behind_raw_s=0` bedeutet nur gleichen letzten Zeitstempel;
wenn beide Alterswerte gemeinsam wachsen, entsteht die Verzögerung bereits
vor dem Index. Eine stille Quelle und Loggerpufferung sind damit noch nicht
voneinander unterschieden. Nur aktueller UTC-Monat und letzte 256 KiB werden
untersucht; kein vollständiger historischer Lückentest.

Beobachtung des Betreibers vom 7. November, **15:06:47 bis 15:10:47 UTC**:
In jeder Probe waren Archiv- und Indexzeitstempel gleich; Indexläufe lagen
jeweils unter zehn Sekunden zurück, ohne Fehler. Das Roharchiv blieb bei
22.275 Bytes stehen, wuchs dann einmal um 733 Bytes auf 23.008 Bytes; der Index
übernahm 25 Zeilen. Danach blieb die Datei bis zum Ende unverändert (letzte
Schreibänderung 193,5 Sekunden alt). Wind erreichte 193,5, schnelle andere
Kanäle bis 238,5 Sekunden Messalter. Damit ist die Verzögerung vor dem Index
belegt. Ob native Loggerpufferung oder die vorgelagerte Lieferung sie verursacht,
ist noch nicht durch Mitschnitt am Prozess nachgewiesen. Kein Eingriff am
Original-Pi und kein zusätzlicher Leser am Stationsport.

Anzeige-Anpassung vorbereitet: getrennte Archivverzögerung von 240 Sekunden
konfigurierbar, ergibt bei Standard-Sensorintervall 60 Sekunden insgesamt
360 Sekunden Altersgrenze. THB/t1 mit 300 Sekunden Sensorintervall bleiben bei
660 Sekunden. Keine Zeitstempelumschreibung; weitere Verzögerungen können
weiterhin sichtbar veralten. Echte API-/SVG-Tests prüfen die Beobachtung mit
vier Minuten alten Werten, weiterhin wirksame Ablaufgrenzen und Indexausfall.
Der Betreiber hat die Installation von Commit `53874a3` auf dem Pi bestätigt:
`extension-update` erfolgreich, persistenter Indexer wieder aufgenommen,
Bootkonfiguration erhalten. Anschließend `t1` auf 300 Sekunden und die
Archivverzögerung auf 240 Sekunden gesetzt; die bestehenden Sensorintervalle
blieben erhalten. Erweiterungskennung:
`cc70c15689c3b729b04fdddd5606764e1c80c38f91b2c6e8363d2786b553c769`.
Die Wirkung in Dashboard und SVG über den nächsten Archivzyklus ist noch
zu bestätigen. Dies ist keine Behebung oder abschließende Ursachenklärung
der vorgelagerten Lieferverzögerung. Siehe
[Anleitung](installer.md#messintervalle-für-dashboard-und-svg).

### 3. Native MAC-/Netzwerkwarnung diagnostizieren

Noch offen:

```text
Error ifconfig read eth0 mac address: Function not implemented
Network Interface not correctly configured.
```

Der direkte Empfang funktioniert trotz dieser Meldung. Die konkrete Ursache
ist nicht belegt. Keine reale IP-/MAC-Änderung aus dem Hinweis auf die alte
Fallback-Adresse ableiten. Gezielte Diagnose der alten ARM-Anwendung in der
Sandbox vorbereiten; der Betreiber führt nötige Zielbefehle aus.

### 4. Danach weitere Betriebsfunktionen

Native Aggregation, historische Diagramme und Exporte auf diesem Pi sind nicht
vollständig abgenommen. Die feste Sensorquellenwahl der Anzeige ist als
stationsspezifische Softwaregrenze dokumentiert. Anschließend RO-/RAM-Konzept,
tägliche geprüfte Sicherung und Wiederherstellung umsetzen; nicht unter einem
laufenden Root-Overlay dessen unteres Dateisystem ändern. Lokaler USB-Umzug und
Abschaltung des alten Pi bleiben getrennte spätere Schritte.

## Rückweg nur bei Bedarf

`live-stop` hält die Dienste an und deaktiviert Boot; `live-resume` aktiviert
beides wieder. `live-remove` baut die unveränderten persistenten Units zurück
und stellt die temporäre private Web-/Indexumgebung wieder her; der Logger
läuft danach nicht. Roharchive bleiben erhalten. Details und Konfigurationsweg
stehen in [Dauerbetrieb und Autostart](continuous-operation.md).

Weitere Repository-Änderungen weiterhin allgemein dokumentieren. Unsere
Stationsdaten und Betriebsnachweise ausdrücklich als Beispiele kennzeichnen.
