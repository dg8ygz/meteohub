# Projektstand

Letzter dokumentierter Entwicklungsstand: 17.11.2026. Diese Übersicht beschreibt
Quellen und bisherige Prüfungen, keinen laufend abgefragten Gerätezustand.

| Bereich | Stand |
|---|---|
| Meteohub 5.1e auf Trixie | Native Oberfläche, TCP-Empfang, Roharchiv und Auswertung in der Beispielinstallation erprobt |
| Dashboard / SVG | Anzeige aus abgeleitetem Index; Sensorwahl teilweise stationsspezifisch |
| Installer | Vorbereitung, Tests, Extension-Update und Live-Dienste vorhanden; vollständige Erstinstallationsabnahme offen |
| OpenSSL-Adapter ohne Binäränderung | Isolierte Funktionstests erfolgreich; nicht in den Installer integriert und nicht auf nativer Hardware abgenommen |
| Beispielstation nach Bereinigung am 16.11. | Aktivierung entfernt, CGI meldet Demo abgelaufen; Wetterarchive erhalten |

## Offene Arbeit

1. Allgemeine Erstinstallation einschließlich Hardware, Neustart, Sicherung und Wiederherstellung abnehmen.
2. Durchgehenden Langzeitbetrieb und vollständigen Archivabgleich nachweisen.
3. THB-Auswertung vervollständigen: isolierter Test grenzt leere Aggregate auf das Taupunktfeld ein;
   die produktive Druckauswertung wurde dafür noch nicht umgestellt.
4. Den neuen OpenSSL-Adapter erst nach vollständiger Anwendungsprüfung als eigenen Installationsweg integrieren.

## Nachweise

- [OpenSSL-Untersuchung und fehlende Installer-Schritte](unmodified-runtime-investigation.md).
- [Native Auswertung](native-evaluation.md), [THB-Analyse](thb-analysis-2026-11-16.md).
- [Entfernte Aktivierung und SD-Bereinigung](sd-cleanup-2026-11-16.md).
- [Historische Betriebsnotizen](history-2026-11.md): datierte Einzelprüfungen und frühere Zwischenstände.

Für den Betrieb gelten [Installer](installer.md) und [Dauerbetrieb](continuous-operation.md).
Alte Aktivierungsnachweise und frühere Dienstzustände sind keine heutige Freigabe.
