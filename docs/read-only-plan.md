# Schreibgeschütztes System und tägliche Datensicherung

**Entwurf vom 7. November 2026; noch nicht aktiviert oder abgenommen.**
Der Betreiber möchte Betriebssystem und SD-Karte weitgehend schonen, flüchtige
Daten im RAM halten und frühmorgens täglich sichern. Der Installer schaltet
bislang absichtlich weder Boot noch Dateisysteme auf Read-only um.

## Warum nicht einfach `/` schreibgeschützt mounten?

Die aktuelle private Laufzeitumgebung benötigt Schreibzugriffe auf
`/home/meteohub` (Konfiguration und Logger-Konfiguration) und `/data`.
Beim älteren Plugin-Spiegelweg kommen `feed.json`, Cursor und Herkunftsprotokoll
hinzu; beim aktuellen direkten TCP-Weg entstehen diese Schreibzugriffe nicht. Der Dashboard-Indexer schreibt SQLite samt WAL und Status.
Der native Logger wird zusätzlich Roharchive, Status und Protokolle schreiben;
seine vollständigen Schreibpfade sind auf dem neuen Pi noch nicht abgenommen.
Diese Funktionen würden auf einer unverändert schreibgeschützten Installation
fehlschlagen.

Ein Root-Overlay kann Schreibzugriffe in RAM umleiten, benötigt aber einen
getrennten dauerhaften Datenspeicher. Ein nachträgliches Zurückkopieren in die
unter einem **laufenden** Overlay liegende Root-Partition ist kein zulässiger
Synchronisationsweg: Änderungen an zugrundeliegenden Dateisystemen während des
Betriebs sind laut [Kernel-Dokumentation](https://docs.kernel.org/filesystems/overlayfs.html#changes-to-underlying-filesystems)
nicht erlaubt; das Verhalten wäre undefiniert.

## Vorgesehene Aufteilung

- Betriebssystem/Boot schreibgeschützt im Normalbetrieb; Wartungsmodus für
  Paket-, Installer- und Konfigurationsänderungen.
- Begrenzte RAM-Verzeichnisse für kurzfristige Messwertpuffer, PID-Dateien,
  Status und begrenzte Logs. Kein komplettes historisches Archiv im RAM eines
  Pi mit 1 GB. Auch Swap auf SD wäre mit dem Ziel „keine laufenden SD-Schreibzugriffe“
  abzugleichen; ein tmpfs allein garantiert das nicht.
- Separater dauerhafter Datenbereich außerhalb des Root-Overlays, im Normalfall
  lesbar. Geprüfte tägliche Sicherung beispielsweise **04:15 Europe/Berlin**;
  dieser Zeitpunkt ist ein Vorschlag, noch kein eingerichteter Timer.
- Konfigurationsänderungen ausdrücklich dauerhaft speichern, damit ein Neustart
  neue Stationseinstellungen nicht verwirft.
- Messwerte aus RAM in eine neue abgeschlossene Sicherung schreiben, prüfen und
  synchronisieren; den letzten gültigen Stand erst anschließend ablösen. Bei
  Fehlern alte Sicherung und noch nicht gesicherte Messwerte behalten. RAM-Grenzen
  und fehlgeschlagene Sicherungen sichtbar melden, nicht still Daten löschen.
- Beim regulären Herunterfahren zusätzlich sichern. Bei Stromverlust ist das
  nicht möglich: tägliche Sicherung bedeutet im Normalfall bis zu 24 Stunden
  Datenverlust, bei fehlgeschlagenen Sicherungen entsprechend mehr.

Eine laufende SQLite-Datenbank samt WAL darf nicht unkoordiniert als einzelne
Datei kopiert werden. Dafür ist eine konsistente Sicherung über die
[SQLite-Backup-API](https://www.sqlite.org/backup.html) vorgesehen. Der Anzeigeindex
ist grundsätzlich aus Rohdaten wiederherstellbar; unersetzliche Messwerte und
Einstellungen haben Vorrang.

Eine zweite Partition auf derselben SD ist dabei kein Schutz vor einem Ausfall
der ganzen Karte. Ein zusätzliches externes Backup bleibt davon getrennt.

## Nächster Schritt: Bestandsaufnahme auf dem neuen Pi

Als normaler Benutzer, ohne Änderungen an Mounts oder Diensten:

```bash
cd "$HOME/src/meteohub"
git pull --ff-only
python3 install-pi.py storage-check
```

Das zeigt RAM/Swap, Dateisysteme, Partitionen und Größen der relevanten privaten
Datenverzeichnisse. Es ist noch keine Messung des täglichen Datenzuwachses.
Danach sind laufende Messwerterfassung, Datenwachstum und RAM-Grenzen zu prüfen.
Vor Boot-/Partitionsänderungen müssen Sicherung und konkreter Rückweg geprüft
werden. Eine bestehende SSH-Sitzung ist kein unabhängiger Wiederherstellungsweg.

Erst nach diesen Befunden werden RAM-Mounts, persistenter Datenbereich, Start- und
Sicherungsreihenfolge implementiert. Abnahme: frische Messwerte, konsistente
Sicherung, Wiederherstellung nach Neustart, neue SSH-Anmeldung, Betrieb bei
vollem RAM-Puffer und fehlgeschlagener Sicherung. Bis dahin keine erfolgreiche
RO-Umstellung behaupten.

## Erster Pi-4-Befund (7. November 2026, Betreiber-Ausgabe)

**Ab hier Betriebsnachweise und konkrete ZRAM-Schritte unserer Beispielstation.**
RAM-Größen, Geräte, Dateipfade und Paketbestand sind keine universellen Vorgaben.
Die ZRAM-Konfiguration setzt insbesondere das tatsächlich installierte Paket
`rpi-swap` voraus; sie ist keine allgemeine Debian-Swap-Anleitung.

- RAM: 905 MiB insgesamt, 707 MiB verfügbar, 197 MiB benutzt. Das ist eine
  Momentaufnahme vor dem nativen Dauerbetrieb, kein freigegebenes RAM-Budget.
- Aktiver Swap: `/dev/zram0`, 905 MiB logische Größe, 2,7 MiB belegt. Zusätzlich
  erscheint `loop0` mit 905 MiB und Swap-Signatur. Die nachfolgende Betreiberprüfung
  bestätigt `backing_dev=/dev/loop0` und dessen Datei `/var/swap` auf der
  Root-SD. `bd_stat` war `0 0 0`: noch keine Belegung/Lese-/Schreibvorgänge
  im aktuellen Statistikzeitraum. Writeback ist dennoch konfiguriert.
  Die ZRAM-Größe ist kein zusätzlicher physischer RAM.
- SD: Bootpartition 512 MiB und Rootpartition 29,2 GiB, beide RW. Ein eigener
  persistenter Datenbereich ist in der vorgelegten Partitionierung nicht vorhanden.
  Freie Extents sind damit noch nicht separat vermessen.
- Private Laufzeitdaten: 28 KiB belegter Platz, Wetterarchiv-Verzeichnis 4 KiB,
  TCP-Verzeichnis 4 KiB, private Anwendungskonfiguration 220 KiB.
  Dashboard-Verzeichnis noch nicht vorhanden. Kein belegter täglicher Zuwachs.
- `loop1` enthält das ursprüngliche Herstellerimage und ist nicht mit `loop0`
  zu verwechseln. Keines der Geräte zu Diagnosezwecken lösen oder deaktivieren.

Nächste rein lesende Prüfung auf diesem Pi:

```bash
cat /sys/block/zram0/backing_dev
cat /sys/block/zram0/bd_stat
sudo losetup --list --output NAME,BACK-FILE
```

`backing_dev` zeigt den konfigurierten Hintergrundspeicher; `bd_stat` dessen
Nutzung und Lese-/Schreibzähler. Erst zusammen mit dem Loop-Dateipfad lässt sich
feststellen, ob Auslagerungen die SD betreffen. Details:
[ZRAM-Writeback und Statistik](https://docs.kernel.org/admin-guide/blockdev/zram.html#writeback).
Ein momentaner Schreibzähler von null beweist nicht, dass Writeback deaktiviert ist.

## ZRAM ohne SD-Writeback vorbereiten

Für Systeme mit dem Raspberry-Pi-Paket `rpi-swap` ist `[Main] Mechanism=zram`
der vorgesehene Modus für komprimierten RAM-Swap ohne Hintergrunddatei. Die
[Herstellerdokumentation](https://github.com/raspberrypi/rpi-swap/blob/main/man/man5/swap.conf.5)
verlangt zur Anwendung der Änderung einen Neustart. Ein `daemon-reload` allein
stellt den aktiven Swap nicht um. Kein manuelles `swapoff`, Loop-Detach oder
Löschen einer noch benutzten Swapdatei im laufenden Betrieb.

Der folgende Schritt bereitet nur die Einstellung vor. Er setzt voraus, dass
`rpi-swap` installiert ist, lässt die Hauptkonfiguration unverändert und
überschreibt kein bestehendes eigenes Drop-in:

```bash
(
set -e
test "$(dpkg-query -W -f='${Status}' rpi-swap)" = "install ok installed"
sudo install -d -m 0755 /etc/rpi/swap.conf.d
sudo sh -c '
set -eu
set -C
printf "[Main]\nMechanism=zram\n" > /etc/rpi/swap.conf.d/90-meteohub-zram-only.conf
'
systemd-analyze cat-config rpi/swap.conf
)
```

Die zusammengeführte Konfiguration vor dem Neustart prüfen: Eine später sortierte
Datei kann die Einstellung wieder überschreiben. Dieser Befehl verändert noch
keine aktiven Swap-/Dateisystem-Mounts. Der reine ZRAM-Modus wird erst nach
Neustart abgenommen (`swapon --show`, `backing_dev`, `losetup --list`). Erwartet:
ZRAM aktiv, kein zugewiesenes Backing-Gerät. Nach Umstellung fehlt die zusätzliche
SD-Auslagerungsreserve; RAM-Limits und Messwertpuffer deshalb gesondert dimensionieren.

Rückbau der eigens angelegten Einstellung: ausschließlich
`/etc/rpi/swap.conf.d/90-meteohub-zram-only.conf` entfernen und erneut starten.
Die bisherige Hauptkonfiguration und andere Drop-ins bleiben dabei unverändert.
Bei diesem Zwischenstand gehen die temporären Web-/Indexer-Units beim Neustart
verloren; Wiederanlauf ist in [installer.md](installer.md#unterbrechen-wieder-aufnehmen-und-neustart)
beschrieben. Dies ist weiterhin keine vollständige RO-Umstellung.

## ZRAM-Abnahme nach Neustart (7. November 2026)

Die Betreiber-Ausgabe nach dem Neustart bestätigt:

- `/dev/zram0` aktiv mit 905 MiB logischer Größe und 0 B Belegung.
- `/sys/block/zram0/backing_dev` meldet `none`.
- `losetup --list` zeigt keine eingerichteten Loop-Geräte mehr.
- 722 MiB RAM verfügbar, 183 MiB benutzt; Momentaufnahme ohne Dauerlast.
- `systemctl --failed`: keine fehlgeschlagenen Units.

Damit ist **RAM-Swap ohne SD-Writeback** für diesen Start nachgewiesen. Daraus
folgt weder ein schreibgeschütztes Root-Dateisystem noch ein eingerichteter
RAM-Messwertpuffer oder täglicher Sicherungsjob. Diese Punkte bleiben offen.

Für die Fortsetzung die vorhandene 5.1e-Testumgebung als normaler Benutzer
mit `python3 install-pi.py web` starten. Ein erneutes Entpacken/Mounten des
Herstellerimages ist dafür nicht nötig. Danach den befristeten `feed-test`
mit der eigenen TCP-Quelladresse und `extension-update` ausführen. Der Test
prüft den Empfangsweg; dauerhafte native Archivierung und Tageszuwachs bleiben
noch gesondert zu messen.


## Wiederaufnahme am 8. November 2026

Der Betreiber hat die noch offene RO-Umstellung erneut aufgegriffen. Der
Dauerbetrieb mit nativem TCP-Logger, Regenarchivierung und Dashboard ist
inzwischen eingerichtet; die fruehere Bestandsaufnahme vor dem Loggerbetrieb
reicht nicht fuer die RAM-Dimensionierung. Dies ist ein Planungsstand, kein
neuer Live-Nachweis auf dem Pi.

Weiterhin offen: aktuelle Speicher-/Archivgroessen und Tageszuwachs,
vollstaendige Schreibpfade, begrenzter RAM-Puffer, dauerhafter Sicherungsbereich,
Sicherungs-/Wiederherstellungsverfahren, Timer, Wartungsmodus und RO-Abnahme.
Der Nachweis fuer ZRAM ohne SD-Backing vom 7. November bleibt ein historischer
Befund und wird vor der Umstellung erneut geprueft.

Naechster Schritt auf unserer Beispielstation, vom Betreiber ausgefuehrt:

```bash
sudo -H -u meteohub -- /bin/bash --noprofile --norc -c '
set -e
cd "$HOME/src/meteohub"
python3 install-pi.py storage-check
python3 install-pi.py live-status
printf "\nAktuelle Datengroessen:\n"
du -h --max-depth=1 "$HOME/meteohub-staging/5.1e-runtime/root/data"
printf "\nZRAM-Hintergrundspeicher:\n"
cat /sys/block/zram0/backing_dev
'
```

Keine neue Software muss fuer diese vorhandenen Lesebefehle geladen werden.
Die Ausgabe liefert eine Momentaufnahme, noch keinen gemessenen Tageszuwachs.
Bis zur Auswertung bleibt die laufende Erfassung unveraendert.
Ein konkreter Vor-Ort-/SD-Rettungszugang ist vor spaeteren Boot- oder
Partitionsaenderungen zu bestaetigen; reine SSH-Erreichbarkeit reicht dafuer
nicht. Die Frage nach diesem Rueckweg wurde dem Betreiber gestellt.

Die bestehende Vorgabe bleibt: Betreiber fuehrt Zielbefehle selbst aus;
Entwicklung und Dokumentation lokal, derzeit kein GitHub-Push. Die Sicherungszeit
04:15 Europe/Berlin ist weiterhin ein Vorschlag, kein eingerichteter Timer.


## Betreiberbefund vom 8. November, ca. 22:03 MEZ

Die angeforderten Lesebefehle wurden vom Betreiber ausgefuehrt:

- RAM 905 MiB, davon 704 MiB verfuegbar; ZRAM 905 MiB, 0 B belegt,
  `backing_dev=none`.
- Root ext4 und Boot vfat weiterhin RW; SD mit 512-MiB-Bootpartition und
  29,2-GiB-Rootpartition. Keine separate Datenpartition vorhanden.
- Laufzeitdaten 6.652 MiB (6.975.488 Bytes belegter Platz), davon Dashboard
  6.098 MiB, Wetterarchiv 488 KiB, alter TCP-Feed-Bereich 52 KiB.
  Private Anwendungskonfiguration 224 KiB.
- Logger, Web und Indexer aktiv, jeweils NRestarts=0; Autostart aktiviert.
  Seit Live-Installation 3.834 neue gueltige Rohzeilen (113.360 Bytes), alle acht
  Sensoren vertreten, darunter sieben Regenwerte; keine ungueltigen Zeilen,
  Trunkierungen oder Ersetzungen gemeldet. Kein Neustart seit Installation.
- Indexlauf erfolgreich; `records_added=0` ist nur der letzte Indexlauf,
  kein Nachweis eines Erfassungsausfalls. Diese Ausgabe ist weder ein
  vollstaendiger Lueckentest noch eine langfristige Speichermessung.

Die aktuellen Daten sind klein genug fuer weitere RAM-Puffer-Planung. Das
Dashboard haelt laut aktuellem Indexer 35 Tage Messwerte; seine jetzigen 6.1 MiB
sind daher kein belegter Maximalbedarf. SQLite-WAL, Archivwachstum, Logs und
Sicherungsspitzen muessen im RAM-Budget beruecksichtigt werden. Kein festes
kleines tmpfs-Limit allein aus dieser Momentaufnahme ableiten.

Die bestehende Sandbox macht insbesondere `/data` und `/home/meteohub`
schreibbar. Beide Bereiche sind bei der RAM-/Persistenzaufteilung zu behandeln;
`/run` ist bereits geteilter fluechtiger Prozesszustand. Die erlaubten
Schreibverzeichnisse ersetzen keinen Nachweis aller tatsaechlichen Schreibzugriffe.

Beim vorgesehenen Root-Overlay muss die persistente Sicherung ausserhalb seiner
unteren Root-Dateisystemschicht liegen. Eine eigene Datenpartition auf derselben
SD erfordert mit der aktuellen Aufteilung eine Offline-Vorbereitung; alternativ
kommt ein separates Speichermedium infrage. Diese Entscheidung und der konkrete
Rettungsweg stehen noch aus. Es wurden keine Mounts, Partitionen, Bootdateien,
Dienste oder Sicherungszeitplaene geaendert.


## Wiederherstellungsweg: Betreiber-Rueckmeldung am 8. November

Der Meteohub-Pi steht beim Betreiber und ist direkt erreichbar. Ein anderer
Linux-Rechner ist noch nicht festgelegt; als moeglicher Arbeitsplatz wurde der
Proxmox-Host .60 mit angeschlossenem SD-Kartenleser genannt. Zugriff auf den Pi
ist damit bestaetigt, Lesegeraet, Hostzugang, Datentraegeridentifikation und
Platz fuer ein vollstaendiges Kartenabbild sind noch nicht geprueft.

Vor dem Abschalten des Pi auf dem vorgesehenen Linux-/Proxmox-Host lesen:

```bash
lsblk -e 7 -o NAME,PATH,SIZE,TYPE,FSTYPE,MOUNTPOINTS,MODEL,TRAN,RM
findmnt -no SOURCE,FSTYPE,TARGET /
df -hT
```

Diese erste Ausgabe erfasst die vorhandenen Hostlaufwerke und moegliche
Sicherungsziele. Noch kein Formatieren, Partitionieren oder Kopierbefehl mit
vermutetem /dev/sdX. Die Karte spaeter nach sauberem Herunterfahren des Pi
anschliessen und die Laufwerksliste erneut vergleichen. Nicht aus der
Reihenfolge oder allein aus dem RM-Flag auf die SD schliessen.

Erst nach eindeutiger Zuordnung und geprueftem Sicherungsziel: vollstaendiges
Offline-Abbild der Karte samt Partitionstabelle, belegte Integritaetspruefung
und konkret dokumentierter Rueckschreibweg. Das Abbild enthaelt private
Konfiguration/Zugangsdaten und gehoert nicht in Git. Ein komprimiertes Abbild
kann kleiner sein; benoetigten Platz nicht allein anhand des belegten
Dateisystemplatzes zusagen. Partitionierung bleibt bis dahin unveraendert.


## Proxmox-Arbeitsplatz: erster Betreiberbefund

Auf dem vorgesehenen Host meldet der Betreiber vier leere USB-Kartenleser-Slots
(/dev/sda bis /dev/sdd, jeweils 0 B). Der SDXC-Slot erscheint derzeit als
/dev/sdc; dies ist noch keine Identifikation der spaeter eingesteckten Karte.
Das Hostsystem liegt auf NVMe/LVM, Root auf /dev/mapper/pve-root (ext4).
Root hat 76 GiB verfuegbar, ausreichend fuer ein unkomprimiertes Abbild der
zuvor gemeldeten ca. 29,7-GiB-SD mit Reserve. /tmp liegt auf tmpfs und ist
kein Sicherungsziel. Vorgesehen ist ein privates Verzeichnis unter /root.
Keine NVMe-, LVM- oder VM-Datentraeger fuer die Kartenarbeiten verwenden.

Naechster angeleiteter Schritt: auf dem Meteohub-Pi Diagnosejournal dauerhaft
sichern und sauber herunterfahren. Erst nach vollstaendigem Shutdown Karte
entnehmen, am Proxmox-Host einstecken und Laufwerke/Partitionen samt IDs erneut
anzeigen. Bisher kein Kartenabbild, keine Dateisystempruefung und keine
Partitionsaenderung erfolgt. Die Unterbrechung des neuen Meteohub beginnt mit
dem Shutdown; der alte Stations-Pi bleibt davon unberuehrt.
