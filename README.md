# Dreamtelligence Artist Workspace

Der Artist Workspace ist ein privates Audiostudio im Browser. Du kannst einen Track in Stems zerlegen, aus der Schlagzeugspur einen Loop schneiden, die Basslinie in MIDI umwandeln und beides in Ableton Live oder Logic Pro weiterbearbeiten. Originale, Referenzen und bearbeitete Varianten bleiben im selben Projekt.

[Geschütztes Online-Studio öffnen](https://studio.dreamtelligence.de/) · [Beispiel für einen DAW-Export herunterladen](docs/verification/artist-workspace/beispiel-loop.zip)

![Studio mit Bibliothek links, Audio-Wellenform in der Mitte und Effekt-Rack rechts](docs/verification/artist-workspace/studio-overview.png)

*Lokale Studio-Ansicht mit synthetischem Demomaterial.*

## Vom Import bis zur DAW

1. **Material importieren.** Lade einen Track oder einzelne Aufnahmen hoch. Eine Vorlage wie **Remix & Samples** legt passende Bearbeitungsschritte im Projekt an.
2. **Clip bearbeiten.** Wähle das Werkzeug im Inspektor. Markiere in der Wellenform einen Ausschnitt oder arbeite mit dem ganzen Clip. Fertige Ergebnisse findest du unter **Aufgaben** und in der Bibliothek.
3. **Varianten vergleichen.** Höre Quelle und bearbeitete Fassung im A/B-Vergleich. Im Effekt-Rack kannst du Filter, EQ, Kompressor, Band, Delay und Hall während der Vorschau einstellen und die gewählte Fassung als WAV speichern.
4. **In der DAW weiterarbeiten.** Lege die gewünschten Ergebnisse in den **Exportkorb** und erstelle ein DAW-Paket. Das ZIP enthält die ausgewählten WAV- und MIDI-Dateien mit einem Manifest. Auf Wunsch richtet der Export die Audiotracks anhand ihrer Startpositionen im Projekt aus.

Das **Handbuch** auf der Startseite und im Studio erklärt alle 19 Werkzeuge und die 12 Effektmodule. Dazu gehören Tempo- und Tonartbearbeitung, Referenzmastering, Sprachbearbeitung und kurze Sounds aus Text. Über **Projektpaket sichern** lässt sich ein Projekt mit seinen Dateien sichern und später wieder öffnen.

## Lokal auf dem Mac starten

Voraussetzungen sind Node.js 22 mit npm sowie `uv`, FFmpeg mit Opus-Unterstützung und Rubber Band. Das Setup richtet die Python-3.11-Umgebung ein und installiert die festgeschriebenen Abhängigkeiten.

```sh
brew install uv ffmpeg rubberband
git clone https://github.com/dreamtelligence/XO-master.git
cd XO-master
npm run setup
npm start
```

Öffne [localhost:8765](http://localhost:8765). Falls der Port belegt ist, starte das Studio mit `npm start -- --port 8767`. Lokale Verarbeitung und Export funktionieren ohne Online-Konto. Für Cloud-Werkzeuge brauchst du [eigene private Modal-Zugangsdaten](docs/PRIVATE_MODE.md).

## Technik und Prüfstand

React und Vite bilden die Oberfläche. FastAPI verwaltet Projekte und Aufträge. Lokal speichert die App den Katalog in SQLite und die Audiodateien im Projekt-Datenverzeichnis. Die geschützte Online-Instanz speichert beides auf einem eigenen Modal Volume und führt Modellaufträge über private Modal-Worker aus.

Der [Online-Prüfbericht](docs/verification/2026-11-18-artist-workspace-online.md) dokumentiert einen vollständigen Track vom Import über Stem-Trennung und MIDI bis zum ZIP-Export. Die Dateien und der Rückimport des Projektpakets wurden geprüft. Die Abnahme des Imports direkt in Ableton Live und Logic Pro steht noch aus.

- [Installation, Werkzeuge und Projektsicherung](docs/ARTIST_WORKSPACE.md)
- [Lokale Audio- und Modellprüfungen](docs/verification/2026-11-18-artist-workspace.md)
- `npm test` führt die lokalen Regressionsprüfungen aus.

Der Projektcode steht unter der [MIT-Lizenz](LICENSE). Für eingebundene Modelle und Plugins gelten deren [jeweilige Lizenzbedingungen](docs/verification/2026-11-18-artist-workspace.md#versionen-und-rechte).
