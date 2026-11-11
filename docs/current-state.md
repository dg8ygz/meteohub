# Arbeitsstand und Fortsetzung – 11. November 2026

**Betriebsnachweis unserer Beispielstation, keine allgemeine Installationsvorgabe.**
Diese Notiz hält den zuletzt vom Betreiber gemeldeten Stand fest. Sie ist keine
automatisch aktualisierte Überwachung. Allgemeine Schritte stehen im
[Installer](installer.md), die individuellen Sensorentscheidungen im
[Stationsbeispiel](station-example.md).

## Betreiberpruefung 11. November morgens und Sechs-Stunden-Plan

Betreiberbelege, keine eigene SSH-Zielabfrage: Anmeldung mit vorhandenen
Schluesseln abgewiesen. Um 07:53 MEZ Uptime 32h57, NTP synchronisiert,
keine fehlgeschlagenen Units oder Kernelwarnungen im 24h-Fenster; 698 MiB RAM
verfuegbar, Swap unbenutzt. Alle 24 stuendlichen Sicherungen im gelieferten
Journal erfolgreich. Loggerstarts an diesen Terminen sind geplante Pausen.
Zu diesem Pruefzeitpunkt Host-Root noch normales ext4 RW; Boot und Persistenz
RO. Anschliessende Rueckkehr zum Root-Overlay siehe unten.

Betreiberauftrag: Sicherungen auf sechs Stunden reduzieren. Helfer um
360-Minuten-Plan erweitert, lokal mit echten systemd-/Mount-Fixtures geprueft.
Zielumstellung um 08:03 bestaetigt, dauerhaft, Altersgrenze 23400 Sekunden.
Termine 00/06/12/18 UTC (im Winter 01/07/13/19 MEZ), naechster Lauf 13:00 MEZ.
Rueckwegsicherung `/root/meteohub-checkpoint-schedule-before-qewphm1y`;
Helper-SHA `d588b4cefdba8a5dea26d9f96420651e19a29922ad9187a5b77753f51d2023ad`.

Archivpruefung 10.11.08:24:09 bis 11.11.08:24:09 MEZ, Bericht auf dem Pi
`/root/meteohub-day-audit-6dd92jbe/report.json`:

- Alle acht Sensoren aktuell im Rahmen ihrer beobachteten Intervalle und
  Archivverzoegerung. Keine identischen Duplikate, widerspruechlichen oder
  rueckwaerts laufenden Zeitstempel; strukturell ungueltige Zeilen 0.
- rain0: 24 Werte, Stundenabstand; t1/thb0: je 287, Median 300s;
  t2: 958, Median 90s. Keine inneren Luecken ueber der beobachteten Kadenz.
- data0: 15 verlaengerte Abstaende bis 121s; sol0/uv0: je 24 bis 92s;
  wind0: 24 bis 90s bei normal 15s. Sichtbare Beispiele fallen auf die
  stuendlichen Checkpoint-/Wiederanlaufzeiten. Native Logs enthalten dabei
  leere TCP-Antworten; kurze Dienstauszeit ist keine Zusage gleich kurzer
  Datenluecken. Vollstaendige Einzelkorrelation bleibt im Bericht nachzusehen.
- Aktueller Roharchivindex: Offset=Dateigroesse=1191745, Inode passend,
  history_importing=false, rejected=0. Der alte provenance.jsonl-Eintrag
  hat abweichende Inode bei gleichem Offset/Dateiende; aktive Verarbeitung
  dieses Altpfads ist damit nicht belegt. Nicht als Roharchivverlust werten.
- Dashboardintervalle sind Anzeigeannahmen, nicht Sollvorgaben der Quelle.
  Die Lueckenauswertung verwendet beobachtete Medianabstaende, keine erfundenen
  exakten Sollslots. Der noch nicht archivierte Fensterrand wird separat als
  Messalter ausgewiesen. Kein Nachweis vollstaendig lueckenlosen Empfangs.

### Root-RO-Boot und Empfang danach bestaetigt

Der Betreiber hat `return-root-ro-pi50.py prepare` erfolgreich ausgefuehrt und
anschliessend regulaer neu gestartet. Sicherung/Diagnose:
`/root/meteohub-root-ro-before-rvs20loq`. Der Helfer sichert vor der
Bootaenderung explizit die Runtime und speichert einen Archivpraefix-Hash.
Der Root-RO-Pruefhelfer rebootet selbst nicht. Rueckweg bei Bootproblemen:
in der Bootpartition `cmdline.txt` nur `overlayroot=tmpfs:recurse=0` durch
`overlayroot=disabled` ersetzen (Karte erforderlichenfalls am vorhandenen
Linux-Kartenleser bearbeiten).

- Nach neuer Anmeldung: neue Boot-ID, Host-Overlay/tmpfs aktiv; Root-Unterlage,
  Boot und Persistenz RO. Archivpraefix bytegleich erhalten, alle vier
  Anwendungsunits aktiv, keine fehlgeschlagenen Units. Remount-Dienst erfolgreich.
- Generation `gen-c4d44c73704e4c5a842ddca214b8006c` wiederhergestellt;
  Sechs-Stunden-Plan und Altersgrenze 23400 Sekunden erhalten. Naechster
  automatischer Lauf weiterhin 11.11.13:00 MEZ.
- Native Webseite um 08:31 MEZ: System-ID `UJpMany2`, **activated**.
  Dropbear-/smbd-PID-Warnungen bleiben erwartbar, da diese Daemons nicht in
  der privaten Laufzeit eingerichtet sind. Native Anzeigen `last data: never`,
  Zeitsynchronisation und WAN bleiben getrennte, ungeklaerte Anzeigepunkte;
  keine PID-Attrappen oder zusaetzlichen Dienste eingerichtet.
- Um 08:29:30 MEZ: Index noch beim Nacharbeiten (2000 Datensaetze, einzelne
  Sensoren 60--90s zurueck); Archiv 1192811 Bytes. Dieser erste Punkt allein
  war noch kein sicherer Nachweis neuer Messungen nach Boot.
- Um **08:32:16 MEZ**: Archiv **1193497 Bytes**, also **686 Bytes Zuwachs**.
  Windzeitstempel ca. **08:30:28 MEZ**, damit neue Aufzeichnung nach Boot
  nachgewiesen. Indexrueckstand fuer alle acht Sensoren 0, kein Indexfehler.
  Regenalter 3213,9s passt zum Stundenintervall; kein neuer Regenwert seit
  Boot behauptet. Runtime zuletzt etwa 6,3 MiB von 320 MiB belegt.

**Wiederanlauf einschliesslich RO, Aktivierung, Archiv und Index abgenommen.**
Offen bleibt die Zielabnahme des ersten automatischen Sechs-Stunden-Laufs
um 13:00 MEZ und seines Einflusses auf die Empfangsluecke. Die bereits
belegten stuendlichen Laeufe ersetzen diesen Nachweis nicht. Ebenso offen:
vollstaendige Ursachen-/Einzelkorrelation der 24h-Luecken und native
Aggregation/Exporte/Statusanzeigen; kein pauschales "alles abgeschlossen".

### Gesicherte Werkzeuge und lokale Pruefungen

- `tools/set-checkpoints-6h.py`: prueft den alten oder bereits aktualisierten
  Helferhash, erzeugt exakt den getesteten neuen Helfer und ruft dessen
  gesicherte Intervallumstellung auf. Download-SHA:
  `e6e57cfccbfd9a3c57ed0db6ffb1d1852864fbfd889a197f9cf2ec873cbff207`.
- `tools/audit-day-pi50.py`: reine Leseauswertung mit lokalem Bericht;
  keine Dienst-/Mount-/Bootaenderung. Download-SHA:
  `90006d4c922db416711df7b4bb8e0d5fd19d4e93863faecdde7d389b52a102db`.
- `tools/return-root-ro-pi50.py`: stationsgebundene UUID-Pruefungen,
  Sicherung/Bootvorbereitung und getrennter Nach-Boot-Check. Download-SHA:
  `d2899793f51a6891e92039cd0b01438219e185ecd3413c0697941892533da5ff`.

Lokale RAM-Tests: vier Tests mit `--isolation` erfolgreich, einschliesslich
echter systemd-/ext4-/Overlay-/tmpfs-Fixtures, Sechs-Stunden-Timerdarstellung,
Altersgrenze und Ruecknahme bei injiziertem Schreibfehler. Kalenderabstaende
ueber Tagesgrenze geprueft. Upgrade gegen Original- und neuen Helferhash sowie
Ablehnung unbekannter Inhalte geprueft. Audit mit synthetischen Rohdaten
(Luecke, Duplikat, Konflikt, Ruecksprung, Rand, fehlender Sensor, Zukunft,
unvollstaendige Zeile) sowie echten temporaeren Dateien/SQLite durchlaufen.
RO-Helfer mit temporaeren Dateien und ersetzten Hostbefehlen geprueft:
Vorbereitung/Nachcheck, abweichendes Archiv, Sicherungsfehler vor Bootaenderung,
Bootschreibfehler mit Ruecknahme und RO-Remount. Diese lokalen RO-Fixtures
sind keine echten Pi-Boots; die Zielabnahme steht separat oben.

Downloadartefakte auf dem eigenen HTTP-Host bereitgestellt und jeweils
bytegleich per HTTP abgerufen. Keine Aktivierungswerte oder Zugangsdaten
enthalten. Lokale Dokumentation/Quellen sichern; kein GitHub-Push beauftragt.

## Feierabendstand 9. November, ca. 23:00 CET: permanente Identitaet installiert

Betreiberbeleg: `/srv/meteohub-persist/identity-migration/ready-gesmgcud`
vollstaendig verifiziert, Datenpartition wieder RO, Logger-PID unveraendert.
Die private aktivierte Konfiguration unterscheidet sich vom gemeinsamen Stand
nur in 32 Bytes (27836 bis 27867). Keine Aktivierungswerte in Repository/Output.
Der permanente Installer wurde nach drei lokalen Tests einschliesslich echtem
systemd-Startfehler/Rollback auf dem Pi ausgefuehrt. Ablauf und Testgrenzen
stehen in [Identitaetssicht](identity-view.md).

- Wartungsstart vorbereitet mit Installer/Diagnose unter
  `/srv/meteohub-persist/identity-migration/maintenance-62cap98p`.
- Erster Installationsversuch: `Errno 11` beim Anfordern der Speichersperre,
  vor der Konfigurationsaenderung. Ein gleichzeitig laufender Checkpoint ist
  plausibel, der Sperrhalter wurde aber nicht festgestellt. Erneuter Aufruf
  erfolgreich; kein Entfernen/Umgehen der Sperre.
- Erfolgreiche Rueckwegsicherung: `/root/meteohub-identity-before-glppuzvh`.
  Beide nativen Dienste sehen dieselbe Konfigurationsdatei; echte Logger-PID
  verifiziert. Permanente Identitaets-/ifconfig-/PID-Drop-ins installiert.
- Aktivierung im gemeinsamen RAM-Checkpoint gesichert:
  `gen-e9950c794ed746e794760cd851f9144c`. Alle vier Anwendungsunits aktiv,
  Datenpartition RO, Stundenintervall und Altersgrenze 5400 Sekunden vorhanden.
- Native Seite vom Betreiber um 22:00:39 UTC / 23:00:39 CET bestaetigt:
  `UJpMany2 — activated`, IP `.50`. Modell/MAC zeigen absichtlich die
  eingeblendete Altsystem-Identitaet. Keine Aktivierungscodes dokumentiert.
- Roharchiv um 21:58:52 UTC: 688029 Bytes, letzter Schreibvorgang 34 Sekunden
  zuvor; t2/sol0/uv0 etwa 37 Sekunden alt. Damit frische Aufzeichnung nach der
  Installation belegt. Um 21:59:53 UTC gleiche Dateigroesse und entsprechend
  gealterte Messwerte; diese einzelne Minute belegt keinen neuen Ausfall.
- Index ohne gemeldeten Fehler, aber beide Punktpruefungen mit
  `records_added=2000` und gleichem Rueckstand: data0 240s, sol0/uv0 225s,
  t2 270s, wind0 105s. Die angeforderte zweimalige Lesepositions-/Inodepruefung
  im Abstand von 12 Sekunden wurde noch nicht geliefert. Fortlaufender Import
  versus wiederholtes Einlesen ist daher OFFEN; 2000 sind verarbeitete, nicht
  zwingend erstmals eingelesene Datensaetze.

**Uebernacht: Host-Root bleibt RW im Wartungsmodus (`overlayroot=disabled`).**
Der Installer hat den Root-Schreibschutz ausdruecklich nicht reaktiviert.
Boot wurde bei Vorbereitung wieder RO gesetzt, Datenpartition nach Installation
als RO bestaetigt; eine erneute vollstaendige Mount-Abnahme steht aus.
Keine weiteren Pi-Aenderungen oder Neustarts zum Feierabend beauftragt.

Naechste Schritte: Index-Lesepositionen/Inodes pruefen, dann RO-Boot vorbereiten
und nach Neustart Aktivierung, gemeinsame Sicht, Dienste, Timer, Mounts und
frische Aufzeichnung abnehmen. Weitere native Statusanzeigen bleiben separat
OFFEN: `last data: never` trotz aktueller Rohdaten, Dropbear-/smbd-PID-Warnungen,
`Time Synchronization: stopped` und `WAN IP: no internet access`. Letztere sind
keine unabhaengigen Nachweise fuer einen Host-NTP-/Internetausfall. Keine
zusaetzlichen Daemons oder erfundenen PID-Dateien zur Warnungsunterdrueckung.
Dies ist eine Auswertung der Betreiberbelege, keine laufende Ueberwachung.

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
- Zu diesem Installationszeitpunkt noch OFFEN: echte neue Archivwerte nach RAM-Umschaltung, manueller Checkpoint
  mit Wiederanlauf, Wiederherstellung nach Pi-Reboot und Host-Root-/Boot-RO.
  Installationsstatus ersetzt keinen Empfangs- oder Wiederherstellungsnachweis.

**Nachkontrolle 07:28:58 bis 07:34:58 CET: Fehler bei der Leseberechtigung.**
Der Beobachter als Benutzer meteohub meldete durchgaengig PermissionError fuer
Roharchiv und Index. Damit ist kein neuer Messwert durch diesen Lauf belegt.
RAM-Belegung danach 4386816 Bytes, Anwendungen weiterhin aktiv. Beide Timer
bestaetigt: Check alle fuenf Minuten, naechste Sicherung 10.11.2026 04:15 CET.

Lokal reproduzierte Ursache: das neu angelegte Overlay-Upper-Verzeichnis war
root:root/0700; diese Metadaten bestimmen auch die Wurzel des eingeblendeten
Runtime-Verzeichnisses. Der bisherige Test lief als root und erfasste diesen
Zugriffsfehler nicht. Korrektur uebernimmt Besitzer, Modus und weitere
Verzeichnismetadaten aus der geprueften unteren Generation vor jedem Mount.
`repair-permissions` sichert den installierten Helper und seine Konfiguration,
aktualisiert Helper samt verwaltetem Hash und korrigiert die gemountete
Runtime-Wurzel ohne Dienstneustart. Kein rekursives chmod und keine Aenderung
der versiegelten Generation.

**Betreiberabnahme der Rechtekorrektur 07:40:05 CET:** korrigierter Helper
SHA256 `42a351386adf7cabbffc460002b4736c4395c18d5b9f2f1a14f40f70eb4da8c0`
geprueft und installiert, Sicherung unter
`/root/meteohub-ram-permissions-before-u1ku8man`. Runtime-Wurzel wieder
UID/GID 1000, Modus 0700; keine Dienstneustarts. Beobachter als meteohub liest
erfolgreich: raw_bytes=611222, letzter Schreibvorgang 79,3 s alt, Windwert
79,6 s alt, weitere Messwerte nach RAM-Installation vorhanden. Index bei allen
acht Sensoren 0 s Rueckstand und ohne Fehler. Regenwert 3679,6 s alt, damit
gerade ueber einer Stunde; naechster stuendlicher Eingang noch separat offen.
RAM-Belegung 4853760 Bytes, aktive/gesicherte Generation unveraendert,
Datenpartition RO, alle Anwendungen aktiv. Kein lueckenloser Langzeitnachweis.

**Manueller Checkpoint und Beobachtung 07:41:04 bis 07:47:04 CET bestanden:**
`meteohub-ram-checkpoint.service` Result=success, ExecMainStatus=0. Neue aktive
und gesicherte Generation `gen-396d2b730dbc463eb09560fce4c77a94` identisch.
Datenpartition wieder RO, vier Anwendungsunits aktiv; RAM direkt danach
2764800 Bytes, nach sechs Minuten 3919872 Bytes. Keine PermissionErrors mehr.
Roharchiv waechst von 611949 auf 612750 Bytes (+801); neue Messzeitpunkte nach
Sicherung nachgewiesen. Neuer Regenwert 07:38:46 CET im Archiv und Index.
Index anfangs im Rueckstand, ab 07:42:52 CET alle acht Sensoren gleichauf und
bis Beobachtungsende ohne Fehler. Indexer verarbeitet anfangs 2000 Datensaetze
je Lauf; dessen Code beginnt bei veraenderter Datei-Inode erneut. Neuaufbauzeit
nach Generationswechsel bei wachsendem Archiv weiter beobachten.
Noch keine Pi-Reboot-/Shutdown-Restore-Abnahme und kein Host-Root-RO.

**Reboot-Test 07:49:52 CET: NICHT abgenommen.** Anmeldung danach erfolgreich,
NTP bei 36,831 s und Loggerstart erst bei 36,852 s. RAM-Restore startet bei
8,694 s und endet bei 10,046 s. Beobachtung 07:51:13 bis 07:57:13 CET zeigt
neue Rohdaten (611949 -> 613481 Bytes), am Ende Indexgleichstand ohne Lesefehler.
Aber Websocket und Webservice sind inactive. Zudem bleibt die gespeicherte
Generation `gen-396d2b730dbc463eb09560fce4c77a94` vom manuellen Checkpoint;
das Archiv beginnt nach Reboot wieder mit 611949 statt der vor Reboot bereits
belegten 612750 Bytes. Mindestens diese 801 Bytes wurden nicht wiederhergestellt;
Shutdown-Sicherung ist damit nicht als erfolgreich belegt. needs_attention=false
trotz inaktiver Anwendungen ist eine weitere Luecke der Statusbewertung.

Lokaler Codebefund: RAM-Service mit normalen systemd-Service-Abhaengigkeiten
wird vor den Websocket geordnet, waehrend normale Sockets vor sockets.target
und basic.target starten. Damit besteht ein potentieller Boot-/Shutdown-
Ordnungszyklus. Bisherige lokale Start-/Stop-Tests nach abgeschlossenem Hostboot
decken diese Gesamttransaktion nicht ab. Journal des aktuellen und vorherigen
Pi-Boots zur konkreten Ursache anfordern; bis zur Korrektur kein weiterer Reboot
und keine Host-Root-RO-Umschaltung.

**Anschliessender Betreiberbeleg:** aktuelles Journal bestaetigt den Zyklus
`sockets.target -> meteohub-web-test.socket -> meteohub-ram.service`;
systemd loeschte den Websocket-Startauftrag bei 4,691 s. Vorheriges Journal
nicht vorhanden (kein persistentes Journal); genaue Ursache der ausgebliebenen
Shutdown-Sicherung bleibt deshalb unbewiesen. Manueller Start von Websocket
und Webservice erfolgreich, beide wieder active/Result=success.

Lokal korrigiert: RAM-Service ist eine fruehe Unit ohne implizites After=basic.target,
mit expliziter Sysinit- und Shutdown-Ordnung sowie Mount-Abhaengigkeit.
Status markiert jede nicht aktive Anwendung als Handlungsbedarf. Neuer
Boot-Graph-Test reproduziert den alten Kreis mit basic.target und prueft
zusaetzlich Meldungen: systemd-analyze verify kann trotz geloeschtem zyklischen
Startjob Exitcode 0 liefern. Negativkontrolle reproduziert den Fehler,
korrigierte Transaktion ist kreisfrei. Echte lokale Mount-/Unit-Tests mit
Upgrade, Health-Fehler bei gestopptem Webdienst, gemeinsamem Target-/RAM-Stop,
gesichertem neuem Testdatensatz und Wiederanlauf bestanden (3 Tests, 32,038 s).
`repair-ordering` aktualisiert Helper/RAM-Unit und Verwaltungs-Hashes mit
vorheriger Sicherung, ohne Dienstneustart.

**Betreiber hat repair-ordering ausgefuehrt:** Helper-SHA256
`70b4620acd07584f0d8c30ae601f44f715d5f73f4daadcce0aee2218c029345b`
bestaetigt, Sicherung `/root/meteohub-ram-ordering-before-adih7iu7`.
Geladene RAM-Unit zeigt DefaultDependencies=no und After=sysinit.target sowie
den Persistenzmount, kein After=basic.target. Alle vier Anwendungen active,
inactive_apps leer, needs_attention=false. RAM 5128192 Bytes, bisherige
Generation unveraendert. Naechste Abnahme: synchroner Stop von Target UND
RAM-Service, neue gespeicherte Generation, Archiv-Praefixvergleich, Wiederanlauf.
Dies ersetzt noch keinen erfolgreichen kompletten Reboot.

**Kontrollierter Stop/Restore auf dem Pi bestanden:** Nachweisverzeichnis
`/root/meteohub-stop-check-srmJ4oHy`. Neue aktive und gesicherte Generation
`gen-c177ef8376a04d5f87ef354c5034e496`; zuvor kopierter Roharchiv-Praefix
sowohl in der SD-Generation als auch nach RAM-Wiederherstellung identisch.
Datenpartition RO, alle vier Anwendungen active, inactive_apps leer,
RAM 2797568 Bytes. Echte Reboot-Abnahme bleibt offen.

Fuer die Wiederholung ist `tools/check-ram-reboot.py` vorbereitet: RAM-Marker
ausserhalb des Wetterarchivs, SHA256 des bereits vorhandenen Archiv-Praefixes,
vorherige Boot-ID/Generation und Diagnose auf normalem beschreibbarem Root.
Ein temporaerer Drop-in schreibt nur RAM-Unit-Ausgaben nach
`/root/meteohub-ram-reboot-check/ram-service.log`. Nach Reboot verlangt der Check
neue Boot-ID, neue Generation, passende ExecStop-Sicherungsbestaetigung sowie
Marker und Archiv-Praefix in Sicherung und RAM. Bei Erfolg entfernt er den
Drop-in und den RAM-Marker; Diagnose bleibt erhalten. Keine globale Aenderung
der Journal-Speicherpolitik. Auf dem Pi noch nicht ausgefuehrt.

**Echter Pi-Reboot-Nachweis anschliessend bestanden:** Pruefwerkzeug meldet
neue Boot-ID, neue gespeicherte Generation, passende ExecStop-Bestaetigung,
erhaltenen Marker und Archiv-Praefix in Sicherung und RAM. Generation
`gen-e088378718874124a12a08a1c38ceef4`; Diagnose unter
`/root/meteohub-ram-reboot-check`. Temporaerer Logging-Drop-in entfernt.
Alle vier Anwendungen active, Datenpartition RO, inactive_apps leer,
RAM 3575808 Bytes. Beobachter um 08:23:49 CET: 619465 Archivbytes, alle acht
Sensoren im Index gleichauf, kein Indexfehler. Letzter Schreibvorgang 166,7 s
alt bei Sicherungsalter 163,8 s: diese Momentaufnahme allein belegt noch keine
nach diesem Boot neu archivierte Messung. Keine weitere feste Messwartezeit
verlangt; RAM-Sicherung/Restore-Abnahme abgeschlossen. Root und Boot noch RW.

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

**Abschlussstand (9. November, gegen 20:09 MEZ):** Dauerhafter Stundenplan
hat den erneuten Host-RO-Boot ueberstanden. Physische Root-, Boot- und
Persistenzpartition RO, alle vier Apps active, keine failed Units, neue
Sicherungsgeneration geladen. Automatischer Nachhollauf, neuer Regenwert im
Archiv und Index sowie Remount-Workaround sind nachgewiesen (Einzelbelege
unten). Naechster Timertermin 21:00 MEZ, noch kein Ausfuehrungsnachweis dieses
zukuenftigen Termins. Alterspruefung ab 90 Minuten. Keine externe Alarmierung
und keine laufende Fernueberwachung. Langzeitbetrieb und separate HTTP-/SVG-
Darstellungspruefung sind damit nicht pauschal abgenommen.

**Paketplan vom Betreiber fuer Host-RO:** overlayroot 0.18.debian14 (all),
cryptsetup und cryptsetup-bin je 2:2.7.5-2 (arm64), drei neue Pakete,
keine Upgrades/Entfernungen. cryptsetup-Abhaengigkeiten durch overlayroot.
Das identische overlayroot-Paket wurde lokal nur entpackt/geprueft:
Default deaktiviert, Postinst loest update-initramfs aus. recurse=0 ist fuer
die separate Persistenzpartition vorgesehen; deren fstab-Eintrag soll direkt
RO gemountet bleiben und bei Checkpoints kurz RW werden. cryptsetup-Postinst
registriert Legacy-cryptdisks-Startskripte; vorhandene aktive crypttab-Eintraege
vor Installation ausschliessen. Kein Autoremove.
Pi-Wrapper do_overlayfs schaltet auch Boot-RO; die eigentlichen Funktionen
enable_overlayfs/enable_bootro und der erzeugte Initramfs-Stand sind noch
anzusehen. Noch keine Installation oder RO-Aktivierung auf dem Pi belegt.

**Paketinstallation auf dem Pi 09.11.2026 08:39 CET bestanden:** eigener
systemd-Installationsdienst Result=success, Exitstatus 0, 33,215 s.
Nur die drei geplanten Pakete installiert. dpkg-Audit ohne Ausgabe.
Debconf fiel mangels Terminal auf Noninteractive zurueck; kein Paketfehler.
Boot-/fstab-Sicherung `/root/meteohub-root-ro-before-7kcZRgfn`.
Kernel `6.18.60+rpt-rpi-v8`, neues 12-MiB-Initramfs nach
`/boot/firmware/initramfs8` kopiert; 2712-Variante ebenfalls erzeugt.

Tatsaechlicher raspi-config-Code vom Pi: enable_overlayfs setzt ausschliesslich
`overlayroot=tmpfs` in cmdline; enable_bootro setzt Boot-fstab auf defaults,ro.
do_overlayfs 0 ruft beide auf. Geplante Anpassung vor erstem Reboot:
Kernelparameter auf `overlayroot=tmpfs:recurse=0` setzen. Originalfunktion
overlayrootify_fstab aus exakt overlayroot 0.18.debian14 lokal gegen die
Stations-fstab getestet: Root wird Overlay, Boot bleibt ro, Datenpartitions-
Eintrag bleibt mit recurse=0 unveraendert. Negativkontrolle recurse=1 legt auch
ueber die Datenpartition ein Overlay. Nachweis lokal privat unter
`overlayroot-review/fstab-test.json`. Keine Zielaktivierung damit behauptet.
Rueckweg fuer den folgenden Boot: auf der Bootpartition in cmdline.txt den
Overlayparameter durch `overlayroot=disabled` ersetzen; Root bootet wieder
normal, Boot bleibt laut persistenter fstab RO und kann zur Wartung remountet
werden. Pi ist beim Betreiber, Kartenleser/Offline-Abbild vorhanden.

**Erster Host-RO-Boot laut Betreiber:** SSH-Anmeldung moeglich. `/` ist ein
beschreibbares Overlay mit tmpfs unter `/media/root-rw`; physische Rootpartition
`/dev/mmcblk0p2` unter `/media/root-ro` ext4 RO. Boot `/dev/mmcblk0p1` vfat RO,
Persistenz `/dev/mmcblk0p3` weiterhin direkter ext4-RO-Mount. Meteohub-Runtime
aktive/gesicherte Generation `gen-6c4b7f5161c846ffbc60a31441bc16f3`, alle vier
Anwendungen active, inactive_apps leer, RAM 3563520 Bytes. Host 731 MiB
verfuegbar, Swap unbenutzt, ZRAM backing_dev=none.
ABER `systemd-remount-fs.service` failed; Betreiber berichtet zudem eine nicht
mitgelieferte Fehlermeldung waehrend des Umschaltskripts. Zusammenhang noch
unbewiesen. Ursache, neue Messwerte nach diesem Boot und Checkpoint unter
Host-RO noch OFFEN. Keine vollstaendige Betriebsabnahme.

### Abendnachweis vom 9. November: Remount und Wartungsstart

Betreiber meldet einen ungeplanten Neustart, vermutlich nach Beruehren des
Pi. Um 18:48 MEZ wurde wieder die Morgengeneration
`gen-6c4b7f5161c846ffbc60a31441bc16f3` geladen; Sicherung rund zehn Stunden
alt. Zwischenzeitliche RAM-Aufzeichnungen sind im wiederhergestellten Archiv
nicht vorhanden. Ein Stromausfall ist damit vereinbar, aber nicht bewiesen;
keine genaue Lueckenbilanz oder Wiederbeschaffung behauptet.

Der Remount scheiterte mit `overlay: No changes allowed in reconfigure`.
Dieselbe Fehlermeldung wurde lokal in einem privaten Mount-Namespace mit
einem temporaeren Overlay reproduziert. `LIBMOUNT_FORCE_MOUNT2=always`
erlaubte den Remount; vorhandene Dateien blieben lesbar, neue Schreibzugriffe
landeten nur im Upper-Verzeichnis. Passender Upstream-Bericht:
https://github.com/systemd/systemd/issues/39558

Auf dem Pi wurde ausschliesslich unter `/run/systemd/system/` ein Drop-in
fuer `systemd-remount-fs.service` mit dieser Environment-Einstellung erstellt.
Anschliessender Dienststart: Result=success, ExecMainStatus=0. Root-Overlay RW,
physische Root-, Boot- und Persistenzpartition weiterhin RO. Das ist ein
gezielter Mount-API-Workaround, keine Unterdrueckung des Dienstfehlers.

Um 18:49:46 MEZ waren neue Archivdaten vorhanden (626693 Bytes; Wind 1,7 s,
andere schnelle Kanaele 31,7 bis 60,7 s alt). Um 18:50:30 war der Index fuer
alle Kanaele auf Archivstand. Regen hatte noch den Morgenstand, daher keine
neue Regenmessung nach diesem Boot nachgewiesen. Manueller Checkpoint unter
Host-RO erfolgreich: `gen-16a9513873884aa59758618f62ccecd6`, alle Apps active,
Persistenz wieder RO, Sicherungsalter 1,2 s.

Fuer die dauerhafte Installation wurde nur der Bootparameter auf
`overlayroot=disabled` umgestellt. Bootparameter, Journal und temporaerer
Workaround liegen auf der Bootpartition unter
`/boot/firmware/meteohub-maintenance-6fnzODpj`. Wartungsboot um 18:52:36 MEZ
bestaetigt: Root ext4 RW, alle vier Apps active, keine failed Units, Persistenz
RO. Neue gespeicherte/aktive Generation
`gen-d19aae6ff12b4e1a9c96564883ea92e0` (Alter 52 s) belegt erneut eine
Sicherung beim geordneten Neustart. Dauerhafter Workaround und erneuter
Overlay-Boot waren zu diesem Zeitpunkt noch nicht ausgefuehrt/bestaetigt. Keine Aenderung des unteren
Dateisystems bei laufendem Host-Overlay vorgenommen.

**Abschluss des Wartungsboots:** Betreiber bestaetigt Installation unter
`/etc/systemd/system/systemd-remount-fs.service.d/90-overlay-workaround.conf`,
Sicherung `/root/meteohub-remount-before-uEG330gN`. Folgender Boot
(gemeldetes uptime -s: 18:56:18 MEZ) mit Host-Overlay erfolgreich:
Remount Result=success, ExecMainStatus=0,
Environment=LIBMOUNT_FORCE_MOUNT2=always; keine failed Units. Root-Overlay RW
auf tmpfs, physische Root-, Boot- und Persistenzpartition RO. Neue aktive und
gesicherte Generation `gen-4fb1a0e39cfb4c4a8cd9b6c2473f0837` geladen.

Fruehe Momentaufnahme zeigte Logger/Indexer inactive und needs_attention=true.
Nachkontrolle um 18:57:42 MEZ erklaert dies: erster NTP-Server antwortete nicht;
Synchronisierung ueber zweiten Server bei Bootsekunde 46,710. Zeitwarte-Dienst
fertig bei 46,713; Logger und Indexer starteten bei 46,73 und waren bei 46,83
aktiv. Keine manuelle Intervention noetig. Alle vier Anwendungen active,
needs_attention=false, Persistenz RO, RAM 3514368 von 335544320 Bytes.
Indexer importiert vorhandene Historie in 2000er-Bloecken ohne verworfene
Zeilen. Neue Empfangs-/Archivdaten nach diesem letzten Boot sind damit noch
nicht nachgewiesen; ebenso wenig der Abschluss des Historienimports.

**Nachkontrolle um 19:08:44 MEZ (18:08:44 UTC):** Betreiber meldet
Roharchiv 629972 Bytes gegenueber 627741 Bytes um 18:58:36 MEZ. Neuester
Windwert rund 19:06:30 MEZ, schnelle weitere Kanaele rund 19:05:45 MEZ,
t1/thb0 rund 19:03:45 MEZ: eindeutig nach dem Loggerstart um 18:57:16 MEZ.
Index fuer alle acht Kanaele auf gleichem letzten Zeitstempel wie das
Roharchiv, kein Index-Lesefehler, letzter Indexlauf 4,2 s zurueck. Damit sind
neue native Archivdaten und das Aufholen des Index nach dem abschliessenden
Host-RO-Boot nachgewiesen. Kein separater HTTP-/SVG-Abruf in diesem Check.
Regen weiterhin Morgenstand (37798,9 s alt); neue rain0-Lieferung noch OFFEN.
Keine dauerhafte Ueberwachung oder allgemeine Langzeitabnahme daraus ableiten.

**Folgeauftrag: Regen und automatische Sicherung, kuerzeres Intervall.**
`ram-storage.py configure-checkpoints --minutes 60 --temporary` ist fuer den
Versuch im laufenden Host-Overlay vorbereitet. Dauerhafte Installation muss
im RW-Wartungsboot ohne `--temporary` erfolgen. Lokaler Test mit echten
ext4/tmpfs/Overlay-Mounts: systemd-Kalendertimer erzeugt selbststaendig eine
neue verifizierte Generation samt Kontrollmarker; danach Apps aktiv und
Persistenz RO. Ausbleibende stuendliche Sicherung loest ab 90 Minuten einen
Fehlerstatus aus. Fehler beim Timerdatei-Austausch rollt Helper, Timer und
Konfiguration zurueck. Versehentlich als permanent deklarierte Installation
unter Host-Overlay wird abgewiesen. Keine Pi-Ausfuehrung oder neue rain0-Daten
durch diese lokalen Tests behauptet. Vier Tests bestanden, einschliesslich
vorhandener Speicher-/Shutdown-/Rollback-Pruefungen; kein Hardware-Neustart im
lokalen Test.

**Stationsversuch der stuendlichen Sicherung:** Betreiber hat Helper-SHA256
`3b77c2e8c679714b7bde914225f32d7dce88eec11f1548015bc3c85f8f184725`
geprueft und `configure-checkpoints --minutes 60 --temporary` ausgefuehrt.
Ruecknahme-Dateien unter `/run/meteohub-checkpoint-schedule-before-feybvh0h`
sind fluechtig. Timer war zuvor aktiv und loeste wegen Persistent=true sofort
um 19:34:30 MEZ einen Nachhollauf aus. Dienstjournal bestaetigt erfolgreichen
Abschluss um 19:34:33 MEZ, Result=success, ExecMainStatus=0. Neue gepruefte
Generation `gen-0bdfe2e55ed54f2b9e176e122885750e`, Digest
`50080411bdddcfc4eb857adaabc36f01b247a4350fb795d0359422fa228c4f18`.
Nachkontrolle rund 19:59 MEZ: aktive/gesicherte Generation gleich, alle Apps
active, Persistenz RO, Backup-Altersgrenze 5400 s, needs_attention=false.
Timer zeigt den naechsten Termin 20:00 MEZ. Dessen Ausfuehrung ist noch nicht
belegt, der automatisch ausgeloeste Nachhollauf hingegen schon. Regen zuletzt
um 19:34:31 MEZ geprueft und noch Morgenstand; spaetere Lieferung offen.

**Dauerhafte Stundenplan-Installation:** Helper/Bootparameter/Diagnose vor dem
Wartungsstart unter `/boot/firmware/meteohub-hourly-ccafrAID` gesichert.
Nach Wartungsboot Root ext4 RW, Apps active, Persistenz RO; aktive/gesicherte
Generation `gen-fda203e99c344ad89439ebce1197a954`. Betreiber fuehrt den
SHA-geprueften Helper von dort ohne `--temporary` aus. Ausgabe bestaetigt
temporary=false, host_overlay=false, Intervall 60 min und Altersgrenze 5400 s.
Konfigurationssicherung `/root/meteohub-checkpoint-schedule-before-2iizxs41`.
Timer loeste um 20:05:37 MEZ einen Nachhollauf aus; unmittelbar folgende
Momentaufnahme zeigte noch die vorherige Generation. Abschluss dieses Laufs
und Rueckkehr in den Host-Overlay-Betrieb sind noch nachzuweisen. Zum separat
geplanten 20:00-Lauf wurde kein Journalnachweis mitgeliefert.

**Nachweis vor abschliessendem Neustart, 20:07:50 MEZ:** Vorbereitungsblock
pruefte Sicherungsdienst inactive/Result=success, bevor er Bootparameter
aenderte. Aktive/gesicherte Generation
`gen-b7779395d5e446fcaa16b358fced0fea`, Alter 130,5 s: neuer erfolgreicher
Sicherungsstand nach der dauerhaften Umstellung. Archiv 644604 Bytes,
Indexgleichstand bei allen Kanaelen, kein Index-Lesefehler. Regenalter 1745,1 s
ergibt neuen rain0-Zeitpunkt **19:38:45 MEZ**: Morgenstand ersetzt, Regen in
native Roharchiv und abgeleiteten Index uebernommen. Kein separater SVG-/HTTP-
Nachweis in dieser Ausgabe. Boot-/Status-/Journal-/Archivdiagnose unter
`/root/meteohub-hourly-ro-before-8wL7YhGz` gesichert.

**Abschlussboot laut Betreiber:** `/` wieder beschreibbares Host-Overlay;
`/media/root-ro`, `/boot/firmware` und `/srv/meteohub-persist` jeweils direkte
RO-Mounts der SD-Partitionen. Keine failed Units. Stundenplan nach Reboot
weiter vorhanden, naechster Termin 21:00 MEZ, Intervall 60 Minuten,
Backup-Altersgrenze 5400 s. Neue aktive und gesicherte Generation
`gen-27f264b193544a4399d14cec7b413f16`, Alter 81,6 s. Alle vier Anwendungen
active, inactive_apps leer, needs_attention=false, RAM 3616768 von 335544320
Bytes. Damit Wiederherstellung und dauerhafte Timerkonfiguration im Host-RO-
Betrieb nachgewiesen. Neue Messdaten nach genau diesem letzten Boot wurden
nicht separat abgefragt; Empfang/Indexgleichstand einschliesslich Regen sind
oben unmittelbar vor diesem Boot belegt. Kein weiterer Neustart fuer die
bestaetigte Konfiguration erforderlich.

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

**Zusaetzlicher Befund vom 9. November abends:** Native Seite meldet fehlende
loggerd/dropbear/smbd-PIDs. Logger MainPID 714 und Web MainPID 706 active,
NRestarts=0; beide `/run` mit Geraet 22, Inode 2253, UID/GID 1000, Modus 0700.
`var/run` zeigt in beiden Roots auf `/run`; `loggerd.pid` fehlt tatsaechlich.
Damit kein unterschiedlicher Run-Mount als Ursache dieses Befunds.
Im lokal geprueften Herstellerpaket 5.1e erzeugt `rpi/rcloggerd` die PID-Datei
ueber start-stop-daemon; unser direkter systemd-Start hatte keinen Ersatz.
Lokaler Originalskript-SHA256:
`2e710d4e1001d918b727f2b94cecf091c244673f5abfcbed4100b765f0dd2616`.

Fix lokal vorbereitet: StartPost publiziert echte MainPID atomar, StopPost
entfernt sie. Datei `tools/logger-pid-status.conf`, SHA256
`adf373c06033f642081727942e01ecddfcb6488f4e0ff8338ae903cefafffd88`.
Frueher schrieb der synthetische Testlogger die PID-Datei selbst und verdeckte
diese Integrationsluecke. Das ist entfernt. Fuenf lokale Tests bestanden,
einschliesslich echtem systemd/lighttpd, authentifiziertem CGI-PID-Vergleich mit
MainPID, Datei-Entfernung bei Loggerstop, PID-Erneuerung nach SIGKILL und
erneutem Archivfortschritt. Testabfragen warten nun auf den tatsaechlichen
Prozesswechsel/Dienstabschluss statt nur auf eine weitere TCP-Verbindung oder
das vorzeitig erreichte Target-inactive. Kein echter ARM-Logger in diesen Tests.
Pi-Test inzwischen bestaetigt: loggerd.pid und systemd-MainPID beide 4774;
nach Neuladen der nativen Seite verschwand die loggerd.pid-Meldung.
Drop-in derzeit nur unter /run, dauerhafte Installation noch OFFEN.
MAC-Warnung getrennt.

Loggerauszug zeigt nach einigen geplanten Neustarts leere TCP-Antworten und
Wiederverbindung 30 Sekunden spaeter (20:00:10/20:00:40 sowie
20:05:40/20:06:10). Letzter sichtbarer Start 20:08:41 mit connect. Deshalb
Checkpoint-Dauer von rund drei Sekunden nicht mit durchgaengigem Empfang oder
einer auf drei Sekunden begrenzten Aufzeichnungspause gleichsetzen. Ursache
der leeren Antworten und genaue Lueckenbilanz weiterhin offen.

Noch offen:

```text
Error ifconfig read eth0 mac address: Function not implemented
Network Interface not correctly configured.
```

Der direkte Empfang funktioniert trotz dieser Meldung. Am 9. November ist
die Formatabweichung belegt: Im Mount-/Netzwerk-Namespace des Webdienstes
liefert /sbin/ifconfig eth0 die echte IP 44.149.114.50/26 und MAC
98:fe:54:62:71:a0, jedoch als `inet` und `ether`. Das verifizierte native
5.1e-CGI enthaelt Abfragen nach `inet addr:` und `HWaddr `. Das Werkzeug und
eth0 fehlen also nicht. Keine IP-/MAC-Aenderung aus dem Fallback-Hinweis ableiten.

`tools/ifconfig-compat.py` bereitet einen ausschliesslich lesenden Adapter vor:
reale iproute2-JSON-Daten des aktuellen Netzwerk-Namespace im alten Format.
Keine erfundenen Identitaeten, keine Netzwerkkonfiguration. Vorgesehen ist
ein privater ReadOnly-Bind nur im Webdienst, kein Austausch des Hostwerkzeugs.
Drei lokale Tests bestanden, darunter echte isolierte Netlink-Abfrage als
unprivilegierter Benutzer und privater Bind-Mount; abgelehnte Aenderungsbefehle
lassen die Netzwerkdaten unveraendert. Echte CGI-Abnahme auf dem Pi OFFEN.
Die getcwd-Warnung des Diagnosebefehls ist getrennt zu behandeln: kuenftig
nsenter --wdns=/ statt --wd=/ fuer das Arbeitsverzeichnis im Ziel-Root nutzen.
Erster Adapter-Zieltest: Quelle unter /run uebernimmt noexec in den Bind-Mount;
direkter Start EACCES, ausdruecklicher Python-Aufruf liefert korrekt echte MAC
und IP im alten Format. Ablage unter /usr/local/libexec im Host-Overlay als
Korrektur vorbereitet. Der lokale Test nutzte zuvor selbst den Interpreter
und erfasste diese Fehlerklasse nicht; jetzt noexec und direkten Start geprueft.
Ziel bestaetigt jetzt direkte Ausfuehrung mit echten Adressen; die MAC-Meldung
ist auf der nativen Seite verschwunden, die allgemeine Netzwerkwarnung bleibt.
Weitere lokale Analyse: Webdienst erlaubt AF_INET/AF_UNIX, waehrend iproute2
AF_NETLINK benoetigt. nsenter bildet diese Prozessfilter nicht nach. Echter
systemd-Test reproduziert Fehler und erfolgreiche Abfrage nach Freigabe von
AF_NETLINK; Netzwerkadministration bleibt ohne Capabilities gesperrt (EPERM
in privatem Testnetz). Web-spezifische Ergaenzung vorbereitet, Pi-Abnahme OFFEN.
Anleitung und Rueckbau: [ifconfig-Anzeigeadapter](ifconfig-compat.md).

Nach AF_NETLINK-Freigabe meldete die native Seite eine abgelaufene Demo mit
System-ID `0000eJD4`. Ein punktueller Archivcheck um 21:07:54 UTC zeigte
frische Daten (Wind 69,1 s, letzte Archivschreibung 68,7 s) und Indexrueckstand
0 fuer alle Sensoren. Dies ist keine Zusage fuer dauerhaften Loggerbetrieb
ohne gueltige Aktivierung; die Lizenzseite kann weitere Warnungen verdecken.
Der Betreiber beauftragte anschliessend ausdruecklich die Bereitstellung der
Kennungen seines Altsystems in der Anwendungssicht und lieferte CPU-/SD-/MAC-
Werte. Ein zeitweiliger Webtest mit separater Konfigurationskopie ist lokal
implementiert und unter echten systemd-Mounts getestet; Zielinstallation und
System-ID-Vergleich noch OFFEN. Siehe [Identitaetssicht](identity-view.md).

Nachtrag zur Zielabnahme: Der Betreiber fuehrte das befuellte Skript aus;
Testverzeichnis `/usr/local/libexec/meteohub-identity-wihrp6vt`, Web-Startcheck
bestanden, Host-MAC/SD und Logger-PID unveraendert. Native Seite zeigt danach
System-ID `UJpMany2` statt `0000eJD4`, weiterhin Demo abgelaufen. Die lokal
archivierte Originalseite `license-compare-original.html` zeigt ebenfalls
`UJpMany2` und activated, ohne Demo-Timeout. Damit stimmt die angezeigte ID
mit dem gespeicherten Altsystem-Nachweis ueberein; das ist keine aktuelle
Abfrage des Altsystems. Keine Aktivierungsdaten wurden mit diesem Schritt
uebernommen. Anschliessend bestaetigte der Betreiber die erfolgreiche Eingabe
des vorhandenen Aktivierungscodes ueber Wartung. In der nativen Oberflaeche
bleiben laut seiner Rueckmeldung nur fehlende dropbear.pid und smbd.pid.
Damit ist die Aktivierung der getrennten Web-Testkopie bestaetigt, nicht die
dauerhafte Aktivierung der gesamten Logger-Laufzeit. Kennungssicht und private
Webkonfiguration liegen weiterhin im fluechtigen Host-Overlay; der normale
RAM-Checkpoint sichert diese Testkopie nicht. Dauerhafte Uebernahme, gemeinsame
Konfigurationssicht und Abnahme nach Neustart bleiben offen. Keine Codes im Repo.

Dropbear und Samba wurden in dieser Laufzeit bislang nicht eingerichtet.
Fehlende PID-Dateien alleine beweisen keinen Dienstausfall; keinen zweiten
SSH-Server oder Dateiserver nur zur Beseitigung der Anzeige installieren und
keine fremden/erfundenen Prozess-IDs eintragen.

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
