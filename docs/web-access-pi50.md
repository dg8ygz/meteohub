# Lokaler LAN-Schalter fuer die native Weboberflaeche

Betreiberauftrag und Abnahme: 16.11.2026, gegen 20:35 MEZ, Pi .50.

Die native Oberflaeche bleibt mit vorhandenem Basic-Passwortschutz auf
127.0.0.1:18090. Ein eigener systemd-socket-proxyd stellt sie bei Bedarf
zusaetzlich unter http://44.149.114.50:18090/ bereit. Erlaubt ist ausschliesslich
das Netz 44.149.114.0/26. HTTP ist unverschluesselt; der Schalter richtet kein
TLS und keine Router-Portweiterleitung ein. Das Backend sieht Proxy-Anfragen
als localhost und nicht mit der urspruenglichen Client-IP.

## Bedienung lokal auf dem Pi

Als root (oder mit sudo):

```sh
python3 /boot/firmware/meteohub-web-access.py lan
python3 /boot/firmware/meteohub-web-access.py local
python3 /boot/firmware/meteohub-web-access.py status
```

`lan` oeffnet, `local` schliesst den LAN-Zugang einschliesslich bestehender
Proxy-Verbindungen. Der originale localhost-Zugang bleibt bestehen.
Der Logger und der originale Webdienst werden dabei nicht neu gestartet.

**Nach einem Neustart ist der LAN-Zugang geschlossen.** Das Skript bleibt
auf der Bootpartition erhalten und kann mit `lan` erneut freigeben.
Es gibt keinen automatischen LAN-Autostart. Bei geaenderter IP/Subnetz muss
die Konfiguration des Skripts fachlich angepasst werden; es verweigert eine
Freigabe, wenn eth0 nicht die erwartete Adresse 44.149.114.50/26 besitzt.

## Umsetzung und Rueckbau

Quelle: `tools/web-access-pi50.py`, Downloadkopie
`http://44.149.114.34/meteohub-web-access.py`.
SHA256 der abgenommenen Fassung:
`01a742925bd205723b9055c40e2e40e2808af5b17626302013ca433975943346`.

`install` kopiert ausschliesslich das Skript auf die gepruefte Bootpartition
(UUID B2F0-82D2), stellt deren vorherigen RO-Zustand wieder her und aendert keine
Bootparameter. Units stehen ausschliesslich unter /run/systemd/system:
`meteohub-web-lan.socket` und `meteohub-web-lan.service`.

Die eigene nftables-Tabelle `inet meteohub_web_lan` verwirft Zugriffe auf
die LAN-IP/Port 18090 von ausserhalb des LANs. Sie wird vor Oeffnen des
Listeners eingerichtet und erst nach dessen Schliessung entfernt. Zusaetzlich
begrenzen systemd-IP-Regeln Socket und Proxy. Andere Firewall-Tabellen,
SSH, Logger-Ports und originale Web-Units werden nicht geaendert.

Zur Abschaltung genuegt `local`. Zur vollstaendigen Entfernung danach die
Skriptdatei auf der kurzzeitig schreibbar gemounteten Bootpartition entfernen
und deren urspruenglichen Mountzustand wiederherstellen.

## Abnahme auf der echten .50

- HTTP von .34 auf die LAN-IP: 401 mit Basic-Challenge.
- Nach `local`: LAN-Verbindung von .34 abgewiesen; localhost weiterhin 401.
- Nach erneutem `lan`: LAN wieder 401 mit Basic-Challenge.
- Verbindung aus temporaerem Netzwerk-Namespace mit Quelladresse
  198.18.255.2 blockiert; zwei verworfene Pakete im eigenen nft-Regelzaehler.
  Namespace, veth und Testroute anschliessend entfernt.
- Originale Logger-PID 168089 und Web-PID 735 unveraendert.
- Dauerhafte Skriptkopie stimmt bytegenau mit Quelle ueberein; Boot wieder RO.
- Keine fehlgeschlagenen systemd-Units nach Installation.
- Passwortgeschuetzte CGI-Seite nicht mit Benutzerkennwort aufgerufen;
  bestaetigt wurden Erreichbarkeit und die weiter bestehende Authentisierung.
- Kein weiterer Pi-Neustart fuer diesen Schalter durchgefuehrt. Rueckkehr
  zu localhost beim Boot folgt aus ausschliesslich fluechtigen Units/Regeln,
  nicht aus einem hier ausgefuehrten Neustarttest.

Private Belege: `/var/local/meteohub-private/review-20261116/web-lan-*.txt`.
Ergebnis ist eine punktuelle Abnahme, keine laufende Ueberwachung.
