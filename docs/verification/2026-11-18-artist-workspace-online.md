# Artist Workspace online

Der vollständige Workspace ist unter [studio.dreamtelligence.de](https://studio.dreamtelligence.de/) erreichbar. Die Oberfläche, Uploads, Projekte, Audiofenster und Exporte kommen von derselben Adresse. Die Live-Effektvorschau nutzt nach der Anmeldung einen separaten, autorisierten Audiokanal zu Modal. Der Online-Katalog gehört zum separaten Volume `dreamtelligence-artist-workspace-online-v1` auf Modal. Die erste Abnahme verwendete synthetisches Audio.

Der Browser meldet sich mit Benutzer `studio` und einem generierten Passwort an. Das Passwort liegt in einem Modal-Secret und in der privaten Zugangsdatei `~/.config/dreamtelligence-xo/artist-workspace-online-login.txt` mit Dateirechten `600`. Auch Lesezugriffe und direkte Asset-URLs benötigen die Anmeldung. Mutationen benötigen zusätzlich den Sitzungsschlüssel und eine passende Herkunft. Der Zugang ist ein gemeinsamer Workspace-Zugang.

## Betrieb

- Der Cloudflare-Eintrag `studio` zeigt im Modus DNS Only auf Vercel. Das Projekt `dreamtelligence-artist-workspace` leitet ausschließlich diese Studio-Domain an die Modal-App weiter. [Routing-Beispiel](../../hosting/artist-workspace/vercel.example.json)
- [modal_artist_workspace.py](../../modal_artist_workspace.py) bündelt den bestehenden Vite-Build und die FastAPI-Anwendung. Das Web-Frontend verwendet denselben Projekt-, Export- und Aufgabenvertrag wie die lokale Installation.
- Ein CPU-Container verarbeitet die Anfragen parallel und hält die lokale SQLite-Arbeitskopie. Der Container sichert konsistente SQLite-Snapshots und die Audio-Assets auf ein Modal Volume. Die Cloud-Startmarke und Remote-ID werden vor dem Weiterarbeiten gesichert. Vor dem Bestätigen von Cloud-Ergebnissen wird der Katalog gesichert. [Modal Volumes und Konsistenz](https://modal.com/docs/guide/volumes#filesystem-consistency)
- Der Web-Container skaliert im Leerlauf auf null. Die sechs vorhandenen Modal-Worker verarbeiten die KI-Aufträge über die bestehende serverseitige Proxy-Authentifizierung. CPU-, GPU- und Speicherverbrauch hängen von der tatsächlichen Nutzung ab. [Modal-Abrechnung](https://modal.com/pricing)
- Die Linux-Versionen von DeepFilterNet, RNNoise und den drei VST3 werden mit Prüfsummen eingebaut. Basic Pitch verwendet im Linux-Container das vorhandene ONNX-Modell. Die Effektkette unterstützt Live-Vorschau und WAV-Render.
- Die Studio-Domain gibt Live-Tickets für bereits gespeicherte Audio-Assets aus. Die direkte WebSocket-Verbindung zu Modal prüft die Herkunft und löst das Ticket einmalig ein. Pro Verbindung verarbeitet ein isolierter Prozess die Quelle mit denselben Effekten und Parametergrenzen wie beim WAV-Render. [Modal WebSocket-Unterstützung](https://modal.com/docs/guide/webhooks#websockets)
- Beim normalen Abspielen lädt der Browser das nächste Hörfenster bis zu fünf Sekunden vor dem Übergang. Opus reduziert die Übertragungsmenge, kompatible Browser können weiterhin WAV-Fenster verwenden. Beim Loopen hilft der 32-MiB-Cache für bereits dekodierte Ausschnitte.

## Abnahme

| Pfad | Ergebnis |
| --- | --- |
| Zugriff | Anonyme Anfragen an Oberfläche, Assets und API erhalten HTTP 401. Fremde Origins und Mutationen ohne Sitzungsschlüssel werden abgewiesen. |
| Browser | Brave und WebKit haben Login, Audioimport, Linux-VST3-Render, A/B-Wiedergabe, ZIP-Download sowie eine Ansicht bei 390 px geprüft. |
| Upload | WAV mit 8.064.044 Bytes angenommen. Autorisierter HTTP-Range-Download lieferte HTTP 206. |
| Studio-Domain | HTTPS, Basic-Login, Herkunftsprüfung, Sitzungsschlüssel, Range 206 und 13.824.044 Byte Upload geprüft. Brave und WebKit öffneten die Anwendung und das Handbuch auch bei 320 px über die normale DNS-Auflösung. |
| CPU-Werkzeuge | QA, Grid und Tonart, Loops und One-Shots, Rubber Band, Matchering, Basic Pitch, MIDI-Edit, Mix, DeepFilterNet, RNNoise, Sprachschnitt und Export erzeugten Dateien. |
| VST3 | CHOW Tape 2.11.4, CHOW Matrix 1.3.0 und Dragonfly Plate 3.2.10 lieferten WAV-Vorschauen und Effektsignale im Live-Stream. |
| Echtzeit | Brave und WebKit prüften denselben Online-Transport, Regler und A/B. Brave bestätigte die geänderten PCM-Blöcke ohne Renderauftrag und ein verfügbares Layout bei 390 px. Im selben Stream war Plate bei Mix 0 samplegleich zur Quelle. Ein gespeicherter M4A-Ausschnitt startete bei 1:02 innerhalb der Auswahl 1:00–1:04. WAV-Speichern mit einer Sekunde Ausklang und Download geprüft. |
| KI-Werkzeuge | Stem-Trennung, Mastering, MossFormer, MuScriptor, Text zu Audio und AudioSR lieferten Ergebnisse. MuScriptor erkannte beim ersten Clip Drums, Akkorde und Beat. Die zweite Probe lieferte zusätzlich Melodie und insgesamt sieben MIDI-Dateien. |
| Export | Das ZIP enthielt WAV, MIDI und Manifest. Der native Import in Ableton und Logic ist weiterhin offen. |
| Neustart | Nach Containerwechsel waren vier Testprojekte und 27 Aufgabenstände vorhanden. Die heruntergeladene Testquelle hatte dieselbe SHA-256. Die erste Anfrage brauchte in diesem Test 4,89 Sekunden. |
| Browser-Puffer | Ein 4-Sekunden-Loop spielte über zwei Wiederholungen mit genau einer HTTP-Anfrage für das PCM-Hörfenster. |
| Regression | 28 lokale Tests bestanden. Der Live-Test prüft Parameterwechsel, Loop, Herkunft und einmalige Ticketnutzung. |

### Wiedergabe und Live-Effekte

Im Online-Test mit Love Dose gab es in Brave über zwei Fensterwechsel keine messbare Unterbrechung. Vor dem Update war beim Fensterwechsel eine Lücke von 1,85 Sekunden gemessen worden. Ein künstlich um 1,4 Sekunden verzögertes Hörfenster lief ebenfalls durch.

Der Live-Stream sendet kleine Blöcke für Quelle und Effekt gebündelt und komprimiert. Die App puffert online 2,65 Sekunden und baut nach einem längeren Aussetzer bei Bedarf einen größeren Puffer auf. In Brave liefen zwei Live-Schleifen ohne messbare Unterbrechung, darunter ein Test mit einer künstlichen Netzwerkpause von 1,4 Sekunden. Der Pegelregler wirkte nach 2,67 Sekunden in Brave und nach 2,76 Sekunden in WebKit in der hörbaren Ausgabe. Die native DSP-Kette verarbeitet weiterhin jeden Effekt. Regleränderungen starten keinen neuen Renderauftrag. A/B schaltet auf die bereits vorliegenden Signale um.

Mit einem Love-Dose-Ausschnitt lieferten Pegel, Hochpass, Tiefpass, Peak-EQ, Kompressor, Gate, Limiter, Hall, Delay, CHOW Tape, CHOW Matrix und Dragonfly Plate jeweils ein verändertes Signal. Die Prüfung änderte für jedes Modul Parameter im selben Stream. Eine Kette aus vier Modulen reagierte ebenfalls.

### Abnahme mit einem vollständigen Track

Eine bereitgestellte 6:45 lange M4A mit knapp 15 MB wurde beim Entpacken zu 24-Bit-WAV rund 107 MB groß. Das bisherige Dienstlimit blockierte die Stem-Trennung vor dem Modellstart. Stem-Trennung, automatische Mastering-Kette und Musikanalyse akzeptieren für den privaten, blockweisen Workspace-Transfer bis zu 256 MiB pro Datei. Der Browser lädt weiterhin die Originaldatei hoch.

Der Test speicherte fünf getrennte Stereo-WAVs über die volle Tracklänge und prüfte ihre Abrufbarkeit über die Studio-Domain. Das Grid schlug 123,05 BPM und B♭-Moll vor. Die Tonart wurde um zwei Halbtöne verschoben und das Tempo blieb dabei erhalten. Basic Pitch erzeugte aus der Bassspur MIDI. Die Browserprobe deckte Auswahlwiedergabe, Solo, Loop und den A/B-Vergleich einer Effektvorschau ab.

MuScriptor speicherte für den vollständigen Track 15 Dateien, darunter Instrumenten-MIDI, Drum-MIDI, Akkorde und Tempokarte. Die Musikanalyse schlug 125 BPM und C-Dur vor. Der Vergleich zeigt, dass Tempo und Tonart je nach Analyse unterschiedlich geschätzt werden können.

Das Testprojekt deckt alle 19 Werkzeuge mit 26 abgeschlossenen Prüfaufträgen und 45 Ergebnisdateien ab. Das Referenzmastering verwendete einen separat bearbeiteten Abschnitt als Testreferenz. Text zu Audio lief mit einem eigenen Prompt. Das DAW-Paket enthielt WAV, MIDI und Manifest. Beim Rückimport des Projektpakets entsprach die Prüfsumme der Originaldatei der importierten M4A. Der native DAW-Import bleibt separat zu prüfen.

## Neue Version ausrollen

Ein eigenes Deployment benötigt zwei Modal-Secrets. In `artist-workspace-online-auth` liegen `XO_WEB_ORIGIN` für den direkten HTTPS-Ursprung und `XO_MODEL_WORKER_CONFIG` für die private Worker-Konfiguration. Das Secret `artist-workspace-online-password` enthält `XO_STUDIO_PASSWORD`. Die Worker brauchen eigene Proxy-Zugangsdaten. GitHub Actions baut und testet den Workspace, ohne Cloud-Zugangsdaten zu verwenden.

Vor einer neuen Version laufende Aufgaben im Online-Katalog prüfen und auslaufen lassen. Der Katalog hat einen schreibenden Container. Die Deployment-Strategie `recreate` terminiert alte Container beim Versionswechsel. Das Volume bleibt bestehen.

```sh
npm run build
modal deploy --env main --strategy recreate modal_artist_workspace.py
```

Nach dem Start Anmeldung und einen bestehenden Katalogeintrag prüfen. Für einen zweiten unabhängigen Workspace ein separates Volume und einen eigenen Zugang verwenden.

Änderungen am Studio-Routing separat aus `hosting/artist-workspace` im Vercel-Projekt `dreamtelligence-artist-workspace` ausrollen. Dessen Ausgabeverzeichnis ist `public`. Verwende `vercel.example.json` als Vorlage für die lokale `vercel.json` und trage die eigene Domain und den eigenen Modal-Ursprung ein.
