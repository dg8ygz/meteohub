# Komponenten

Pfade in dieser Tabelle gelten relativ zum Repository-Hauptverzeichnis.

| Dateien | Aufgabe |
| --- | --- |
| `tools/inspect-original.py` | Liest ELF-Metadaten und Symlinks aus dem separat geöffneten Originalimage, ohne dessen Programme auszuführen. |
| `tools/stage-openssl3.py`, `tools/test-crypto-adaptation.py` | Erstellen private, hashgeprüfte OpenSSL-3-Testkopien aus dem Herstellerimage und prüfen die ELF-Änderungsgrenzen; kein Installer und keine allgemeine ABI-Garantie. |
| `tools/stage-update.py`, `tools/test-update.py` | Bereiten das verpflichtende 5.1e-Kernupdate aus dem Herstellerpaket in einer neuen privaten Kopie vor; keine alten Systemdateien oder Update-Skripte werden ausgeführt/installiert. |
| `tools/probe-cgi.py` | Führt nach einer echten Isolationsprüfung einen CGI-Probelauf oder die native Konfigurationsgenerierung (`-1`) oder einen begrenzten Plug-in-Datenwegtest aus; keine Webserver- oder Loggerinstallation. |
| `tools/stage-runtime.py`, `tools/test-runtime.py` | Bereiten einen privaten Konfigurations-/Datenbaum für den CGI-Test vor und prüfen Dateiauswahl sowie optional die tatsächliche systemd-Isolation. |
| `tools/live-service.py`, `tools/test-live-service.py` | Dauerhafter direkter TCP-Logger, private Web-/Indexdienste, Autostart, Status und Rückbau nach passender nativer Testabnahme. |
| `tools/web-test.py`, `tools/test-web.py` | Passwortgeschützte Browser-Testoberfläche über Loopback/SSH und echte HTTP-Tests mit synthetischem CGI; keine Bootfreigabe oder Loggerinstallation. |
| `tools/prepare-tcp-plugin.py`, `tools/test-tcp-plugin-prepare.py` | Prüfen die native Plug-in-Konfiguration und legen den Snapshot-Adapter im privaten Testbaum an; starten weder TCP-Zubringer noch Logger. |
| `tools/tcp-feed.py`, `tools/test-tcp-feed.py` | Empfangen den bestehenden Plugin-Kopierstrom einer Station ausschließlich lesend und erstellen begrenzte JSON-Snapshots für das Spiegel-Plugin. |
| `cgi_compat.sh` | Ergänzt bei leerem GET des nativen Haupt-CGI die Startseite. |
| `gnuplot_compat.py` | Übersetzt alte Plot-Präambeln für das Distributions-gnuplot; verändert keine Roharchive. |
| `prepare_logger.py`, `rcloggerd` | Begrenzen den nativen Logger auf die isolierte Pluginquelle und steuern dessen systemd-Dienst. |
| `live-feed-relay.py`, `read-source-socket.sh` | Lesender Zubringer vom bestehenden Stationssocket über SSH zum authentifizierten Test-Endpunkt. |
| `live-feed.cgi`, `live_feed_plugin.py` | Übernahme der Messwertkopie mit Herkunftsprotokoll, Frischeprüfung und persistentem Cursor; Wind wartet beim Start auf eine echte Temperatur. |
| `live-status.cgi`, `live-test-monitor.py` | Statusabfrage und zeitlich begrenzter Labortest; keine automatische Alarmierung. |
| `normalize_native.py`, `verify-native-records.py` | Normalisierung und Abgleich von Plugin- und nativen Archivzeilen. |
| `stop_qemu.py` | Kontrolliertes Ausschalten des Testgasts über den QEMU-Monitor. |
| `dashboard/` | Abgeleiteter SQLite-Anzeigeindex, JSON-API, HTML-Dashboard und eigenständige SVG-Grafik. |

Die Skripte enthalten bewusst noch feste **Testgastpfade**. Sie sind keine
universellen Installationsprogramme. Insbesondere `verify-native-records.py`
bezieht sich auf den Labormonat November 2026 und dessen lokale Vergleichsbasis.
