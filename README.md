# Dreamtelligence Artist Workspace

Privater Audio-Arbeitsplatz für Mac und DAW. Importiere Material einmal, bearbeite Stems, Loops, Samples, Sprache und MIDI im selben Projekt und exportiere WAV/MIDI-Pakete für Ableton Live oder Logic Pro.

Der geschützte [Online-Workspace](https://studio.dreamtelligence.de/) ist im Browser erreichbar.

## Lokal starten

```sh
npm run setup
npm start
```

Öffne [den Workspace](http://localhost:8765). Wenn die geschützte Altansicht dort bereits läuft, nutze `npm start -- --port 8767`. Du brauchst Node.js 22, FFmpeg mit Opus, Rubber Band und uv.

- [Installation, Werkzeuge und Projektsicherung](docs/ARTIST_WORKSPACE.md)
- [Eigene private Modal-Konfiguration](docs/PRIVATE_MODE.md)
- [Geschützten Online-Workspace betreiben](docs/verification/2026-11-18-artist-workspace-online.md)
- [Prüfungen und aktuelle Abnahmegrenzen](docs/verification/2026-11-18-artist-workspace.md)
- [Gesamtplan](docs/plans/2026-11-18-artist-workspace-plan.md)

`npm test` führt die lokalen Sicherheits-, Transfer- und Audiotests aus. Echte Modellläufe sind separat und starten bewusst über den Arbeitsbereich. Die bisherige geschützte Werkzeugansicht startet mit `npm run legacy`. Früherer Marketing- und Zahlungscode liegt unter [disabled](disabled/README.md).
