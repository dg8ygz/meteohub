# Unveränderte Herstellerprogramme: Untersuchung vom 17. November 2026

## Ergebnis und Umfang

Ein kleiner externer Bibliotheksadapter ist technisch aussichtsreich: Die sechs
untersuchten originalen 5.1e-ARMHF-Programme konnten im isolierten QEMU-Test ihre
Bibliotheken laden. Alle 17 benötigten alten Crypto-Funktionsimporte bestanden
zusätzlich Funktionstests auf x86-64 und emuliertem ARMHF mit OpenSSL 3.

Das ist **keine vollständige Anwendungs- oder Imagefreigabe**. Der bestehende
Installer verwendet weiterhin seine bisherige OpenSSL-Anpassung. Er wurde
nicht auf den Versuch umgestellt. Auf dem produktiven Pi .50 wurden für diese
Untersuchung keine Dateien, Dienste oder Bootparameter geändert.

Quellcode und wiederholbare Funktionstests liegen unter
[`experiments/openssl-bridge`](../experiments/openssl-bridge/README.md).
Es wurden weder proprietäre Programme noch Konfigurationen, Aktivierungswerte
oder private Schlüssel in das Repository übernommen.

## Statischer Befund

Grundlage sind die geprüften Raspberry-Pi-Programme des Herstellerupdates 5.1e,
nicht die alten ARMEL-Dateien aus `setup-plug.tgz`. Die Quellenentscheidung
steht im [SheevaPlug-Bericht](vendor-setup-plug-review.md).

| Programm | OpenSSL-Abhängigkeit | Importierte Crypto-Funktionen |
|---|---|---|
| `loggerd` | keine | keine |
| `loggereval` | keine | keine |
| `meteometar` | `libssl.so.1.0.0` | keine |
| `meteonet` | SSL und Crypto 1.0.0 | `MD5` |
| `meteoschedule` | SSL und Crypto 1.0.0 | `MD5` |
| `meteohub.cgi` | SSL und Crypto 1.0.0 | 16 BIO-, PEM-, EVP- und RSA-Funktionen |

Diese sechs Programme importieren keine TLS-Funktionen. Das ist keine Aussage
über sämtliche Dateien im Herstellerarchiv oder über erst zur Laufzeit
nachgeladene Funktionen.

Die geprüften Original-Hashes, Bibliotheksnamen und versionierten Importe sind
als [reine Prüfmetadaten](../experiments/openssl-bridge/reviewed-imports.json)
beigefügt. Quellkopie und verwendete Testkopie aller sechs Programme wurden
abschließend erneut gegen diese Hashes verglichen.

Der Adapter exportiert 17 Namen mit Version `OPENSSL_1.0.0` und ruft jeweils
explizit den gleichnamigen Export `OPENSSL_3.0.0` aus `libcrypto.so.3` auf.
Ein leeres Objekt erfüllt ausschließlich die ungenutzte SSL-Bibliotheks-
abhängigkeit. Es stellt keine TLS-Funktionen und keine Erfolgssimulation bereit.
Die Originaldateien werden nicht gepatcht. Es wird keine OpenSSL-1-Implementierung
mitgeliefert.

Ein Major-Versionswechsel garantiert keine ABI-Kompatibilität. Insbesondere
alte Strukturzugriffe und abweichende Semantik bleiben zu prüfen; die
[OpenSSL-Migrationsdokumentation](https://docs.openssl.org/3.0/man7/migration_guide/)
beschreibt diese Grenzen. Der Versuch ist bewusst auf die geprüften Importe
begrenzt.

## Nachweise und Grenzen

| Prüfung | Ergebnis | Aussagegrenze |
|---|---|---|
| Exakte Exporte, alte Importversionen und explizite moderne Weiterleitungen | bestanden | keine allgemeine OpenSSL-1-Emulation |
| MD5-Testvektor und binärer Base64-Rundlauf | bestanden auf x86-64; ARM-Probe prüft zusätzlich `abc`/`YWJj` | nur getestete Eingaben |
| PEM gültig/ungültig; RSA-Referenz nach Freigabe des EVP-Objekts | bestanden auf beiden Architekturen | keine vollständige Prüfung aller Objektverwendungen im CGI |
| RSA-Block mit frischem Testschlüssel gültig; Nullblock zurückgewiesen | bestanden auf beiden Architekturen | kein Hersteller-Aktivierungstest |
| Alle sechs Originalprogramme: Loader-Trace ohne fehlende Bibliotheken/Versionen | Exit 0; Hashes unverändert | nicht gleichbedeutend mit Funktionsausführung |
| Original-CGI in minimaler Testumgebung | HTML bis zur Lizenzannahmeseite ausgegeben | Exit 1; fehlende Konfiguration/Helfer und schreibgeschützte Konfiguration; keine vollständige CGI-Abnahme |
| Native ARM-Hardware, Stationsbetrieb, Auswertung, Sicherung/Wiederherstellung | **OFFEN für diesen Adapter** | bisherige Betriebsnachweise gelten für den bestehenden Runtime-Pfad |

Die Tests verwenden ausschließlich neu erzeugte Testschlüssel. Sie akzeptieren
keine Herstellerlizenz stellvertretend und erzeugen keine Aktivierung.

Testumgebung: GCC 14, QEMU user 10.0.13, ARMHF-glibc 2.41-11cross1 und
ARMHF-OpenSSL 3.5.7-1~deb13u2; Host-OpenSSL 3.5.7-1~deb13u3. Das sind die
konkret geprüften Versionen, keine Empfehlung, diese Paketstände für ein
späteres Release festzuhalten. ARM-Pakete wurden privat entpackt; der
Debian-Paketindex wurde anhand signierter Release-Metadaten und die Downloads
anhand seiner Prüfsummen geprüft. Es erfolgte keine globale Cross-Paketinstallation.
Herstellerprogramme liefen ohne Netzwerk, unprivilegiert in einer getrennten,
schreibgeschützten Testwurzel. Die vollständigen privaten Testartefakte liegen
unter `/var/local/meteohub-private/unmodified-runtime-20261117/`.

## Was dem frischen Installer noch fehlt

Die folgende Bestandsaufnahme trennt vorhandenen Code von bereits auf .50
erprobten, aber nicht vollständig in den allgemeinen Erstinstallationsablauf
überführten Komponenten.

| Bereich | Vorhanden | Noch erforderlich |
|---|---|---|
| Herstellerbezug | `install-pi.py prepare`: HTTPS-Downloads mit festen Hashes, separate Laufzeit | unveränderte Programme als eigener Staging-Pfad; exakte Import-/Hashfreigaben; keine Binäranpassung in diesem Pfad |
| OpenSSL 3 | bisheriger Patch-Pfad und jetzt externer Versuch | native Abnahme, privater Bibliothekspfad, Manifest/Abbruch bei unbekannten Importen, Rückweg |
| Webzugang | Web-Vorbereitung, eigenes Passwort, zunächst Loopback | allgemeiner Erststartablauf und hostunabhängige LAN-Freigabe; keine privaten Netzadressen übernehmen |
| Logger und Dashboard | `live-service.py`, Dienste und geprüfter direkter TCP-Betrieb | Ersteinrichtung mit nutzereigener Station; kein vorgegebener privater Endpunkt |
| Native Auswertung | `tools/native-eval.py` und Unit vorhanden | generisch in Erstinstallation, Reihenfolge und Sicherung einbinden; Pfade/Benutzer parameterisieren |
| Statusanzeige, Logger-Zeitpfad, WAN | einzelne Betriebsanpassungen auf .50 und Teile im Repository | vollständige generische Installation, Tests und Rückbau ohne Kennungs-/Aktivierungsanpassung |
| RAM und Sicherungen | `ram-storage.py`, Sechs-Stunden-Plan | zusammenhängende Erstinstallation; produktiven Freeze-Pfad vollständig übernehmen und mit allen schreibenden Diensten prüfen |
| Host-Overlay, Boot und Persistenz | auf .50 erprobt | neue Speicheraufteilung, Größenprüfung, Wartungsmodus und Wiederherstellung für frische Karten automatisieren |
| Öffentliches Basisimage | Quellenentscheidung dokumentiert | reproduzierbarer Build aus frischem OS; keine privaten Klone, Herstellerdateien oder Download-Caches |
| Erster Start | einzelne Setup-Schritte vorhanden | individuelle Benutzerzugänge, SSH-Hostschlüssel und Machine-ID; keine alten Schlüssel/Passwörter/Lizenzwerte |
| Release-Abnahme | bestehende Tests und Betriebsberichte | frische Karte booten; neue SSH-Anmeldung; CGI, Daten, Auswertung, Sicherungen, Restore und Neustart nachweisen |

Der Bericht ersetzt keinen noch fehlenden Installer-Code. Insbesondere der
produktive Freeze-Checkpoint und die Statusanpassungen dürfen nicht allein
aufgrund ihrer Betriebsnachweise als vollständiger öffentlicher Installer
ausgegeben werden.

## Nächste Schritte

1. Den externen Adapter auf einer separaten Pi-Testkarte mit eigener frischer
   Konfiguration abnehmen. Vorher keine Umstellung des produktiven Loggers.
2. Bei Erfolg einen expliziten Installer-Pfad für unveränderte Dateien bauen;
   Programm-Hashes, Symbolumfang und privaten Bibliothekspfad streng prüfen.
3. Die obigen Betriebskomponenten in eine allgemeine Erstinstallation überführen.
4. Erst dann ein sauberes Basisimage bauen und auf frischer Karte vollständig
   testen. Herstellerprogramme erst beim jeweiligen Nutzer herunterladen.

Unveränderte Programmdateien und getrennte Downloads sind technische Maßnahmen,
keine pauschale rechtliche Freigabe. Anwendungsbedingungen und Lizenzen der
verteilten Betriebssystemkomponenten bleiben zu beachten.
