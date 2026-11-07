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
| Aktualität | Ohne Intervallkonfiguration gilt 60 Sekunden als Annahme. API/SVG lesen `sensor_intervals_seconds` aus ihrer Konfiguration; ein Einrichtungsdialog ist nicht vorhanden. |
| Druck-Testkennzeichen | `pressure_archive_observed` prüft speziell `thb0`. Andere THB-IDs sind über die tatsächlichen Archivzeilen und die Sensorzähler zu bewerten. |

Die Sensorzuordnung im nativen Meteohub muss fachlich richtig bleiben.
Sensoren nicht nur umbenennen, um sie einer festen Anzeigevorgabe anzupassen.
Eine allgemeine Konfiguration für Anzeigenquellen, Beschriftungen und Zeitzone
ist noch offen. Der vorhandene Extension-Updater prüft installierte Dateien;
lokale Änderungen an einer installierten Ausgabe sind kein unterstützter
Konfigurationsweg.

## Was allgemein nachgewiesen werden muss

Für jede eigene Station: Empfang der erwarteten Kanäle, neue native
Archivdatensätze, richtige Einheiten, passende Anzeigequellen und Aktualität.
Das Testfenster muss die tatsächlichen Sensorintervalle abdecken. Danach folgen
Dauerbetrieb, Neustart, Aggregation, Exporte und Sicherungs-/Wiederherstellungstest.
Ein einzelnes `PASS` des begrenzten Tests ist keine vollständige Betriebsabnahme.

Weiter zur [allgemeinen Installer-Anleitung](installer.md) oder zur
[Pi-Ersteinrichtung](raspberry-pi-setup.md).
