# Artist Workspace · technische Abnahme

Implementierungszweig `artist-workspace` im vorhandenen Arbeitsbaum. Gegenstand dieses Berichts sind echte lokale Audio-Render, begrenzte private Modelltests und reproduzierbare Prüfschritte. Die Vorläuferstände sind im [privaten Betrieb](../PRIVATE_MODE.md) und im [ursprünglichen Modal-Audit](2026-11-18-modal-audit.md) dokumentiert.

## Nachweise

- [Projektstart in Brave](artist-workspace/start-desktop.png), [Werkzeuge und Export auf dem Desktop](artist-workspace/workspace-desktop.png), [Inspektor bei 390 px](artist-workspace/workspace-mobile.png)
- [Beispiel-DAW-ZIP aus dem Browser](artist-workspace/beispiel-loop.zip) mit einem synthetischen Zwei-Sekunden-Ausschnitt als Stereo-WAV und gemessenen Exportwerten. Seine Quelle wurde für diese Abnahme erzeugt.
- `npm run build`: TypeScript und Vite bauen produktiv. `npm test` prüft mit 20 automatisierten Tests lokale Sicherheitsgrenzen, Audio, Projektpersistenz und die Modal-Vertragslogik mit isoliertem Speichermodell.
- Brave mit echter lokaler API, Dateiauswahl, Audioanalyse, hörbarem Transportpfad, Loop-Schnitt, ZIP-Download und Reload geprüft. Desktop 1440 × 900 und mobile Breite 390 × 844 ohne horizontale Dokumentüberbreite. In Safari 26.6.2 Testprojekt geöffnet und erzeugten Take mit laufender Transportzeit abgespielt. Die native WebDriver-Freigabe blieb ausgeschaltet.
- macOS Apple Silicon, Mac16,10 mit 16 GiB RAM. Für Musik dient ein eigens erzeugtes 12-s-Stereo-Signal mit Transienten und 123 BPM. Die synthetische Sprachprobe enthält zusätzlich deterministisches rosa Rauschen. Es wurde kein Musikmaterial aus dem Benutzerkonto hochgeladen.

## Korrektur der Aufgabenanzeige

Der frühere Abnahmekatalog enthält fehlgeschlagene Versuche. Bei identischem Audiomaterial erklärt der Workspace, welche Referenz benötigt wird. Historische Python-/NumPy-Diagnosen erscheinen als verständliche Aufgabenmeldungen. Brave hat die Anzeige anhand des ursprünglichen Abnahmekatalogs geprüft. Basic Pitch hat im erneuten lokalen Test eine MIDI-Datei mit 123 BPM erzeugt. Der bereits erfolgreich wieder übernommene MuScriptor-Auftrag enthält sieben MIDI-Dateien. Die aktuelle Testsuite besteht aus 22 Tests.

## Privater Modell- und DSP-Pfad

| Engine | Technischer Nachweis |
| --- | --- |
| SCNet XL IHF | Echte kohärente Modellauswahl mit vier Stereo-Stems bei je 529.200 Samples und 44,1 kHz. Hybridmodus bleibt für Einzel-Vocals und Instrumental verfügbar. Die Gruppenausgabe hat keine nachgewiesene samplegenaue Rekonstruktionssumme. |
| Automatik | Privater CPU-Auftrag mit geschütztem Staging, gespeicherter Call-ID, WAV-Download und anschließender lokaler Lautheitsmessung. |
| MuScriptor / Beat This / Essentia | Privater 12-s-Job, danach lokale Wiederübernahme derselben Remote-ID. Sieben MIDI-Dateien einschließlich variabler Tempo-Map und Clicktrack bei erkanntem 125 BPM. Weitere Dateien für Akkorde, Grid und Zusammenfassung. |
| MossFormer / Whisper / AST | Private Sprachvariante und separate JSON-Schnittvorschläge aus einem 6,775-s-Testclip. Ein zweiter Lauf hat AST zusätzlich ausgeführt. Vorschläge bleiben bis zur Auswahl und zum Schnitt im Quellmaterial unverbindlich. |
| Stable Audio Open 1.0 | Echter 2-s-Stereo-Take mit Seed 1234 und 88.200 Samples bei 44,1 kHz. Zusätzlich zwei 1,5-s-Ergebnisse in einem Batch mit Seeds 570 und 571. |
| librosa / FFmpeg | Echte Onset-/Grid-Ausgabe, zwei geschnittene One-Shots mit 18.230 bzw. 18.050 Samples und kompakter Browser-Loop. |
| Rubber Band 4.0.0 | Vier SCNet-Stems gemeinsam in einem Offline-Pass von 123 auf 128 BPM, +2 Halbtöne, je 553.500 Stereo-Samples bei 48 kHz. |
| Basic Pitch | Lokale ONNX-Inferenz mit exportiertem MIDI bei 123 BPM. Der Fehler bei NumPy-Skalaren im MIDI-Adapter wurde korrigiert und die bestehende Cloud-MIDI-Ausgabe ohne neues Modellrender wieder übernommen. |
| Pedalboard | Echte Gain-/Bypass-Kette in Float32 getestet. Die Messung bestätigt −6 dB, die Reihenfolge bleibt im Snapshot gespeichert. |
| Matchering | Echte Verarbeitung mit einer eigens anders entzerrten Referenz bei gemessenen −9,57 LUFS und −2,36 dBTP vor DAW-Export. Identischer Mix und Referenz werden abgewiesen. |
| DeepFilterNet / RNNoise | Aus demselben 48-kHz-Monoclip je 325.218 Ausgangssamples mit angepasster Padding- und Delay-Behandlung. |
| AudioSR Basic | Privater 2-s-Render einer bandbegrenzten Probe, neue Variante in Mono bei 48 kHz, Seed 42. Gewichtssicherung im separaten Image und korrigierter Nyquist-Sonderfall. Rund 57 s einschließlich Queue, Kaltstart und lokaler Übernahme. |

Queue-integrierte Wandzeit auf dem Mac lag im Beispiel bei 4,8 s für vier Stretch-Ergebnisse und 5,7 s bis zu den zwei One-Shots. Die private Separation brauchte rund 53 s vom Einreihen bis zur lokalen Übernahme. Die Wartezeiten der gemeinsam eingereihten Kurzjobs enthalten Queuezeit. Produktionslast, Audioqualität im Blindvergleich und Einzelkosten der Läufe sind nicht vermessen.

Für den ausgerichteten DAW-Export wurden vier Stereo-WAVs mit jeweils 553.500 Samples, 48 kHz und 24 Bit sowie ein MIDI mit 128 BPM aus demselben Stretch-Run verifiziert. Ein einzelner gestarteter GPU-Auftrag mit bestätigter Call-ID wurde gezielt beendet. Die anderen Aufträge derselben Anwendung blieben ausführbar. Die Prüfwerte stehen im [Nachweis](artist-workspace/aligned-summary.json).

## Umsetzungspakete

| Paket | Stand | Beleg und offene Abnahme |
| --- | --- | --- |
| P0 | technisch geprüft | Dirty-Basis auf Arbeitszweig erhalten, Versionsinventar und Schutztests. |
| P1 | technisch geprüft | React/FastAPI/SQLite, Import, Reload, Neustart, Hash, Range und sichere Projektgrenzen. |
| P2 | technisch geprüft, Betriebsrest offen | Fünf private Dienste mit hashgeprüftem 4-MiB-Staging, Claim-/Call-ID-Belegen, Recovery und Cancel ausgerollt. Die jobspezifische Staging-Kopie wird nach lokalem Ergebnis-Commit zur Freigabe gemeldet. Aufbewahrung der wiederverwendbaren Uploadteile und Ausgabedaten hat noch keine automatische Frist. Bestehende Modellgrenzen bleiben bei 50/100 MiB für konvertiertes Audio. |
| P3 | technisch geprüft | Gemeinsame Bibliothek, Inspektor, Transport und Aufgaben, echte Modellresultate aus der Projekt-API. |
| P4 | teilweise geprüft | Revisionsentwurf, Schritt-Snapshots, Asset-Herkunft, lokale Cache-Wiederverwendung und Undo. Eine geprüfte, editierbare Folge mit bis zu acht verknüpften Schritten löst ihre nachfolgenden Eingaben über unveränderliche Asset-IDs auf. |
| P5 | technisch geprüft, Hörabnahme offen | FFmpeg-QA, librosa-Grid/Onsets, editierbare Ausschnitte, mehrere kurze Exporte. |
| P6 | technisch geprüft, Hörabnahme offen | Offline-Gruppenrender und Audio/MIDI-Längenprüfung. Phasenlage an musikalischen Transienten ist noch nicht klanglich abgenommen. |
| P7 | technisch geprüft, DAW offen | Standard-MIDI-Ereignisse, Basic Pitch und MuScriptor, visueller Editor und synthetische Hörprobe. RPN-Rundreise mit komplexen Controller-Verläufen und DAW-Import offen. |
| P8 | technisch geprüft, Hörabnahme offen | Pedalboard-Kette, lokale Vorschau, Stereo-Bounce, Offset und Pegeltests. Längere DSP-Tail- und Hörreihen offen. |
| P9 | technisch geprüft | Beide Mastering-Pfade sowie erneute Messung der encodierten Datei im Export. Level-Matching steht nach Messung beider Eingänge zur Verfügung. |
| P10 | technisch geprüft, Hörabnahme offen | Drei Sprachfilter, separate Whisper-/Pausen-Vorschläge und EDL mit Quell-/Ergebnisabbildung. Kurzer deutscher synthetischer Clip technisch geprüft. |
| P11 | technisch geprüft, Hörmatrix offen | Stable Audio mit echten Einzel- und Batch-Takes. Separater AudioSR-Basic-Kurzlauf mit Originalerhalt geprüft. |
| P12 | technisch geprüft, DAW offen | ZIP, 24-Bit-WAV, MIDI und geprüfte Projektwiederherstellung. Fehlende Stems bzw. MuScriptor-Aufgaben lassen sich gezielt erneut starten. Native Ableton-/Logic-Abnahme offen. |
| P13 | offen | Vollabnahme mit realer Hörsitzung, DAW, großen Dateien und kompletter Recovery-/Retention-Matrix. |

## Abnahmematrix

| Test | Status |
| --- | --- |
| T01–T05 | Automatisiert geprüft. Zusätzlich sechs private Live-Capability-Routen anonym mit 401 und eingeloggte Proxy-Anfragen ohne Browser-Token. |
| T06–T07 | Vier echte Stems vorhanden. Exklusive Endindizes, WAV-Schnitte und Sample-Grenzen automatisiert. Klangliche Grenzabnahme offen. |
| T08–T09 | Stereo und Gruppenlänge, echtes 123/128-BPM-MIDI, 6/8 und Offline-Zeitmapping geprüft. Phasen-Hörtest und vollständige MIDI-Kompatibilitätsmatrix offen. |
| T10–T11 | Gain/Bypass, Float32-Ausgabe und gemeinsamer Bounce mit Clip-Offset geprüft. Alle Tail-/Preroll-Kombinationen noch offen. |
| T12–T13 | Echter Auto- und Referenz-Render sowie abschließende FFmpeg-QA im PCM-Export. Vollständige Fixture-Matrix für Intersample-Clipping und Stille offen. |
| T14 | Drei Filter und Schnittzeitmapping geprüft. Hörabnahme Sprache deutsch/englisch mit mehreren Störarten offen. |
| T15 | Echter Take, dauerhafter Seed und Projektmaterial. Batch-Auslösung hat serverseitige Obergrenzen. Zwei echte Takes nacheinander erzeugt und lokal gespeichert. |
| T16 | Echter AudioSR-Basic-Render auf bandbegrenzter Probe. Vergleichsreihe mit MP3, Rauschen und Hall offen. |
| T17–T19 | Lokale Auftrags-Idempotenz, Restart, Cache, Remote-Claim und ACK-Verlust mit isoliertem Modal-Speicher. Gleiche Live-Remote-ID bei Wiederübernahme real geprüft. Remote-Cancel zusätzlich im Live-Kurzlauf. Parallel-Race unter realer Last offen. |
| T20 | Manifest, Prüfung auf Pfadtraversal bei ZIP-Import, Projekt-Restore und Stereo-WAV/MIDI-Ausgabe technisch geprüft. Ableton Live und Logic Pro sind auf dem Test-Mac nicht installiert. |
| T21 | Speichergrenzen, sichere Hörkopienbereinigung, begrenzte Wiederaufnahme und privater Cloud-Pfad im Code. Grenzlast, Mac-Sleep und automatische Cloud-Retention offen. |
| T22–T23 | Brave- und Safari-Checks, zentraler Transport bei 390 und 1440 px, Formlabels und deaktivierte Commerce-Routen. Vollständiger 200%-Zoom- und Tastatur-Audit offen. |
| T24 | Statische Builds, lokaler Lockfile-Pfad und private Image-Updates geprüft. Der Bestand enthält ältere Modal-Images mit offenen transitiven Paketständen. npm audit meldet einen Advisory in der Vite-Entwicklerkette über picomatch. Der Scan der Produktionsabhängigkeiten meldet keine Funde. |

## Versionen und Rechte

| Artefakt | Version / Quelle / Einordnung |
| --- | --- |
| Lokale Python-Pakete | Vollständig versioniert in [requirements-workspace.lock](../../requirements-workspace.lock), Python 3.11.16. |
| Basic Pitch | 0.4.0, ONNX-Modell `nmp.onnx`, SHA256 `2c3c1d144bfa61ad236e92e169c13535c880469a12a047d4e73451f2c059a0ec`. [Spotify](https://github.com/spotify/basic-pitch). |
| FFmpeg / Rubber Band | Homebrew FFmpeg 9.0.1 mit GPL-Build und libmp3lame. Rubber Band 4.0.0. [FFmpeg-Lizenz](https://ffmpeg.org/legal.html), [Rubber Band](https://breakfastquay.com/rubberband/). |
| librosa, Pedalboard, Matchering | 0.11.0, 0.9.17 und 2.0.6. Vertriebsbedingungen für GPL-Komponenten separat prüfen. [librosa](https://github.com/librosa/librosa), [Pedalboard](https://github.com/spotify/pedalboard), [Matchering](https://github.com/sergree/matchering). |
| DeepFilterNet | Gepinnter ARM64-Build v0.5.6 mit eingebautem Modell. Hash und Bezugsweg stehen im Setup-Skript. [Release](https://github.com/Rikorose/DeepFilterNet/releases/tag/v0.5.6), [Kontext zu Code und Gewichten](https://github.com/Rikorose/DeepFilterNet/commit/7b14b89). |
| RNNoise | Source-Commit `70f1d25`, Modellarchiv `0a8755f8…e8b37`; beide Downloads werden checksum-geprüft. [Xiph](https://github.com/xiph/rnnoise). |
| Vorhandene Modal-Modelle | Bestehende Gewichte und Anbieterbedingungen, im Programm für Veröffentlichungsprojekte gesperrt. ZFTurbo-Checkpoints sind im Modul mit SHA gepinnt. MuScriptor large unter CC BY-NC mit Zusatzbedingungen. Stable Audio unter eigener Community-Lizenz. [MuScriptor](https://huggingface.co/MuScriptor/muscriptor-large), [Stable Audio](https://huggingface.co/stabilityai/stable-audio-open-1.0/blob/main/LICENSE.md). |
| AudioSR Basic | audiosr 0.0.7, HF-Revision `74a47f49061a1e788e968cc43ad45c0b6243f37d`, SHA256 `8a3506b9619ed32435ce2c115604750c7bddb5ad8502be7b1a3131bde878aa01`. [AudioSR](https://pypi.org/project/audiosr/0.0.7/), [Basic-Gewichte](https://huggingface.co/haoheliu/audiosr_basic). |

Dies dokumentiert den privaten Testbetrieb. Für Veröffentlichung oder Weiterverteilung sind die konkreten Paket-, Build- und Gewichtsbedingungen je Einsatz zu prüfen.
