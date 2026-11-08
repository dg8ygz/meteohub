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


## Eingesteckte Karte identifiziert, 8. November ca. 22:11 MEZ

Betreiberausgabe auf dem Proxmox-Host: SDXC-Leser jetzt 29,7 GiB, /dev/sdc,
Bootpartition 512 MiB vfat UUID B2F0-82D2, Rootpartition 29,2 GiB ext4 UUID
15f4c6be-1102-4331-9904-f78e78afd1fd. Beide Partitionen ohne Mountpunkt.
Leserpfad: `/dev/disk/by-id/usb-Generic_SDXC_MMC_0000000000000006-0:2`.
Dieser by-id-Pfad identifiziert den Leser; die Dateisystem-UUIDs werden daher
vor jeder Kartenoperation zusaetzlich geprueft. Host-NVMe/LVM bleibt unberuehrt.

Als naechster Schritt angeleitet: gesamte Karte schreibgeschuetzt lesen,
privates Vollabbild unter /root mit freiem Platz fuer Kartengroesse plus Reserve
erzeugen, Partitionstabelle sichern, Abbildgroesse vergleichen und SHA-256 von
Karte und Abbild unabhaengig berechnen und vergleichen. Bei Lesefehler abbrechen;
kein conv=noerror und kein Ueberspringen defekter Bereiche. Noch kein erfolgreicher
Backup-Nachweis vorgelegt. Kein fsck mit Reparatur und keine Groessenaenderung.

Die nachfolgende stationsspezifische Anleitung verwendet den bestaetigten
Leserpfad und beide UUIDs. Das Sicherungsverzeichnis wird neu angelegt;
`conv=excl` verhindert das Ueberschreiben eines vorhandenen Abbildes.
Die Kernel-Schreibsperre auf der Karte/ihren Partitionen wird fuer die Sicherung
gesetzt und nicht automatisch aufgehoben. Nach Umstecken muss sie erneut
geprueft werden.

```bash
(
set -euo pipefail
umask 077

karte=/dev/disk/by-id/usb-Generic_SDXC_MMC_0000000000000006-0:2
test -b "$karte"
test "$(blkid -s UUID -o value "${karte}-part1")" = B2F0-82D2
test "$(blkid -s UUID -o value "${karte}-part2")" = 15f4c6be-1102-4331-9904-f78e78afd1fd
test -z "$(lsblk -nro MOUNTPOINTS "$karte" | tr -d '[:space:]')"

bytes=$(blockdev --getsize64 "$karte")
test "$bytes" -gt 30000000000
test "$bytes" -lt 34000000000
sicherung=$(mktemp -d /root/meteohub-sd-vor-ro-XXXXXXXX)
frei=$(df -B1 --output=avail "$sicherung" | tail -n 1)
test "$frei" -gt "$((bytes + 2147483648))"

for geraet in "$karte" "${karte}-part1" "${karte}-part2"; do
  blockdev --setro "$geraet"
  test "$(blockdev --getro "$geraet")" = 1
done

sfdisk --dump "$karte" > "$sicherung/partitionen.sfdisk"
printf '%s\n' "$bytes" > "$sicherung/kartengroesse.bytes"
printf 'Sicherung: %s\n' "$sicherung"
dd if="$karte" of="$sicherung/karte.img" bs=4M iflag=fullblock conv=excl,fsync status=progress
test "$(stat -c %s "$sicherung/karte.img")" = "$bytes"

cd "$sicherung"
printf '\nPruefe Abbild und lese die Karte zum Vergleich erneut ...\n'
sha256sum karte.img > SHA256SUMS
sha256sum "$karte" > karte-original.sha256
test "$(awk '{print $1}' SHA256SUMS)" = "$(awk '{print $1}' karte-original.sha256)"
sync
printf '\nOK: Kartengroesse und SHA-256 stimmen ueberein.\nSicherung: %s\n' "$sicherung"
cat SHA256SUMS
)
```

Shellsyntax lokal geprueft; Ausfuehrung und Hashvergleich auf der .60 stehen aus.


### Korrektur des dd-Aufrufs

Erster Betreiberlauf legte `/root/meteohub-sd-vor-ro-UeIWJB9y` an, stoppte
jedoch bei der Optionspruefung von dd: `excl` war faelschlich als Output-Flag
angegeben. Richtig ist `conv=excl,fsync`. Kein Kartenabbild oder erfolgreicher
Backup-Abschluss wurde damit nachgewiesen. Die Karten-Schreibsperren waren
bereits gesetzt; die Partitionierung wurde nicht geaendert.

Korrigierten Aufruf lokal mit Testdateien geprueft: bytegleiche Kopie und
verweigertes Ueberschreiben einer vorhandenen Zieldatei. Der Betreiber hat den
Ablauf als `flash.sh` gespeichert; trotz des Namens liest dieses Skript die
Karte und schreibt ausschliesslich das Sicherungsabbild auf den Host.


## Vollabbild erfolgreich geprueft: Betreiber-Nachweis

Die korrigierte Sicherung wurde vom Betreiber auf dem Proxmox-Host beendet:

- Verzeichnis: `/root/meteohub-sd-vor-ro-juN2kxBj`
- Abbild: `karte.img`, exakt **31.914.983.424 Bytes**
- SHA-256: `89148f69b230f0a8237d3eb3d2066a30738a19a8d27d4c301680ea21d452b47f`
- dd meldete erfolgreichen Abschluss; anschliessend bestaetigte das Skript
  gleiche Dateigroesse und gleiche SHA-256 von Abbild und erneut gelesener Karte.
- Partitionstabelle und Kartengroesse wurden vor der Kopie mitgesichert.

Dies ist ein vom Betreiber vorgelegter Integritaetsnachweis der Offline-Kopie,
noch kein Test des Rueckschreibens oder Bootens einer wiederhergestellten Karte.
Das Abbild bleibt unveraendert erhalten. Es liegt auf einem anderen physischen
Datentraeger als der SD, enthaelt aber private Daten und wird nicht publiziert.

Naechster Schritt: exakte Partitionstabelle, Dateisystemeigenschaften und
rein lesende ext4-Pruefung mit `e2fsck -fn`. Nur bei erfolgreicher Pruefung
`resize2fs -P` als Schaetzung der Mindestgroesse auslesen. Noch kein Resize,
kein Reparaturlauf und kein Aufheben der Schreibsperre. Die spaetere Zielgroesse
muss deutliche Reserve fuer Betrieb und Updates enthalten; nicht auf die
angegebene Mindestgroesse zusammenschrumpfen.

Bei spaeterem Rueckbau waere das **ganze** unveraenderte Abbild auf die erneut
eindeutig identifizierte SD zurueckzuschreiben, womit auch die alte
Partitionstabelle wiederhergestellt wird. Dafuer muessen alle Kartenpartitionen
ungemountet, die Zielkapazitaet ausreichend und die Schreibsperre gezielt
aufgehoben sein. Ein solcher Schreibbefehl wird erst fuer den konkreten
Rueckbaufall ausgegeben, nicht zusammen mit den aktuellen Lesebefehlen.


## Offline-ext4-Pruefung und Groessenplan

Der Betreiber bestaetigt fehlerfreie `e2fsck -fn`-Pruefung, Dateisystem clean.
7658624 Bloecke zu 4096 Bytes, 6279446 frei; belegt 1379178 Bloecke =
5,261 GiB. Geschaetztes Minimum 1396793 Bloecke = 5,328 GiB.
MBR-ID 0xe1523b9f, Sektorgroesse 512 Bytes. Boot Start 16384, Groesse 1048576;
Root Start 1064960, Groesse 61268992 Sektoren.

Plan: Root-Dateisystem und spaeter Rootpartition je 12 GiB (3145728 ext4-Bloecke,
25165824 Sektoren). Root-Start unveraendert; neue Datenpartition ab Sektor
26230784, Rest 36103168 Sektoren = 17,215 GiB. MBR-ID, Bootpartition,
Root-Partitionsnummer und Dateisystem-UUID bleiben erhalten. Die Partitionen
werden erst nach erfolgreich verkleinertem und erneut geprueftem ext4 angepasst.

Lokaler mechanischer Vorabtest mit temporaerem sparse-ext4-Abbild 16 -> 12 GiB,
unter anderem orphan_file/metadata_csum_seed und ohne 64bit: e2fsck davor/danach
Exit 0 und exakt 3145728 Bloecke bestaetigt. Leeres Testdateisystem, kein Ersatz
fuer Daten-/Bootabnahme auf der SD. Privater Testbeleg:
`/var/local/meteohub-private/resize-12g-local-test.json`.

Naechster Betreiberbefehl betrifft nur das Dateisystem. Er prueft Karten-UUIDs,
Groesse, unveraenderte Partitionstabelle und Sicherungsabbild erneut. Nach Ende
oder Fehler werden Karte und Rootpartition wieder schreibgeschuetzt. Bei jedem
Fehler Ausgaben pruefen, keine Partitionstabelle verkleinern und kein `-f` zum
Erzwingen eines resize2fs-Fehlers verwenden. Das Vollabbild bleibt unveraendert.

```bash
(
set -euo pipefail
umask 077
export LC_ALL=C

karte=/dev/disk/by-id/usb-Generic_SDXC_MMC_0000000000000006-0:2
wurzel="${karte}-part2"
sicherung=/root/meteohub-sd-vor-ro-juN2kxBj

test "$(blkid -s UUID -o value "${karte}-part1")" = B2F0-82D2
test "$(blkid -s UUID -o value "$wurzel")" = 15f4c6be-1102-4331-9904-f78e78afd1fd
test "$(blockdev --getsize64 "$karte")" = 31914983424
test -z "$(lsblk -nro MOUNTPOINTS "$karte" | tr -d '[:space:]')"
sfdisk --dump "$karte" | cmp - "$sicherung/partitionen.sfdisk"
test "$(stat -c %s "$sicherung/karte.img")" = 31914983424
test "$(awk '{print $1}' "$sicherung/SHA256SUMS")" = 89148f69b230f0a8237d3eb3d2066a30738a19a8d27d4c301680ea21d452b47f
(cd "$sicherung" && sha256sum -c SHA256SUMS)

trap 'sync; blockdev --setro "$wurzel"; blockdev --setro "$karte"' EXIT
blockdev --setrw "$karte"
blockdev --setrw "$wurzel"

e2fsck -fp "$wurzel" 2>&1 | tee "$sicherung/ext4-vor-verkleinerung.txt"
resize2fs -p "$wurzel" 12G 2>&1 | tee "$sicherung/ext4-verkleinerung.txt"
e2fsck -fn "$wurzel" 2>&1 | tee "$sicherung/ext4-nach-verkleinerung.txt"

tune2fs -l "$wurzel" | grep -E 'Filesystem state:|Block count:|Free blocks:|Block size:'
test "$(tune2fs -l "$wurzel" | awk '/^Block count:/ {print $3}')" = 3145728
test "$(tune2fs -l "$wurzel" | awk '/^Block size:/ {print $3}')" = 4096
sync
printf '\nOK: ext4 auf 12 GiB verkleinert und geprueft; Partitionstabelle noch unveraendert.\n'
)
```

Noch kein Nachweis der Ausfuehrung auf der echten Karte; Partitionsschritt und
neue Datenpartition bleiben ausstehend.


## Root-Dateisystem auf der Karte erfolgreich verkleinert

Betreiber bestaetigt: Sicherungsabbild erneut SHA-256-geprueft, resize2fs auf
3145728 Bloecke zu 4096 Bytes erfolgreich. Anschliessendes e2fsck ohne Fehler,
clean, 98832 Dateien, 1311274 belegte und 1834454 freie Bloecke. Die alte groessere
Rootpartition besteht noch. Damit darf als naechster Schritt ihre Grenze auf
das bereits verkleinerte Dateisystem angepasst werden.

Den MBR-Umbau lokal an einem sparse-Kartenabbild mit exakt 31914983424 Bytes
und der alten Tabelle geprueft: Trockenlauf ohne Mutation; danach alte MBR-ID,
Bootpartition und Root-Start erhalten, Rootgroesse und dritte Partition exakt
wie geplant. Privater Beleg `partition-12g-local-test.json` unter
`/var/local/meteohub-private`. Kein Hardware-/Bootnachweis durch diesen Test.

Naechster angeleiteter Betreiberbefehl: neue MBR-Tabelle mit unveraenderter
Kennung schreiben, Partitionen neu einlesen, Root-Dateisystem erneut lesend
pruefen. Keine Formatierung in diesem Schritt. Schreibschutz am Ende wieder
setzen; bei Fehler abbrechen und Zustand untersuchen.

```bash
(
set -euo pipefail
umask 077
export LC_ALL=C

karte=/dev/disk/by-id/usb-Generic_SDXC_MMC_0000000000000006-0:2
wurzel="${karte}-part2"
sicherung=/root/meteohub-sd-vor-ro-juN2kxBj

test "$(blkid -s UUID -o value "${karte}-part1")" = B2F0-82D2
test "$(blkid -s UUID -o value "$wurzel")" = 15f4c6be-1102-4331-9904-f78e78afd1fd
test "$(blockdev --getsize64 "$karte")" = 31914983424
test -z "$(lsblk -nro MOUNTPOINTS "$karte" | tr -d '[:space:]')"
test "$(stat -c %s "$sicherung/karte.img")" = 31914983424
sfdisk --dump "$karte" | cmp - "$sicherung/partitionen.sfdisk"
test "$(tune2fs -l "$wurzel" | awk '/^Block count:/ {print $3}')" = 3145728
test "$(tune2fs -l "$wurzel" | awk '/^Block size:/ {print $3}')" = 4096
e2fsck -fn "$wurzel"

cat > "$sicherung/partitionen-neu.sfdisk" <<'TABLE'
label: dos
label-id: 0xe1523b9f
unit: sectors
sector-size: 512

start=16384, size=1048576, type=c
start=1064960, size=25165824, type=83
start=26230784, size=36103168, type=83
TABLE

trap 'sync; for g in "${karte}-part1" "${karte}-part2" "${karte}-part3" "$karte"; do if test -b "$g"; then blockdev --setro "$g"; fi; done' EXIT
blockdev --setrw "$karte"

sfdisk --no-act --wipe never --wipe-partitions never "$karte" < "$sicherung/partitionen-neu.sfdisk"
sfdisk --wipe never --wipe-partitions never "$karte" < "$sicherung/partitionen-neu.sfdisk"
blockdev --rereadpt "$karte"
udevadm settle

test "$(blockdev --getsize64 "${karte}-part1")" = 536870912
test "$(blockdev --getsize64 "$wurzel")" = 12884901888
test "$(blockdev --getsize64 "${karte}-part3")" = 18484822016
test "$(blkid -s UUID -o value "$wurzel")" = 15f4c6be-1102-4331-9904-f78e78afd1fd

e2fsck -fn "$wurzel" 2>&1 | tee "$sicherung/ext4-nach-partitionierung.txt"
sfdisk --dump "$karte" | tee "$sicherung/partitionen-nachher.sfdisk"
lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINTS,UUID,PARTUUID "$karte"
printf '\nOK: Rootpartition 12 GiB; dritte Partition angelegt, noch NICHT formatiert.\n'
)
```

Erfolg auf der SD und Bootabnahme noch ausstehend.


### Betreiberbeleg: Partitionstabelle erfolgreich angepasst (08.11.2026)

Stationsexemplar auf Proxmox .60: Der Betreiber hat die oben angeleitete
Partitionierung ausgefuehrt. MBR-ID e1523b9f, Boot-UUID B2F0-82D2 und
Root-UUID 15f4c6be-1102-4331-9904-f78e78afd1fd sind erhalten. Partition 2
ist nun exakt 12 GiB; die anschliessende lesende ext4-Pruefung war sauber.
Partition 3 beginnt bei Sektor 26230784, umfasst 36103168 Sektoren
(18484822016 Bytes) und hat PARTUUID e1523b9f-03. Sie hat laut lsblk
noch kein Dateisystem. Alle Partitionen waren ungemountet.

Naechster Betreiberbefehl: ausschliesslich diese neue Partition als ext4
formatieren, vollstaendig initialisieren und pruefen. Keine Mount-, fstab-,
Boot- oder RO-Overlay-Aenderung. Der Block verweigert die Formatierung bei
bereits vorhandener Signatur oder abweichender Kartentabelle. Bei einem
Abbruch nicht blind erneut formatieren, sondern den Zustand untersuchen.

Syntax und mkfs-Optionen lokal an einem sparse-Abbild mit exakt der geplanten
Partitionsgroesse geprueft: mkfs.ext4, e2fsck -fn und blkid -p erfolgreich.
Privater Beleg: /var/local/meteohub-private/format-data-local-test.json.
Dies prueft keine echte SD und ersetzt keine Bootabnahme. Formatierung auf
der SD, Einbindung, RAM-Datenhaltung und taegliche Sicherung bleiben OFFEN.

```bash
(
set -euo pipefail
umask 077
export LC_ALL=C

karte=/dev/disk/by-id/usb-Generic_SDXC_MMC_0000000000000006-0:2
daten="${karte}-part3"
sicherung=/root/meteohub-sd-vor-ro-juN2kxBj

test -b "$daten"
test "$(blockdev --getsize64 "$karte")" = 31914983424
test "$(blkid -s UUID -o value "${karte}-part1")" = B2F0-82D2
test "$(blkid -s UUID -o value "${karte}-part2")" = 15f4c6be-1102-4331-9904-f78e78afd1fd
test "$(blkid -s PARTUUID -o value "$daten")" = e1523b9f-03
test "$(blockdev --getsize64 "$daten")" = 18484822016
test -z "$(lsblk -nro MOUNTPOINTS "$karte" | tr -d '[:space:]')"
sfdisk --dump "$karte" | cmp - "$sicherung/partitionen-nachher.sfdisk"
test -z "$(wipefs --noheadings --output TYPE "$daten")"

trap 'sync; for g in "${karte}-part1" "${karte}-part2" "${karte}-part3" "$karte"; do if test -b "$g"; then blockdev --setro "$g"; fi; done' EXIT
blockdev --setrw "$karte"
blockdev --setro "${karte}-part1"
blockdev --setro "${karte}-part2"
blockdev --setrw "$daten"

mkfs.ext4 -L meteohub-data -m 0 \
  -E lazy_itable_init=0,lazy_journal_init=0 "$daten" 2>&1 |
  tee "$sicherung/daten-formatierung.txt"

e2fsck -fn "$daten" 2>&1 |
  tee "$sicherung/daten-pruefung.txt"
blkid "$daten" | tee "$sicherung/daten-kennung.txt"
lsblk -o NAME,SIZE,RO,FSTYPE,MOUNTPOINTS,UUID,PARTUUID "$karte"
printf '\nOK: Datenpartition formatiert und geprueft; Schreibschutz wird wieder gesetzt.\n'
)
```


### Betreiberbeleg: Datenpartition formatiert und geprueft (08.11.2026)

Der Betreiber meldet mkfs.ext4 und anschliessend alle fuenf e2fsck-Paesse
erfolgreich. Neues Dateisystem: LABEL meteohub-data, UUID
6d332cf5-8a19-4fc5-bcaa-5156ab2dad54, PARTUUID e1523b9f-03,
4512896 Bloecke zu 4096 Bytes. Root- und Boot-UUID unveraendert.
Die lsblk-Ausgabe wurde vor dem EXIT-Trap erstellt: RO=0 fuer Gesamtdisk
und Partition 3 ist daher kein Nachweis eines fehlgeschlagenen Traps.
Den abschliessenden Schreibschutz vor Entnahme separat anzeigen lassen.

Naechster Schritt: sync und ungemounteten Zustand am Proxmox pruefen,
SD in den ausgeschalteten Pi zuruecksetzen und regulaer booten. Auf dem Pi
neue Anmeldung, Bootzeit, Partitionen, Root-/Bootmounts, fehlgeschlagene
Units und live-status pruefen. Nach ausreichender Laufzeit neue Archivdaten
mit Zeitstempel nach diesem Boot nachweisen. Ein aktiver Dienst allein
ist keine Abnahme der Aufzeichnung.

Es wurde noch kein fstab-Eintrag fuer die Datenpartition gesetzt. RAM-Daten,
RO-System und Sicherungstimer sind weiterhin NICHT eingerichtet. Das
vollstaendige Originalabbild auf .60 bleibt als Wiederherstellungsquelle
erhalten. Lokale Dokumentation; kein Push.


### Bootbeleg nach Partitionierung: 08.11.2026, 23:29 CET

Betreiber ist auf dem Pi neu als root angemeldet. Bootzeit 23:27:56 CET;
Pruefung 23:29:43 CET. Root 12 GiB und Boot 512 MiB sind mit ihren bisherigen
UUIDs korrekt RW gemountet; Datenpartition 17,2 GiB mit UUID
6d332cf5-8a19-4fc5-bcaa-5156ab2dad54 ist noch ungemountet.
ZRAM vorhanden. Keine fehlgeschlagenen Units; Logger, Web und Index aktiv,
NRestarts jeweils 0; Bootwechsel erkannt.

Aufzeichnung nach diesem Boot noch OFFEN: Neuester Wind-/Solar-/UV-Eintrag
21:11:01 UTC (22:11:01 CET), somit vor dem Herunterfahren. Die 3922 Datensaetze
seit Installation sind kumulativ und kein Nachweis fuer Daten nach dem Boot.
Indexer arbeitet, hat beim letzten Lauf aber keine neuen Datensaetze gefunden.
Knapp zwei Minuten Laufzeit reichen angesichts zuvor beobachteter
Archivverzoegerung noch nicht zur Diagnose eines Empfangsausfalls.
Naechster Schritt: aktuelles Bootjournal, Anwendungslog und vier Minuten
lesende Archivbeobachtung; keine Neustarts oder weiteren Storage-Aenderungen.
