# Zeitweilige Hardwarekennung fuer die native Weboberflaeche

Auf ausdruecklichen Betreiberauftrag vom 9. November stellt
`tools/identity-view.py` die Kennungen seines Altsystems ausschliesslich im
Mount-Namespace des Meteohub-Webdiensts bereit. Das Programm veraendert weder
Hardware noch Kernel-Netzwerkparameter oder Lizenzpruefungen. Es erzeugt keinen
Aktivierungscode. Die privaten Kennungen werden nicht im Repository gespeichert.

Voraussetzung ist der derzeitige Pi mit aktivem Root-Overlay, laufendem Logger,
installiertem ifconfig-Anzeigeadapter und bereits erlaubtem AF_NETLINK. Der
Installer kontrolliert Root-UUID, Dienstpfade, Adapterhash und bestehende
Drop-ins. Ein erneuter Aufruf bei aktiver Identitaetssicht wird abgelehnt.

Der Installer:

- sperrt den RAM-Checkpoint waehrend der Einrichtung gegen gleichzeitigen Rebase;
- kopiert die Anwendungskonfiguration in ein privates, fluechtiges Verzeichnis;
- bindet CPUinfo und SD-Seriennummer/Kartenname/Datum nur fuer den Webdienst ein;
- ersetzt nur eth0-HWaddr in einer Kopie des Anzeigeadapters; IP, Netzmaske und
  andere Schnittstellen stammen weiterhin aus dem aktuellen Netzwerk;
- prueft die Werte per ExecStartPre unter UID, Mounts und Prozessfiltern des
  echten Webdiensts und startet ausschliesslich diesen neu;
- stellt bei Startfehler die bisherigen Drop-ins wieder her und startet den
  bisherigen Webdienst; Nachweise bleiben im ausgegebenen Testverzeichnis;
- prueft unveraenderte Host-MAC/SD-Werte, Logger-MainPID und Originalkonfiguration.

Der Zielpfad und `rollback.sh` werden ausgegeben. Die Rechte des Webdiensts,
HTTP-Authentifizierung, IP-Filter und fehlenden Administrations-Capabilities
bleiben bestehen. Der Logger bleibt in seiner bisherigen Identitaetssicht.
Die private Webkonfiguration ist fuer diesen Test vom Logger getrennt:
Sensor-/Stationsaenderungen in dieser Oberflaeche stellen den Live-Logger nicht um.

Zwei lokale Tests bestanden, darunter echte systemd-RootDirectory-/Bind-Mounts
mit SD-Pfad-Symlinks, Prozessfiltern, leerem Capability-Satz und einer separaten
Netzwerk-Namespace. Die Websicht zeigt die Test-MAC und reale aktuelle IP;
die zugrunde liegende Netzwerk-MAC und die Quell-SD-Dateien bleiben unveraendert.
Das ist kein Lauf des proprietaeren ARM-CGI. Dessen System-ID und Aktivierung
muessen am Ziel-Pi anhand der nativen Seite separat festgestellt werden.

Die Sicht und die Konfigurationskopie verschwinden beim Neustart des
Root-Overlays. Sie sind kein dauerhafter Teil der Meteohub-RAM-Sicherung.
Vor dauerhafter Uebernahme muss die gemeinsame Konfigurationssicht fuer Web und
Logger wieder geklaert werden. Unter aktivem Overlay nie dessen unteres Root
beschreiben.

## Vorbereitung der dauerhaften Uebernahme

Nach bestaetigter Aktivierung der privaten Webkopie sichert
`tools/stage-identity-persistence.py` diese Kopie samt Identitaetsdateien,
unveraendertem Live-Home, temporaeren Drop-ins und Diagnosen unter
`/srv/meteohub-persist/identity-migration/ready-*`. Das Verzeichnis ist nur fuer
root zugaenglich. Die Ausgabe enthaelt ausschliesslich Anzahl und Positionen
geaenderter Konfigurationsbytes, keine Aktivierungswerte.

Das Skript verwendet den geprueften installierten RAM-Helfer, dessen
Checkpoint-Sperre, UUID-Kontrolle und RW/RO-Kontext. Es prueft Kopie und Quellen
auf Inhalt, Rechte, Eigentuemer und Symlinks, verifiziert ein Manifest und
veroeffentlicht erst danach die Sicherung. Dienste und Bootdateien werden nicht
geaendert. Bei geaenderten Quellen wird abgebrochen; unvollstaendige Kopien
bleiben als `.pending-*` gekennzeichnet.

Lokale Abnahme: `python3 tools/test-stage-identity-persistence.py --isolation`
prueft Bytebereichsausgabe und eine echte ext4-Kopie einschliesslich absichtlich
beschaedigter Kopie, falscher UUID und RO-Wiederherstellung. Zwei Tests bestanden.
Die lokale Fixture ersetzt keine Ausfuehrung auf dem Ziel-Pi. Die anschliessende
Betreiberabnahme ist unten dokumentiert.

Betreiberabnahme der Sicherung am 9. November: `ready-gesmgcud` wurde vollstaendig
verifiziert und die Partition wieder RO gemountet. Die beiden nativen
Konfigurationen unterscheiden sich ausschliesslich in 32 Bytes, Offset
27836 bis 27867. Logger-PID unveraendert, kein Dienstneustart.

`tools/install-identity-persistent.py` bereitet die permanente Uebernahme vor:

- `prepare SNAPSHOT` prueft dessen vollstaendiges Manifest, die bestaetigten
  Konfigurationsunterschiede und die bekannten Kompatibilitaetsdateien. Es
  sichert sich selbst, Journal, Units und Bootzeile dauerhaft auf der separaten
  Datenpartition. Erst danach setzt es ausschliesslich `overlayroot=disabled`
  fuer den folgenden Wartungsstart und setzt Boot/Daten wieder RO. Kein Reboot
  und kein Dienstneustart durch das Werkzeug.
- `install SNAPSHOT` ist ausschliesslich auf dem bekannten RW-ext4-Root nach
  Wartungsstart erlaubt. Es uebernimmt das vorhandene Aktivierungsfeld in die
  aktuelle gemeinsame Konfiguration; alle anderen aktuellen Einstellungen
  bleiben erhalten. Ein unabhaengig geaendertes Aktivierungsfeld wird abgelehnt.
  Die Identitaetsdateien werden unter `/usr/local/libexec/meteohub-native-identity`
  installiert, beide nativen Dienste bekommen `60-native-identity.conf` und der
  Logger den PID-Drop-in. Es gibt keinen privaten Home-Bind mehr. AF_NETLINK wird
  wie im bereits abgenommenen Webtest zugelassen; andere Netzwerk-/Capability-
  Einstellungen werden nicht ersetzt.
- Die Dienste werden fuer die Konfigurationsuebernahme angehalten und danach
  gestartet. ExecStartPre prueft die Sicht unter den echten Dienstbedingungen.
  Geraete-/Inodegleichheit der Konfiguration wird in beiden Prozesswurzeln
  kontrolliert, ebenso der echte Logger-PID. Bei Fehler wird der alte Stand
  wiederhergestellt. Rueckwegsicherung unter `/root/meteohub-identity-before-*`.
- Nach erfolgreichem Start folgt ein regulaerer RAM-Checkpoint (mit einer
  weiteren kurzen Anwendungspause), damit die gemeinsame Aktivierung dauerhaft
  gesichert ist. Schlaegt dieser fehl, bleibt der Installer mit ausdruecklichem
  Hinweis im Wartungsmodus. Der Root-Schreibschutz wird nicht automatisch
  reaktiviert; native Seite und neue Archivdaten sind vorher am Pi zu pruefen.

Lokale Tests: `python3 tools/test-install-identity-persistent.py --isolation`.
Drei Tests pruefen die begrenzte Felduebernahme mit unabhaengigen Einstellungen,
Bootparameter und echte systemd-Dienste mit RootDirectory, gemeinsamer
Konfiguration, Prozessfiltern, Identitaets-Binds und PID-Datei. Ein absichtlich
fehlschlagender ExecStartPre weist die Wiederherstellung und den anschliessenden
erfolgreichen Installationsweg nach. Nur der RAM-Mount-Vorcheck dieser Fixture
ist ersetzt; deren RAM-/Checkpoint-Lebenszyklus prueft `test-ram-storage.py`
separat. Die lokale Fixture startet keine proprietaeren ARM-Binaerdateien und
ersetzt nicht die Zielabnahme.

## Betreiberabnahme am 9. November, ca. 23:00 CET

Nach Wartungsneustart erste Ausfuehrung vor Aenderungen an belegter Speichersperre
abgebrochen (`Errno 11`); Sperrhalter nicht nachgewiesen. Wiederholung erfolgreich.
Rueckwegsicherung `/root/meteohub-identity-before-glppuzvh`; Installer bestaetigt
permanente Binds, gemeinsame Konfigurationsdatei in beiden Diensten und echte
Logger-PID. Anschliessender Checkpoint
`gen-e9950c794ed746e794760cd851f9144c` erfolgreich, Persistenz RO, alle vier
Anwendungsunits aktiv. Native Seite zeigt `UJpMany2 — activated` und echte IP
`.50`. Neue Rohdaten belegt, Indexgleichstand noch nicht erreicht/geprueft.

Host-Root bleibt auf Betreiberwunsch zum Feierabend im RW-Wartungsmodus. Die
Rueckkehr zum RO-Boot und Abnahme nach diesem Neustart stehen noch aus. Die
Dropbear-/smbd-PID-Meldungen und weitere unzutreffende oder ungeklaerte native
Statusanzeigen werden nicht durch Scheinprozesse kaschiert. Detailbelege und
Fortsetzung stehen in `docs/current-state.md`.
