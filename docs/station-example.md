# Beispielstation und allgemeine Installationsvorgaben

Stand: 7. November 2026. Diese Seite beschreibt **unsere getestete Station**.
Sie ist kein Pflichtprofil für eine andere Wetterstation. Die datierten
Messwerte und Testausgaben in der Anleitung bleiben als Betriebsnachweise
erhalten; ein erfolgreicher Lauf dort ist keine Abnahme einer anderen Anlage.

## Was jeder Anwender selbst festlegt

| Einstellung | Bedeutung für die eigene Installation |
| --- | --- |
| Pi-Adresse und SSH-Benutzer | Eigener Zugang; `PI_IP` und `BENUTZER` sind Platzhalter. |
| Quelladresse und Port | Vorhandener Meteohub-Stationsdatenstrom; 5500 bezeichnet dessen erste Station, nicht jeden beliebigen Wetterempfänger. |
| Stationstyp und Anschluss | Müssen zum eigenen Empfänger passen. Der aktuelle `direct-test` unterstützt auf dem Ziel speziell Station 0 / User-defined / TCP/IP Meteohub. USB-Dauerbetrieb ist damit nicht eingerichtet. |
| Sensor-IDs und Kanalnummern | Tatsächlich erkannte Kanäle sinnvoll und eindeutig zuordnen. Eine Nummer sagt allein nichts über Innen-/Außenstandort aus. |
| Stationshöhe und Druckreduktion | Eigene Höhe und passende Berechnung wählen; gemessenen Stationsdruck von reduziertem Meereshöhendruck unterscheiden. |
| Temperatur für Windchill | Den tatsächlich außen messenden, geeigneten Sensor auswählen. |
| Messintervalle | Je Sensor aus Konfiguration und Beobachtung bestimmen; seltene Übertragungen nicht pauschal als Ausfall werten. |
| Exporte und Zugangsdaten | Eigene Ziele und private Zugangsdaten; nicht aus dem Beispiel übernehmen oder in Git speichern. |

## Unser Stationsprofil

| Bereich | Einstellung bzw. Befund ausschließlich dieser Station |
| --- | --- |
| Datenquelle | Bestehender Meteohub, erste Station über TCP-Port 5500. |
| Ziel für den Test | Pi 4 Model B, 1 GB RAM, Raspberry Pi OS Lite Trixie ARM64 mit zusätzlicher ARMHF-Laufzeit. |
| Native Anwendung | Meteohub 5.1e, Build 277. |
| Stationshöhe | 336 m; Druckreduktion nach Stationshöhe. Diesen Wert nicht für andere Standorte kopieren. |
| Temperatur | Kanal 1 → `t1` (Zusatzsensor), Kanal 2 → `t2` (Außen); Windchill verwendet `t2`. |
| Weitere Kanäle | Wind 0 → `wind0`, Solar 0 → `sol0`, UV 0 → `uv0`, Daten 0 → `data0`, THB 0 → `thb0`. |
| Kombisensor | Temperatur 128,9 °C und Feuchte 100 % wurden als ungeeignete Nutzwerte behandelt. Der Druck wird übernommen. |
| Roharchiv | Vollständiges ursprüngliches THB einschließlich Temperatur/Feuchte; keine erfundenen Ersatzwerte. |
| Anzeige | Aus THB nur Stationsdruck; Temperatur aus den getrennten Sensoren. |

Der direkte native Test schrieb nach der THB-Zuordnung 39 neue Archivzeilen,
darunter eine `thb0`-Zeile. Diese enthielt 981,6 hPa Stationsdruck und
1021,1 hPa reduzierten Druck. Das ist ein konkreter Empfangs-/Archivnachweis,
keine Kalibrierung und keine Vorgabe für erwartete Messwerte anderer Stationen.
Die [Testprotokolle](installer.md#direkte-native-thb-archivierung-bestätigt)
dokumentieren auch das geplante Testende und die noch fehlende Dauerinstallation.

## Derzeit feste Vorgaben der Anzeige

**Die folgende Tabelle beschreibt vorhandenen Code, keine frei konfigurierbaren
Optionen.** Eine allgemeine Anleitung macht diese Stellen noch nicht universell:

| Komponente | Aktuelles Verhalten und Grenze |
| --- | --- |
| THB-Decoder, API und SVG | Für alle `thbN` wird nur Stationsdruck verwendet. Auch plausible THB-Temperatur und -Feuchte werden ausgeschlossen. Ein Anwender mit ausschließlich einem funktionierenden THB-Temperatursensor benötigt dafür erst eine Softwareanpassung. |
| Dashboard-Temperaturkarte | Bevorzugt `t2`, danach `th0`; andernfalls den zuletzt gemessenen verfügbaren Temperaturkanal. Dieser Rückgriff garantiert keine Außentemperatur. |
| SVG-Temperatur | Liest fest `t2`; kein entsprechender Rückgriff auf andere IDs. |
| SVG und Windvektor | Verwenden `wind0`; weitere feste SVG-Quellen sind `thb0`, `rain0`, `sol0`, `uv0`. Fehlende Werte erscheinen als Strich. |
| Dashboard-Beschriftung | Bezeichnet `t2` als „Außen“ und `t1` als „Zusatzsensor“. Diese Bezeichnungen sind für andere Stationen zu prüfen. |
| Zeitdarstellung | Aktuell Deutsch und `Europe/Berlin`; eine andere OS-Zeitzone ändert diese Codevorgaben nicht. |
| Aktualität | Ohne Intervallkonfiguration gilt 60 Sekunden als Annahme (180 Sekunden Altersgrenze). API/SVG lesen `sensor_intervals_seconds` aus ihrer Konfiguration; Einstellung über `tools/dashboard-interval.py`, kein Einrichtungsdialog. |
| Druck-Testkennzeichen | `pressure_archive_observed` prüft speziell `thb0`. Andere THB-IDs sind über die tatsächlichen Archivzeilen und die Sensorzähler zu bewerten. |

Die Sensorzuordnung im nativen Meteohub muss fachlich richtig bleiben.
Sensoren nicht nur umbenennen, um sie einer festen Anzeigevorgabe anzupassen.
Eine allgemeine Konfiguration für Anzeigenquellen, Beschriftungen und Zeitzone
ist noch offen. Der vorhandene Extension-Updater prüft installierte Dateien;
lokale Änderungen an einer installierten Ausgabe sind kein unterstützter
Konfigurationsweg.

## Was allgemein nachgewiesen werden muss

Stationsbefund vom 7. November: Der Betreiber meldete fehlenden Luftdruck in
Dashboard und SVG bei etwa vier Minuten alten Werten. Die unkonfigurierte
Altersgrenze von drei Minuten reproduziert dieses Verhalten. Frühere
Archivzeitstempel für THB lagen etwa fünf Minuten auseinander. Für diese Station
wird daher `thb0 --interval 300` vorgeschlagen (elf Minuten Altersgrenze).
Die Konfiguration auf dem Pi und deren Wirkung sind noch vom Betreiber zu
bestätigen. Dies ist keine pauschale Intervallvorgabe für andere Stationen.

Für jede eigene Station: Empfang der erwarteten Kanäle, neue native
Archivdatensätze, richtige Einheiten, passende Anzeigequellen und Aktualität.
Das Testfenster muss die tatsächlichen Sensorintervalle abdecken. Danach folgen
Dauerbetrieb, Neustart, Aggregation, Exporte und Sicherungs-/Wiederherstellungstest.
Ein einzelnes `PASS` des begrenzten Tests ist keine vollständige Betriebsabnahme.

Weiter zur [allgemeinen Installer-Anleitung](installer.md) oder zur
[Pi-Ersteinrichtung](raspberry-pi-setup.md).


## Regen-Ergänzung am 08.11.2026 (nur diese Station)

Morgens war `@SENSORIDMAP 0 1 0 0` bereits in der vom CGI erzeugten
Konfiguration gespeichert, jedoch nicht in der festen Live-Kopie. Die Quelle
liefert `rain0` nur etwa stündlich um xx:38; ein fünfminütiger allgemeiner
Empfangstest kann deshalb ohne Regenzeile erfolgreich sein. Nach Übernahme
und Dauerstart muss der nächste echte Regenwert abgewartet werden, zuzüglich
Archivpufferung. Für diese Quelle `rain0`-Intervall von 3600 s konfigurieren, andere
Sensorintervalle und vorhandene Archivverzögerung unverändert lassen.

Letzter Quellencheck08.11.13:38CET: Rate0, Zusatzwert0, kumulativer Zähler
-31908. Der negative Zähler ist kein gültiger Niederschlagsgesamtwert und
bleibt ein eigener Datenqualitätsbefund; Rate0 nicht als fehlend behandeln.
Bei der Vorbereitung scheiterte der bisherige Fernzugriff an der Anmeldung.
Der Betreiber hat den vorbereiteten Block anschließend selbst erfolgreich
ausgeführt (Rückmeldung gegen 14:42 MEZ):

- Gespeicherte Konfiguration mit Regenmapping erzeugt, beide Konfigurationen
  gesichert; Anzeigeintervall von 60 auf 3600 s, Altersgrenze 7260 s.
- Echter direkter Empfangstest: 44 gültige neue Archivzeilen in 302,15 s,
  alle acht Sensor-IDs, darunter eine neue `rain0`-Zeile um **14:38:47 MEZ**.
  Keine ungültigen Zeilen oder unerwarteten Archiv-Ersetzungen.
- Anschließend Dauerbetrieb installiert: Logger, Web und Indexer aktiv,
  Autostart aktiviert, noch keine Neustarts. Die neue Live-Sicherung heißt
  `live-before-uzh4bsnt`, die Konfigurationssicherung `rain-before-fd8F1Ik0`.

Die Übernahme und der erste native Regenwert sind belegt. Die Betreiber-
Nachkontrolle um 14:51:30 MEZ bestätigt zusätzlich 50 neue gültige Zeilen
nach dem Dauerstart (1463 Bytes), aktive Dienste ohne Neustarts und einen
fehlerfreien Index ohne Rückstand bei allen acht Sensoren einschließlich
`rain0`. Anschließend bestätigt der Betreiber die Anzeige in Dashboard/SVG
mit „ja, regenrate 0,0“. Die Regenübernahme einschließlich Darstellung ist
somit abgeschlossen. Nächster stündlicher Regenwert im Dauerbetrieb und
Langzeitabnahme bleiben getrennt offen; der negative Gesamtzähler der Quelle
wurde nicht korrigiert. Der unmittelbar nach
Installation auf null gesetzte Archivzähler allein ist kein Fehlernachweis;
er zählt erst ab der neuen Installation. Der absichtliche Test-Timeout nach
fünf Minuten ist ebenfalls kein Absturz des anschließend gestarteten Dienstes.
