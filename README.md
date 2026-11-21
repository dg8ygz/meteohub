# Meteohub auf Debian Trixie

Kompatibilitätshelfer für bestehende Meteohub-Wetterstationen sowie ein
HTML-Dashboard und eine einbettbare SVG-Wettergrafik ohne Flash.

**Entwicklungsstand:** Migration und Funktionstests vorhanden; kein fertiges
Installationsimage und keine vollständige Produktionsfreigabe.
Herstellerprogramme und passende Nutzungslizenz werden separat benötigt.

## Einstieg

| Aufgabe | Anleitung |
|---|---|
| Neuen Pi vorbereiten | [Pi 3/4 mit Trixie](docs/raspberry-pi-setup.md) |
| Originalprogramme beschaffen | [Herstellerquelle und Voraussetzungen](docs/originalsoftware.md) |
| Installieren oder aktualisieren | [Installer](docs/installer.md) |
| Empfang und Autostart betreiben | [Dauerbetrieb](docs/continuous-operation.md) |
| Dashboard oder SVG nutzen | [Anzeige](docs/anzeige.md) |
| Code verstehen und testen | [Komponenten](docs/komponenten.md) · [Tests](docs/tests.md) |
| Grenzen und offene Arbeit prüfen | [Projektstand](docs/current-state.md) |

Der vorgesehene Datenweg ist:

```text
bestehende Station → nativer TCP-Logger → Roharchiv → Dashboard / SVG
```

Die älteren JSON-/Plugin-Helfer dienen anderen Testwegen. Sie gehören nicht
parallel an denselben Stationsanschluss. Sensorzuordnung und feste Annahmen der
Anzeige sind im [Stationsbeispiel](docs/station-example.md) dokumentiert.

## Wichtige Grenzen

- Der eingebaute Hersteller-Updater ist in dieser Portierung kein unterstützter Updateweg.
  Die [Updateanleitung](docs/installer.md#updates-auf-dieser-trixie-portierung) verwenden.
- Ein Checkout oder `git pull` aktualisiert keine laufende Installation.
- Der neue [OpenSSL-Adapter](docs/unmodified-runtime-investigation.md) ist ein isolierter Versuch;
  der Installer verwendet ihn noch nicht.
- Private Konfigurationen, Aktivierungsdaten, Wetterarchive und Herstellerdateien bleiben außerhalb des Repositorys.

Dies ist ein unabhängiges Projekt, keine offizielle Meteohub-Veröffentlichung.
