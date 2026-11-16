# SD-Bereinigung, 16. November 2026

Betreiberauftrag: unnötige Dateien und Berichte sowie die Aktivierung und ihre
Hardware-Identitätsanpassung entfernen, bevor ein SD-Abbild mit PiShrink
verkleinert wird. Wetterarchive und die betriebliche Konfiguration erhalten.

## Durchgeführt

- Altes SD-Image samt Downloadarchiv, unbenutzte 5.0s-Laufzeit, CGI-/Logger-
  Testverzeichnisse, Installationssicherungen, Tagesberichte und Boot-Testpakete
  entfernt. Paketdownloadcache geleert; keine Pakete deinstalliert.
- `meteohub-5.lic` entfernt und ausschließlich das bekannte 32-Byte-
  Aktivierungsfeld der aktuellen Konfiguration auf den unaktivierten Zustand
  zurückgesetzt. Das übrige Konfigurationsformat und die Stationsdaten erhalten.
- Identitäts-Drop-ins von Webdienst und Logger sowie den installierten
  Identitätsadapter entfernt. Der verbleibende ifconfig-Formatadapter zeigt
  die tatsächliche Host-MAC; CPU- und SD-Kennungen werden nicht mehr ersetzt.
- Alte Konfigurationskopien, Identitätsmigration, initiale Snapshots und alte
  RAM-Generationen entfernt. Eine neue unaktivierte Generation erfasst den
  bestehenden Wetterdatenbestand; eine weitere reguläre Freeze-Sicherung
  bestätigt den aktuellen Sicherungsweg. Auch die verborgene alte Laufzeit
  auf der Root-Partition ist von Lizenzdatei/Aktivierungsfeld bereinigt.
- Dauerhafte Änderungen über `overlayroot-chroot` ausgeführt und das laufende
  Overlay entsprechend angepasst. Shell-History-Dateien geleert. Die allgemeinen
  Software-Lizenzbedingungen als Rechtstexte bleiben erhalten.
- Host-Statusadapter, WAN-Abfrage, nativer Auswertungsdienst, Dashboard,
  Sechs-Stunden-Sicherungsplan und lokaler LAN-Schalter bleiben installiert.

## Nachweise und Grenzen

Prüfung am 16. November, etwa 21:53–21:57 MEZ:

Root-Belegung nach Bereinigung etwa 2,2 GiB statt zuvor etwa 4,9 GiB;
auf der Root-Partition wurden 2.908.131.328 Byte freigegeben. Dazu kommen
kleinere Einsparungen auf Boot und Persistenz.

- Vorhandenes Wetterarchiv nach Bereinigung/Rebase bytegleich als Präfix
  nachgewiesen; keine Archivbereinigung oder erfundene Messdaten.
- Neue Sicherungsmanifeste vollständig verifiziert; keine `.lic`-Datei in den
  geprüften verbliebenen Laufzeiten/Generationen; Aktivierungsfelder dort leer.
- Alle fünf Anwendungs-Units aktiv, keine fehlgeschlagenen Units. Root-Unterlage,
  Bootpartition und Persistenz wieder RO. Dashboard ohne Rückstand gegenüber
  dem vorhandenen Roharchiv. Bis 21:56:26 war noch kein neuer Archivzuwachs nach dem letzten Dienststart
  belegt; aktive Units allein sind kein Nachweis weiterer Aufnahme.
- Native CGI-Abfrage liefert erwartungsgemäß „Demo Version has timed out“ mit
  der tatsächlichen Geräteidentität. Eine aktivierte native Weboberfläche wird
  nach der ausdrücklich gewünschten Entfernung nicht mehr zugesagt.
- Ein erster Löschversuch hielt an einer vorsichtigen Mount-Prüfung an: Python
  `Path.is_mount()` deutete die unterschiedlichen Gerätekennungen von Overlay-
  Datei und Verzeichnis als Mount. Die tatsächliche Mounttabelle zeigte keinen
  separaten Mount. Mit exakter Mountpunktprüfung abgeschlossen; die Dienste
  wurden durch den Kontextmanager auch beim ersten Abbruch wieder gestartet.
- Die erforderliche Bereinigung/Rebase beinhaltete einen kurzen Dienststopp;
  keine Behauptung einer lückenlosen Aufnahme während dieser Wartung.
- Kein Neustart, Ausschalten, SD-Dump oder PiShrink-Lauf ausgeführt.

Private Löschlisten, Manifestprüfungen und Diagnosebelege liegen außerhalb des
Pi auf dem Wartungsserver; keine privaten Konfigurationen oder Schlüssel im
Repository. Frühere Aktivierungsnachweise und Rückrollanweisungen mit den
nun entfernten Sicherungspfaden gelten nicht mehr für den aktuellen Zustand.

## Abbild und PiShrink

Vor dem SD-Dump regulär herunterfahren, damit der Shutdown-Checkpoint den
letzten Datenstand schreibt. Nicht im laufenden Betrieb die Karte entfernen.

Die SD hat drei Partitionen: Boot etwa 512 MiB, Root 12 GiB und Daten etwa
17 GiB. [PiShrink](https://github.com/Drewsif/PiShrink/blob/master/pishrink.sh)
verkleinert die letzte Partition. Die davor liegende Root-Partition bleibt
12 GiB groß, auch wenn sie deutlich weniger belegt ist. Für diese Datenpartition
ist ein Lauf auf einer **Kopie des Images** mit `-s` sinnvoll, um die automatische
Root-Erweiterung beim Booten wegzulassen, beispielsweise:

```sh
sudo pishrink.sh -s original.img verkleinert.img
```

Dateien wurden auf Dateisystemebene gelöscht, freie Blöcke nicht sicher
überschrieben. Ein Rohabbild ist deshalb nicht als forensisch bereinigt oder
anonymisiert zu betrachten. Host-Zugänge und Netzwerkkonfiguration wurden nicht
zurückgesetzt. PiShrink allein ist keine sichere Datenlöschung.
