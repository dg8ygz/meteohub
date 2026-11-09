# Lesender ifconfig-Anzeigeadapter

Meteohub 5.1e sucht im nativen CGI die alten net-tools-Ausgabetexte
`HWaddr ` und `inet addr:`. Der Ziel-Pi liefert dagegen `ether` und `inet`.
Die Fehlermeldung allein beweist keinen ENOSYS-Systemaufruffehler.

`tools/ifconfig-compat.py` fragt ausschliesslich `/usr/sbin/ip -j address show`
im aktuellen Netzwerk-Namespace ab. Es formatiert die echten IPv4-/IPv6- und
Ethernetdaten fuer alte Leser. Erlaubt sind Auflisten, `-a` oder ein einzelner
Schnittstellen-/IPv4-Labelname. Konfigurationsargumente werden abgelehnt.
Statistiken und nicht vorhandene Adressen werden nicht erfunden.

## Begrenzter Zieltest

Quelle auf den Pi uebertragen, SHA256 mit dem lokal geprueften Stand vergleichen.
Als root nach `/usr/local/libexec/meteohub-ifconfig-compat.py` installieren (0755), dann
`/run/systemd/system/meteohub-web-test.service.d/40-ifconfig-compat.conf` anlegen:

```ini
[Service]
BindReadOnlyPaths=/usr/local/libexec/meteohub-ifconfig-compat.py:/usr/sbin/ifconfig
RestrictAddressFamilies=
RestrictAddressFamilies=AF_INET AF_UNIX AF_NETLINK
```

Bestehende BindReadOnlyPaths nicht leeren. `daemon-reload` und ausschliesslich
Webdienst neu starten. Die native Laufzeit verlinkt /sbin nach usr/sbin;
der private Dateimount ueberdeckt die aus dem Host eingebundene Datei nur
fuer diesen Dienst. Das Hostwerkzeug und der Logger bleiben unveraendert.

Pruefen: Webdienst active, Logger-MainPID unveraendert, alte Ausgabe ueber
`nsenter --target WEBPID --mount --net --root --wdns=/ -- /sbin/ifconfig eth0`.
Danach die echte native CGI-Seite neu laden. Erst deren Ergebnis bestaetigt,
ob die Formatangleichung die Warnung beseitigt. Die lokalen Tests enthalten
keinen proprietaeren ARM-CGI-Lauf.

Rueckbau: Nur dieses Drop-in entfernen, daemon-reload, Webdienst neu starten;
danach die Adapterdatei entfernen. Bei fehlgeschlagenem Webstart denselben
Rueckbau ausfuehren. Keine Netzwerkparameter aendern.

Der erste Pi-Test belegte: /run ist noexec, der Dateimount erbt diese Sperre.
Der ausdrueckliche Python-Aufruf funktionierte, direkte Ausfuehrung nicht.
Deshalb Quelle auf einem ausfuehrbaren Mount ablegen; /run nicht auf exec setzen.
Der Integrationstest prueft jetzt auch direkte Ausfuehrung und reproduziert
den Fehler mit einer echten noexec-tmpfs-Quelle vor dem Wechsel der Quelle.

Nach Wechsel des Ablageorts bestaetigte der Betreiber direkte Ausfuehrung im
Web-Namespace und Wegfall der MAC-Fehlermeldung. Die allgemeine Netzwerkwarnung
blieb. Die CGI-Binaeranalyse zeigt diesen Warnpfad bei fehlender Ausgabe aus
`ifconfig eth0 | grep "inet addr:"` (5.1e, VA 0x6e8c8 bis 0x6ead4).
Die bestehende Dienstpolicy erlaubt nur AF_INET/AF_UNIX; iproute2 benoetigt
AF_NETLINK. nsenter uebernimmt keinen Seccomp-Filter des Zielprozesses.
Ein echter lokaler systemd-Test reproduziert das Versagen des Adapters mit
dieser Policy. Mit AF_NETLINK liefert er Daten; ein Netzwerk-Aenderungsversuch
im privaten Testnetz scheitert weiterhin mit EPERM bei leerem Capability-Satz.
Deshalb fuer den Adapter nur im Webdienst die obige Allowlist verwenden.
IPAddressDeny/Allow und CapabilityBoundingSet nicht lockern. Zielabnahme
der AF_NETLINK-Ergaenzung noch offen. Kein weiterer Loggerstart erforderlich.

Das Drop-in liegt unter /run, die Quelle im fluechtigen Host-Overlay unter
/usr/local/libexec. Beide verschwinden beim Neustart aus diesem Testbetrieb.
Nach Zielabnahme zusammen mit dem loggerd-PID-Drop-in in einem RW-Wartungsboot
dauerhaft installieren (Quelle z.B. /usr/local/libexec, Drop-in /etc/systemd).
Nicht unter aktivem Overlay in das untere Root-Dateisystem schreiben.
Native Netzwerk-Konfigurationsfunktionen werden mit diesem Adapter ausdruecklich
nicht implementiert. Dropbear-/Samba-PID-Meldungen sind davon unabhaengig.
