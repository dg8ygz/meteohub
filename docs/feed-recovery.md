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

Der aktuelle Spiegelpfad übernimmt von `thbN` ausschließlich den Stationsdruck.
Zum Beispiel ergibt `thb0 1289 100 9839` einen Druckwert von 983,9 hPa; weder
die Temperatur von 128,9 °C noch die Feuchte werden als Messwerte weitergegeben.
Das gilt auch dann, wenn die THB-Temperatur wieder plausibel aussieht.
Eigenständige Temperatursensoren wie `t1` und `t2` bleiben davon unberührt.

Das Plugin schreibt dafür ausdrücklich markierte `pressure_only`-Datensätze
in sein privates Provenienzjournal. Der Originaltext bleibt dort als Beleg
erhalten, wird aber nicht als kombinierter THB-Datensatz auf die native
Logger-Pipe geschrieben. Der Dashboard-Indexer übernimmt daraus nur das Feld
`pressure`, nach einer eigenen Bereichsprüfung auf 300–1200 hPa.
Es gibt keine erfundene Ersatztemperatur. Dies ist eine separate Speicherung
im Anzeigeindex, kein Nachweis eines THB-Datensatzes im nativen Roharchiv.

Bei einer Installation `live_feed_plugin.py` und `dashboard/index_weather.py`
gemeinsam übernehmen. Bestehende laufende Installationen werden durch einen
Git-Pull allein nicht umgestellt. Der Prozesstest `python3 test-feed-process.py`
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
