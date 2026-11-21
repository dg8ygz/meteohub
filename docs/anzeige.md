# Dashboard und SVG

**Stationsspezifische Beispiele sind keine universellen Einstellungen.** Die
Auswahl von `t2` als Außentemperatur und der Ausschluss von THB-Temperatur/Feuchte
stammen aus unserem Stationsprofil. Teile davon sind noch fest im Code hinterlegt
und gelten deshalb derzeit auch bei anderen Installationen. Das
[gekennzeichnete Stationsbeispiel](station-example.md) nennt diese Grenzen
und trennt sie von den allgemeinen Installationsschritten.

Die kompakte SVG ist 600 × 180 Pixel groß. Nach einer passenden Webserver-
Einrichtung kann sie beispielsweise so eingebettet werden:

```html
<a href="/weather.svg"><img src="/weather.svg" width="600" height="180"
  alt="Aktuelle Wetterwerte und Windrichtung"></a>
```

Der Bildabruf erzeugt eine neue Darstellung, ein einfaches `img` aktualisiert
sich jedoch nicht selbstständig. Für HTTPS-Seiten muss auch der Bildpfad über
HTTPS erreichbar sein. Beim aktuellen Pi-Installer sind Dashboard, API und SVG
über dieselbe Webanmeldung geschützt; der Listener ist nur per SSH-Tunnel
zugänglich. Der ältere VM-Laboraufbau hatte einen gesondert veröffentlichten
SVG-Pfad. Das ist kein automatisch eingerichteter öffentlicher Pi-Zugang. `.htaccess` sperrt diesen Quellordner selbst
gegen Webzugriffe, sofern Apache die Datei auswertet. Für andere Webserver ist
die entsprechende Zugriffssperre separat einzurichten.

Das Dashboard benötigt Python 3, SQLite und Browser-JavaScript, die SVG nur einen
Bildbetrachter. Der Labormonitor benötigt zusätzlich Python `requests`, die
nativen Kompatibilitätshilfen unter anderem systemd, Lighttpd und gnuplot.
ARM-Binaries benötigen eine passende ARM-Laufzeit; ein x86-Host allein genügt nicht.

- Roharchive bleiben maßgeblich; der Anzeigeindex ist davon abgeleitet.
- Der native Empfang soll auch die ursprünglichen THB-Datensätze aufzeichnen.
  Dashboard und SVG verwenden daraus nur plausiblen Stationsdruck;
  THB-Temperatur, Feuchte und Meeresspiegeldruck werden dort nicht angezeigt.
  Für den Stationsumzug ist der [direkte native TCP-Empfang](installer.md#direkter-nativer-meteohub-tcp-empfang)
  vorgesehen: kein JSON-Zubringer oder eigenes Empfangsplugin. Eine passende
  native Sensorzuordnung ist erforderlich. An unserer Beispielstation ist die
  THB-Archivierung im begrenzten Pi-Test nachgewiesen; jede weitere Station
  benötigt ihre eigene Abnahme.
- Eine gültige Regenrate wird auch bei negativem Gesamtzähler übernommen.
  Der negative Gesamtzähler wird verworfen, ohne eine Zählerkorrektur zu erfinden.
  Dadurch bleibt der Zeitstempel der aktuellen Regenrate erhalten.
- Fehlende oder veraltete aktuelle Werte erscheinen als fehlend, nicht als Null.
- Windvektoren zeigen den 24-Stunden-Mittelwind und die maximale Böe je Sektor.

Zugangsdateien für Relay/Monitor werden nur in einem privaten Laufzeitverzeichnis
angelegt. Die Skripte laden sie relativ zu ihrem eigenen Standort; deshalb
Laufzeitkopien außerhalb des Webroots verwenden. Keine echten Zugangswerte in
Beispiele übernehmen. Dienste und Authentifizierung müssen getrennt eingerichtet
werden; dieser Ordner führt bei einem Checkout keine Installation aus.
