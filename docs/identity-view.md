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
Das ist noch keine Ausfuehrung auf dem Ziel-Pi. Vor dem Wartungsneustart muessen
dessen Sicherungsergebnis und Konfigurationsunterschiede vorliegen; der
dauerhafte Installer und die gemeinsame Web-/Logger-Sicht sind noch offen.
