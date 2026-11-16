# THB-Auswertung: isolierter Vergleich vom 16. November 2026

Auf Betreiberauftrag auf Pi .50 ausgeführt, 21:35:47–21:38:56 MEZ.
Ausschließlich Datenkopien in eigenen, netzlosen systemd-Testdiensten;
keine Änderung am Quell-Pi .9, Logger, Produktivarchiv oder produktiven
Aggregaten. Kein Sensorwert wurde durch einen Testwert ersetzt.

## Ergebnis

Die vorherige Vermutung, allein die Temperatur von 128,9 °C verhindere die
native THB-Auswertung, war zu ungenau. **Entscheidend ist in diesen Datensätzen
das dritte THB-Messwertfeld, das der Auswerter als Taupunkt verarbeitet.**

Beispiel für die vorhandene Struktur:

```text
Zeitstempel thb0 1289 100 1289 9620 -1 10015
```

Bei unveränderten Druckfeldern wurden jeweils dieselben 575 THB-Rohzeilen aus
den letzten 48 Stunden mit dem originalen 5.1e-Programm ausgewertet. Kontroll-
kanal `t1` ergab in allen neun ersten Fällen dieselben 573 Aggregate und
identische Dateihashes.

| Änderung ausschließlich in der Testkopie | THB-Fünf-Minuten-Aggregate |
| --- | ---: |
| Keine | 0 |
| Nur Temperaturfeld auf Testwert 200 | 0 |
| Nur drittes THB-Messwertfeld auf Testwert 93 | 573 |
| Temperatur und drittes Messwertfeld geändert | 573 |
| Nur Feuchtefeld geändert | 0 |
| Nur Vorhersagefeld geändert | 0 |
| Weitere Kombinationen mit geändertem dritten Messwertfeld | 573 |

Der Auswerter gibt Testwert 93 in der Taupunktgruppe als **93,0** aus;
Testwert `9.3` wird dort zu **9,0**. Die Temperatur 1289 erscheint dagegen
als **128,9**. Die beiden Felder werden folglich nicht gleich skaliert.
Ein zusätzlicher Grenztest akzeptiert im dritten Feld 150, verwirft aber 151.
Der ursprüngliche Feldwert 1289 liegt deutlich darüber. Damit ist die
feldbezogene Ablehnung reproduziert; nicht nachgewiesen ist bislang, an
welcher Stelle zwischen Quelle, Loggerformat und Auswerter die unterschiedliche
Skalierung entsteht. Eine automatische Division des Produktivfelds wäre daher
keine bereits geprüfte Reparatur.

Einfache Versuche mit vermeintlichen Fehlwertkennzeichen `-999999`, `-99999`
und `-99999.9` erzeugen ebenfalls keine THB-Aggregate. Sie sind keine
freigegebene Methode, um Temperatur/Taupunkt zu unterdrücken und nur Druck
zu verarbeiten.

## Betrieb und verbleibende Arbeit

- Die beiden Druckfelder und alle Zeitstempel blieben in sämtlichen Testfällen
  unverändert. Druckaggregate konnten bei akzeptiertem Taupunktfeld entstehen.
- Roharchiv-Präfixe vor/nach jedem Testlauf per SHA-256 identisch.
- Logger-PID durchgehend 168089; keine Produktionsdienste neu gestartet.
- Temporäre Auswertungsverzeichnisse anschließend entfernt. Berichte und
  ausdrücklich als `TEST-ONLY` bezeichnete Ergebnisse außerhalb der
  produktiven Laufzeit aufbewahrt; kein Einspielen in Dashboard oder Checkpoint.
- **Produktive native THB-Aggregate bleiben vorerst leer.** Der Dashboard-Druck
  aus dem Roharchiv ist davon getrennt und wird nicht verändert.

Für eine Reparatur muss die Rohfeld-Skalierung an Quelle/Logger/Auswerter
abgeglichen und eine Druckverarbeitung ohne erfundene Temperatur-/Feuchtewerte
nachgewiesen werden. Die ursprünglichen Rohdaten bleiben dabei erhalten.

Private Belege auf .34:
`/var/local/meteohub-private/thb-analysis-20261116/reports.json`,
Testskripte, Fallausgaben und ergänzende Binäranalyse im selben Verzeichnis.
Die Berichte wurden vor einem möglichen Pi-Neustart auf .34 gesichert.
