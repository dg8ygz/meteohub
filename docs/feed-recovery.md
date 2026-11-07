# Serielle Messwerte mitlesen und einen geschlossenen Logger-Kanal behandeln

Eine serielle Schnittstelle ist kein Verteiler. Wenn das reguläre Plugin
`cat /dev/ttyUSB0` verwendet, darf zum Beobachten nicht ein zweiter Leser auf
dasselbe Gerät gestartet werden. Beide Prozesse können Teile des Datenstroms
weglesen. Dem Logger fehlen dann vollständige Datensätze oder einzelne Bytes.
Zum Beobachten das Archiv, die Logger-Ausgabe oder den bestehenden Kopier-Socket
verwenden. Ein zusätzliches interaktives `cat` mit Strg+C beenden; nicht alle
`cat`-Prozesse abschießen, denn darunter kann das reguläre Plugin sein.

Der Spiegel-Feed und der native Logger sind getrennte Prüfpunkte. Ein aktueller
HTTP-Heartbeat oder ein aktuelles Dashboard beweist nicht, dass der native
Logger neue Datensätze archiviert. Prüfen:

1. Zeitstempel und Abstände im ursprünglichen Roharchiv.
2. Aktuelle Quellzeitstempel im Spiegel-Feed.
3. Letzte erfolgreiche Logger-Verarbeitung und dessen Fehlerausgabe.
4. Tatsächlich neu geschriebene Datensätze im nativen Testarchiv, unter
   Berücksichtigung der verzögerten Pufferleerung.

## Druck aus dem Kombisensor getrennt übernehmen

**Stationsspezifische Entscheidung mit derzeit globaler Umsetzung in der
Anzeige:** Die folgenden `t1`/`t2`- und THB-Regeln entstanden wegen der Messwerte
unserer [Beispielstation](station-example.md). Sie sind keine allgemeine
Anweisung, funktionierende Temperatur-/Feuchtesensoren anderer Stationen zu
ignorieren. Die Anzeige unterdrückt diese THB-Felder derzeit dennoch generell;
eine konfigurierbare Auswahl ist noch nicht implementiert.

Die Plugin-Schritte in diesem Abschnitt gelten nur für den älteren Spiegelpfad.
Beim [direkten nativen TCP-Empfang](installer.md#direkter-nativer-meteohub-tcp-empfang)
läuft dieses Plugin nicht und ist kein `plugin-update` erforderlich.

Seit der Betreiberentscheidung vom 7. November 2026 wird der vollständige
ursprüngliche `thbN`-Datensatz an den nativen Logger gegeben. Beispiel:
`thb0 1289 100 9839` bleibt unverändert. Die auffällige Temperatur und Feuchte
sind damit im nativen Datensatz enthalten, werden aber vom Dashboard/SVG
ausgeschlossen. Deren Druckanzeige nutzt 983,9 hPa. Eigenständige Temperatur-
sensoren `t1` und `t2` bleiben die Temperaturquellen, auch für die ausdrücklich
gewählte Windchill-Berechnung. Keine Ersatztemperatur wird erfunden.

Das dokumentierte Pluginformat verlangt Temperatur, Feuchte und Stationsdruck
zusammen; Druck hat dort die Einheit 1/10 hPa. Beim Spiegeln eines sechsstelligen
THB-Rohdatensatzes werden nur die drei Eingabewerte übertragen, der Druck wird
gegebenenfalls von ganzen hPa in Zehntel umgerechnet. Native abgeleitete Felder
(Taupunkt, Vorhersage, Meeresspiegeldruck) werden nicht als Pluginfelder gesendet.
Ungültige Druckwerte außerhalb 300–1200 hPa und falsche THB-Feldzahlen werden
verworfen und protokolliert. Die native Verarbeitung einschließlich etwaiger
eigener Wertebereichsprüfungen muss auf dem Zielgerät nachgewiesen werden.

Das Provenienzjournal enthält nach erfolgreichem Pipe-Schreiben `plugin`-
Datensätze. Der Indexer übernimmt daraus und aus nativen Roharchiven nur
`pressure` für THB. Alte `pressure_only`-Journalzeilen bleiben lesbar, sind aber
kein Nachweis früherer nativer Archivierung. Bereits durchlaufene Quellwerte
werden bei der Aktualisierung nicht neu eingespielt.

Die native THB-Anzeige selbst kann die mitgelieferten Temperatur-/Feuchtewerte
weiterhin zeigen und Ableitungen berechnen. **Bei unserer Station** für
Nutzanzeigen und Exporte nur den Druck auswählen; die tatsächlich eingerichteten
Temperaturquellen `t1`/`t2` belassen. Nicht
behaupten, die proprietäre Anwendung unterdrücke diese Felder intern.

Bestehende Pi-Installationen mit `python3 install-pi.py plugin-update` umstellen,
während kein begrenzter Feed-/Loggertest läuft. Ein Git-Pull allein aktualisiert
die installierte Plugin-Kopie nicht. Anleitung und native Abnahme:
[Installer](installer.md#native-thb-druckaufzeichnung-aktualisieren).
Der Prozesstest `python3 test-feed-process.py`
prüft den tatsächlichen Plugin-Prozess und anschließend den tatsächlichen
SQLite-Indexer mit gültigem Druck, fehlerhaftem Druck sowie plausibler und
unplausibler THB-Temperatur.

## Broken pipe im Spiegel-Plugin

Der native Logger kann seinen Lesekanal schließen und auf das Ende des Plugins
warten. Die frühere allgemeine `OSError`-Behandlung in `live_feed_plugin.py`
fing auch `BrokenPipeError` ab und versuchte endlos weiterzuschreiben. Damit
endete das Plugin nicht, während der Logger auf dieses Ende wartete.

Das Plugin beendet sich jetzt bei geschlossenem Ausgabekanal mit Fehlerstatus,
damit die aufrufende Logger-Logik fortfahren kann. Es erfindet keine Messwerte
und versucht nicht, den physischen Sensor selbst neu zu starten. Ein Datensatz
wird erst nach erfolgreichem Schreiben in die Pipe als weitergeleitet
protokolliert. Dies ist weiterhin kein Archivierungs-ACK des nativen Loggers.
Frühere Provenienzzeilen können Schreibversuche enthalten, die noch vor dem
Pipe-Fehler protokolliert wurden; sie dürfen nicht rückwirkend als bestätigte
Archivierung gelten.

Der Prozesstest `python3 test-feed-process.py` schließt einen echten Pipe-Leser
und verlangt, dass das Plugin zeitnah endet, den fehlgeschlagenen Datensatz
nicht als erfolgreich weitergeleitet meldet und keinen Fortschritt speichert.
Die alte Fassung scheitert daran mit Timeout. Die bisherigen Tests für
Temperatur vor Wind und Neustart ohne Wiederholung bleiben bestehen.

Vor der Reparatur eines bestehenden Hängers Plugin, Logs, Fortschrittsdatei und
Testarchiv sichern. Danach nur den betroffenen Test-Logger neu starten und
echte neue Archivzeilen nachweisen. Historische Lücken bleiben sichtbar, solange
keine gesonderte Wiederherstellung aus belegten Originaldaten erfolgt ist.
