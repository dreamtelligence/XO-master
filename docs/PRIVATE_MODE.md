# Privater Arbeitsmodus – 18.11.2026

## Artist Workspace

Der React-Workspace wird mit `npm start` explizit gestartet. Seine API akzeptiert geschützte Aufträge über Projekt- und Asset-IDs. Die fünf vorhandenen Modal-Dienste bieten zusätzlich den geschützten Workspace-Vertrag. In der neuen UI gibt es keine Browserroute zum rohen Modal-Proxy. Der bisherige Loopback-Server bleibt als Legacy-Modus verfügbar. [Start und Bedienung](ARTIST_WORKSPACE.md), [Workspace-Prüfungen](verification/2026-11-18-artist-workspace.md).

## Historischer Stand der geschützten Altansicht

Die lokale App zeigt die vier Werkzeuge direkt, ohne obere Navigation, Marketingbereiche, Anmeldung, Preise, Stripe oder Credit-Gates. Die deaktivierten Implementierungen sind im Projekt erhalten; siehe [`disabled/`](../disabled/README.md).

Die fünf bestehenden Modal-Apps wurden mit `requires_proxy_auth=True` neu bereitgestellt (Deployment-Tag `private-20261118`). Der Schutz gilt für Uploads, Status, Health, Vorschauen und Downloads einschließlich alter Job-URLs. Modal prüft die Zugangsdaten vor dem Aufruf des Web-Containers; siehe [Modal Proxy Tokens](https://modal.com/docs/guide/webhook-proxy-auth).

Die App ist für den privaten Betrieb auf diesem Mac eingerichtet. Ein öffentlicher Vercel-Proxy wurde nicht eingerichtet. Bisherige öffentliche Frontends können die jetzt geschützten Modal-URLs ohne Authentifizierung nicht mehr verwenden. Ein Vercel-Deployment der deaktivierten Commerce-Handler wurde nicht vorgenommen; externe Stripe-Konfigurationen und Abonnements wurden nicht geändert.

## Lokaler Zugriff

`python3 dev_server.py` startet die App ausschließlich auf `127.0.0.1:8765`. Im Browser: http://localhost:8765.

Der Browser verwendet relative `/api/modal/<dienst>/…`-Pfade. Der lokale Server liest `~/.config/dreamtelligence-xo/modal.json` und setzt `Modal-Key` und `Modal-Secret` ausschließlich beim serverseitigen Weiterleiten. Der Browser bekommt weder die Zugangsdaten noch die Cloud-Konfiguration. Die private Datei hat Rechte `600`; breitere Dateirechte lehnt der Server ab.

Ohne Konfiguration bleibt Modal geschlossen (HTTP 503). Im Repository liegt kein funktionierender privater Proxy-Token. Der frühere statische `http.server` reicht für diese geschützte App nicht mehr aus.

Nur erlaubte Frontend-Dateien werden ausgeliefert. Repository-Dateien, Dotfiles, Konfiguration und Verzeichnislisten bleiben gesperrt. Der Proxy prüft Host, Origin und Fetch-Site, erlaubt ausschließlich bekannte Dienste/Routen und begrenzt Uploads. Fremde Webseiten sollen dadurch den privaten Proxy nicht für Aufträge benutzen können. Der Server bindet nicht an LAN-Adressen.

## Eigene Einrichtung nach einem Clone

1. Eigene Modal-Apps im eigenen Workspace deployen. Die fünf `modal_app_*.py` behalten den Proxy-Auth-Schalter eingeschaltet.
2. Eigenen Proxy-Token in den Modal-Einstellungen oder mit `modal workspace proxy-tokens create --json` erzeugen. Die Ausgabe enthält Geheimnisse und darf nicht ins Repository, in Screenshots oder öffentliche Logs gelangen.
3. `~/.config/dreamtelligence-xo/modal.json` erstellen und mit `chmod 600` schützen. Beispiel mit Platzhaltern:

```json
{
  "token_id": "wk-PLACEHOLDER",
  "token_secret": "ws-PLACEHOLDER",
  "services": {
    "separation": "https://YOUR-SEPARATION-APP.modal.run",
    "mastering": "https://YOUR-MASTERING-APP.modal.run",
    "transcription": "https://YOUR-TRANSCRIPTION-APP.modal.run",
    "enhancement": "https://YOUR-ENHANCEMENT-APP.modal.run",
    "generation": "https://YOUR-GENERATION-APP.modal.run"
  }
}
```

Alternativer Pfad: `python3 dev_server.py --config /absoluter/privater/pfad/modal.json`.

Proxy-Tokens sind Workspace-Zugangsdaten. Personen mit gültigem Proxy-Token oder entsprechendem Workspace-Zugang können weiterhin berechtigt zugreifen. Schutz vor kopiertem Quellcode ersetzt keinen Schutz vor weitergegebenen Zugangsdaten oder einem kompromittierten lokalen Benutzerkonto. Token-Rotation ist über Modal möglich; danach die private Datei ersetzen und den lokalen Server neu starten.

## Prüfungen

- Alle fünf Live-Apps: anonymer Health-Aufruf **401**, anonymer POST **401**, falscher Token **401**, eigener Token bei Health **200**.
- Lokaler Proxy: Health **200**, leerer POST **422** von der echten FastAPI-Validierung; Authentifizierung erfolgreich, ohne einen Verarbeitungsauftrag anzulegen.
- Lokale Credit-/Checkout-/Paywall-/Webhook-Routen: **410**. Fremder Origin: **403**. Repository-Dateiabruf: **404**. Keine Proxy-Zugangsdaten im ausgelieferten HTML/CSS.
- Neun automatisierte Tests prüfen fehlende Konfiguration, Host/Origin-Grenzen, Pfadzugriff, Dateirechte, Upload-Limit, serverseitige Header und verpflichtende Authentifizierung der fünf Modal-Apps.
- Echter Auftrag über den lokalen Proxy nach der Absicherung: Mastering-Job `04bd9b68-6c9f-4aff-8e4d-08dfc8f84162`, synthetischer achtsekündiger Clip, `completed`, 16-/24-Bit-WAV jeweils HTTP 200. Vom Backend gemeldete Verarbeitung: 2,87 Sekunden. Kein Modal-Schlüssel in Antwortheadern.
- Desktopansicht in Brave geprüft: keine obere Navigation, keine Kauf-/Login-Elemente, vier Werkzeuge. Farben aus den `--dt-*`-Tokens der Dreamtelligence-Website (`app/globals.css`): Weiß `#ffffff`, Lavendel `#f6f1fc`, Text `#1c1629`, Violett `#311081`, Akzente `#96b1ff` / `#fadcec`.
- Gitleaks für Arbeitsverzeichnis und Git-Historie: jeweils ein bereits vorhandener Supabase-JWT-Fund. Dessen Rolle ist `anon`; es handelt sich nicht um einen Modal-Token oder Service-Role-Schlüssel. Keine Modal-Zugangsdaten gefunden. Dies ersetzt keinen Supabase-RLS-Audit.

Rohbelege und Deployment-Logs: `/tmp/xo-private-mode-20261118/`. Temporäre Dateien sind kein dauerhaftes Archiv.

Diese Prüfung ist kein vollständiger Sicherheitsaudit. Keine Änderung an Workspace-Mitgliedschaften, fremden Apps, Stripe-Konten oder Abonnements. Die Audioverarbeitung wurde zuvor separat mit echten Kurzaufträgen geprüft; Zugriffstests nach der Absicherung werden getrennt ausgewiesen.
