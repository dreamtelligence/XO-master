# Dreamtelligence Artist Workspace

Ein privates Audiostudio im Browser für **Stem Separation, Audio-to-MIDI, Sampling, Live-Effekte und Mastering**. Bearbeite Tracks und Aufnahmen und exportiere deine Ergebnisse als WAV und MIDI für Ableton Live oder Logic Pro.

[Geschütztes Online-Studio öffnen](https://studio.dreamtelligence.de/) · [Beispiel für einen DAW-Export herunterladen](docs/verification/artist-workspace/beispiel-loop.zip)

## Funktionen

| Bereich | Was du im Studio machen kannst |
| --- | --- |
| **Stem Separation** | Einen Track in **Vocals, Drums, Bass und Begleitung** zerlegen oder eine **Instrumentalversion** ohne Gesang erzeugen. Die ausgewählten Spuren landen als einzelne WAV-Dateien im Projekt. |
| **Audio-to-MIDI** | Mit Basic Pitch Noten und Pitch Bends aus einer Einzelspur wie Bass oder Gitarre erkennen. MuScriptor liefert aus einem Song je nach Auswahl Instrumenten- und Drum-MIDI, Akkorde und eine Tempokarte. Noten im MIDI-Editor anpassen, quantisieren und transponieren. |
| **Loops, Samples und Tonart** | Vorschläge für Tempo, Taktraster, Tonart und Anschläge übernehmen oder korrigieren. Ganze Takte oder freie Ausschnitte als Loops speichern und mehrere One-Shots in einem Durchgang schneiden. Tempo und Tonhöhe mit Rubber Band unabhängig ändern. |
| **Live-Effekte und Remix-Mixer** | Effekte in einer Kette anordnen, bis zu 30 Sekunden live bearbeiten und Quelle und Effektsignal im A/B-Vergleich hören. Ausschnitte mit Ausklang oder ganze Clips als WAV rendern. Stems mit Pegel, Panorama, Schnitt und Startversatz als Stereomix ausgeben. |
| **Mastering und Audioprüfung** | Einen Mix automatisch mastern oder mit Matchering an eine Referenz anlehnen. Lautheit (LUFS), True Peak und stille Abschnitte prüfen. |
| **Sprachbearbeitung** | Hintergrundgeräusche mit MossFormer, DeepFilterNet oder RNNoise reduzieren. Pausen und Störstellen markieren und bestätigte Schnitte als neue Fassung rendern. |
| **Sound-Generierung und AudioSR** | Aus Text bis zu drei kurze Audio-Takes erzeugen. Mit AudioSR Basic experimentell hohe Frequenzen in einem Ausschnitt von bis zu 15 Sekunden ergänzen. |
| **DAW-Export und Projektsicherung** | Ausgewählte WAV- und MIDI-Dateien mit Manifest als ZIP exportieren. Audiotracks auf Wunsch nach ihrer Startposition ausrichten. Projektpakete mit Audiodateien sichern und wieder öffnen. |

### Stem Separation im Studio

Track importieren, in der **Bibliothek** auswählen und im **Inspektor → Werkzeug → Stems trennen** die gewünschten Spuren anhaken. **Mel-Band RoFormer** übernimmt Gesang und Instrumentalversion. **SCNet XL IHF** liefert die übrigen Stems und kann alle vier Stems als zusammengehörige Gruppe berechnen. Die WAVs erscheinen nach dem Lauf in der Bibliothek und unter **Aufgaben**.

### Live-Effekt-Rack

Zur Auswahl stehen **Gain, Hochpass, Tiefpass, parametrischer EQ, Kompressor, Noise Gate, Limiter, Hall, Delay, CHOW Tape, CHOW Matrix und Dragonfly Plate**. Im Studio erklärt das **Handbuch** alle 19 Werkzeuge und 12 Effektmodule.

![Studio mit Bibliothek links, Audio-Wellenform in der Mitte und Effekt-Rack rechts](docs/verification/artist-workspace/studio-overview.png)

*Lokale Studio-Ansicht mit synthetischem Demomaterial.*

## Beispiel vom Track bis zur DAW

1. Importiere einen Track und trenne Drums und Bass als eigene Stems.
2. Markiere zwei Takte der Drumspur und speichere sie als WAV-Loop. Wandle die Bassspur mit **Basic Pitch** in MIDI um.
3. Lege den Loop und das Bass-MIDI in den **Exportkorb** und erstelle ein DAW-Paket. Ziehe die Dateien aus dem ZIP in dein Arrangement.

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

Im Online-Test erzeugte die Stem Separation aus einem 6:45 Minuten langen Track fünf Stereo-WAVs über die volle Länge. Der Prüfbericht dokumentiert auch Audio-to-MIDI, den ZIP-Export und den Rückimport des Projektpakets. Die Abnahme des Imports direkt in Ableton Live und Logic Pro steht noch aus. [Online-Prüfbericht](docs/verification/2026-11-18-artist-workspace-online.md#abnahme-mit-einem-vollständigen-track)

- [Installation, Werkzeuge und Projektsicherung](docs/ARTIST_WORKSPACE.md)
- [Lokale Audio- und Modellprüfungen](docs/verification/2026-11-18-artist-workspace.md)
- `npm test` führt die lokalen Regressionsprüfungen aus.

Der Projektcode steht unter der [MIT-Lizenz](LICENSE). Für eingebundene Modelle und Plugins gelten deren [jeweilige Lizenzbedingungen](docs/verification/2026-11-18-artist-workspace.md#versionen-und-rechte).
