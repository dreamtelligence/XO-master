# Technische Planungsnotizen für den Artist Workspace

Stand: 18.11.2026. Ausschließlich Recherche und überprüfbare Anforderungen; keine Installation, Inferenz, App- oder Deploymentänderung.
Grundlage: aktueller Quellcode und [Kandidatenübersicht](2026-11-18-audio-chain-candidates.md). Die folgenden Abnahmewerte sind vorgeschlagene Anforderungen, keine bereits erreichten Messwerte.

## 1. Einheitliche Audio-Zeitbasis vor der Verkettung

Jedes Artefakt braucht Originalbezug, Sample-Rate, Kanalbelegung, Sample-Anzahl, Format und Start-/Endposition in Samples. Sekundenwerte sind abgeleitet. Originale bleiben unverändert.
Analyse darf mono sein; ein Analyse-Downmix darf das Stereo-Arbeitsartefakt nicht ersetzen. Enhancement lädt aktuell ausdrücklich mono; dieser Eingriff muss im neuen Ablauf sichtbar und wählbar werden.
Abnahme: Stereo-Impulsdatei mit verschiedenen linken/rechten Impulsen behält Kanalzuordnung und bekannte Startposition nach Decode/Export; Sample-Rate-Wechsel erzeugt eine dokumentierte Zeitabbildung und keinen verdeckten Versatz.
Abnahme: Bei unveränderter Rate und reinem Schnitt sind exportierte Positionen bis auf ein Sample reproduzierbar. Resampling wird anhand einer ausdrücklich festgelegten Toleranz geprüft, nicht als bitidentisch bezeichnet.
Codebezug: `modal_app_enhancement.py`, `enhance_audio_processing`; RNNoise-Formate siehe Abschnitt 9.

## 2. Rubber Band: Dauer, Stereo und Mehrspur-Kohärenz

Tempoänderung ist ein Render-Schritt. Für konstante BPM ist das gewünschte Dauerverhältnis `source_bpm / target_bpm`; Pitch-Faktor bei Halbtönen `2 ** (semitones / 12)`. Variable Beat-Grids brauchen eine gemeinsame Zeitabbildung.
Rubber Band kann je nach Transienten lokal unterschiedlich viele Samples liefern. Offline-Modus und gemeinsam verarbeitete Stereokanäle müssen bewusst konfiguriert werden; R3/Finer ist eine Qualitäts-/CPU-Option, keine Gratisgarantie.
Abnahme: Stereo-Render, inklusive identischer linker/rechter Kanäle, hat nach dokumentierter Latenz-/Längenkorrektur gleiche Kanalzeitbasis; kein Kanal wird separat getrimmt oder pegelnormalisiert.
Abnahme: Mehrere Stems eines Projekts erhalten dieselbe globale Zeitabbildung, Startreferenz und Exportlänge. Korrelierte Impulse an Anfang/Mitte/Ende werden vermessen; hörbare Phasenfehler dürfen nicht als „samplegenau“ freigegeben werden.
Quelle: [Rubber Band Integration](https://breakfastquay.com/rubberband/integration.html), insbesondere Ausgabevariabilität und `OptionChannelsTogether`.

## 3. BPM-Anzeige, Beat-Grid und MIDI-Tempo sind verschiedene Dinge

Direkter Befund: `create_click_track_midi(beats, downbeats, tempo, ...)` nutzt `tempo` nicht und konstruiert aktuell `PrettyMIDI()` ohne Anfangstempo. Ein Teststück bei 120 BPM verdeckt diesen Unterschied.
`tempo_map.txt` ist derzeit eine Textliste mit Sekundenpositionen und Anweisungen; sie ist keine standardisierte MIDI-Tempo-Map. Gleichmäßige Clicks in Sekunden sind noch keine korrekt gesetzten Takt-/Tempo-Events.
Abnahme: 90-, 123- und 150-BPM-Fixtures ergeben erwartete MIDI-Tempo-Events und Taktpositionen; 3/4 und 6/8 werden ausdrücklich geprüft. Halb-/Doppeltempo muss korrigierbar sein.
Abnahme: Ein beschleunigter 123-BPM-Loop und die zugehörigen MIDI-Noten laufen in derselben Zielzeitbasis; MIDI-Export enthält definierte Tempo-/Taktinformationen. Flexible Tempi werden entweder korrekt abgebildet oder klar als konstantes Tempo exportiert.
Quelle: [pretty_midi Container: Notenzeit in Sekunden, Takt-Events](https://craffel.github.io/pretty-midi/containers.html); lokaler Code `modal_app_transcription.py`, `create_click_track_midi`, `create_daw_tempo_map`.

## 4. Loop-/One-Shot-Schnitt benötigt Grenz- und Metadatenregeln

Onset- und Beat-Erkennung liefert Vorschläge. Jeder Schnitt muss eine vom Künstler korrigierbare Region besitzen; Fades, Vorlauf, Release-Ende und Snap sind eigene Parameter.
Originalzeit und regionslokale Zeit getrennt speichern. Noten vor dem Loopstart bzw. über dem Loopende brauchen eine dokumentierte Clip-/Überhangregel; nicht stillschweigend negative MIDI-Zeiten schreiben.
Abnahme: 1-/2-/4-/8-Takt-Exporte bei frei gewählter Startposition; leere, sehr kurze und überlappende Regionen erzeugen verständliche Validierung statt kaputter Dateien.
Abnahme: One-Shots bewahren Anschlag und gewählten Ausklang; künstliche Fades werden nicht ungefragt auf die erste Transiente gelegt. ZIP/Manifest gibt BPM, Takt, Tonartschätzung, Originaloffset und Sample-Rate an.
Quelle: [librosa Onset-Implementierung und Backtracking](https://github.com/librosa/librosa/blob/main/librosa/onset.py).

## 5. Pedalboard: Effektreihenfolge, Zustand und Ausklang

Eine Kette besitzt geordnete, versionierte Parameter und eine explizite Bypass-Position. Bei stückweiser Verarbeitung dürfen Delay-/Hallzustände nicht je Audioblock zurückgesetzt werden.
Der tatsächliche Export muss mit derselben Kette wie die freigegebene Vorschau gerendert werden. Pegelabgleich für das Abhören ist Monitor-Gain und verändert nicht unbemerkt das Export-Master.
Abnahme: Derselbe Clip als ein Buffer und in mehreren Buffern ist innerhalb festgelegter numerischer Toleranz gleich; keine zusätzlichen Klicks an Blockgrenzen. Ein Impuls mit Hall hat den vereinbarten Ausklang.
Abnahme: „Tail behalten“ versus „auf Projektlänge schneiden“ ist explizit. Ein verworfener Render darf den nächsten Auftrag nicht mit altem Effektzustand beeinflussen.
Quelle: [Pedalboard `process`/`reset` und gepufferte Ausgabe](https://spotify.github.io/pedalboard/reference/pedalboard.html).

## 6. Qualitätscheck misst Exportdateien, nicht nur In-Memory-Audio

Der bestehende Masteringpfad verwendet `pyloudnorm` und einen Pedalboard-Limiter. Ein Limiter-Schwellwert oder Sample-Peak allein belegt keinen True-Peak-Grenzwert.
Vorher-/Nachher-Bericht: LUFS, LRA, Sample-/True-Peak, Länge, Kanäle, Stille, nicht-finite Samples und Clipping. Bei Stille oder unzureichendem Material sind „nicht messbar“ und Grund gültige Zustände.
Abnahme: Testdatei mit Intersample-Peaks wird von True-Peak-Messung erkannt. Nach finalem Resampling/PCM- oder verlustbehaftetem Export erneut messen; gemessene Überschreitungen blockieren die betreffende zugesagte Exportkonformität.
Abnahme: Benutzerziel, tatsächlich gemessener Wert und Toleranz sind getrennte Felder. Kein universelles Streaming-Lautheitsversprechen und kein Musikqualitäts-Score aus RMS/SNR ableiten.
Quelle: [FFmpeg `loudnorm` und EBU-R128](https://ffmpeg.org/ffmpeg-filters.html#loudnorm), [True-Peak-Modus](https://ffmpeg.org/ffmpeg-filters.html#ebur128).

## 7. A/B muss denselben Inhalt vergleichen

Direkter Befund: Enhancement erzeugt aktuell einen Stereo-Preview mit Original links und Bearbeitung rechts, auf `min_length` abgeschnitten. Nach Stille-/Füllwortentfernung liegen unterschiedliche Inhalte auf denselben Sekundenpositionen.
Der neue Player benötigt getrennte Versionen mit gemeinsamer Transportzeit; bei zeitverändernden Schnitten entweder Edit-Decision-/Zeitmapping oder einen Vergleich in inhaltlich entsprechender Auswahl.
Abnahme: A/B springt bei einem reinen Klangfilter an dieselbe Inhaltsposition; bei Schnittoperationen wird die Zeitabbildung benutzt und der Modus sichtbar. Kein automatisches links/rechts-Splitten als gewöhnliches Stereo-Ergebnis.
Abnahme: Lautheitsabgleich ist umschaltbar und nachvollziehbar. Nur ein aktiver Transport spielt; Umschalten, Pause, Seek und Stop erzeugen keinen zweiten unkontrollierten Player.
Codebezug: `modal_app_enhancement.py`, `preview_audio = np.column_stack(...)`.

## 8. Browserdarstellung darf große Audiodateien nicht vollständig vervielfachen

WaveSurfer ist Darstellung/Player, kein Audio-Editor oder Render-Backend. Die offizielle Dokumentation warnt bei großen browserdecodierten Dateien vor Speicherproblemen und empfiehlt vorberechnete Peaks mit Dauer.
Serverseitige Waveform-Peaks plus gezielte Previewartefakte vorsehen; Original-/Masterdownloads bleiben separat. Seek/Range-Verhalten muss über lokale Proxyroute und Modal-Route gemeinsam funktionieren.
Abnahme: Ein mehrminütiges Stereo-Projekt mit vier Stems öffnet ohne vollständige Float32-Decodierung aller Quellen gleichzeitig. Ein 30-Sekunden-Bearbeitungsfenster lässt sich unabhängig vom Full-File-Download hören.
Abnahme: Range-Requests haben korrekte 206-/Content-Range- bzw. definierte 200-Fallback-Semantik; Chrome/Brave und Safari werden mit denselben Preview-Dateien geprüft.
Quelle: [WaveSurfer FAQ zu großen Dateien, Peaks und Streaming](https://wavesurfer.xyz/docs/).

## 9. Sprachmodelle und AudioSR bleiben materialabhängige Bearbeitungen

RNNoise-Demo arbeitet mit 48-kHz-Mono-Raw-PCM16, nicht mit WAV. Konvertierung muss Header/Bytes korrekt trennen und Ausgaberate/-kanäle nach dem Modell dokumentieren. DeepFilterNet ist eine Alternative, kein weiterer obligatorischer Filter hinter MossFormer.
AudioSR ergänzt Frequenzanteile generativ. Das Upstream-Training simulierte Lowpass-Verlust; unbekannte Cutoffmuster, MP3-Verlust und starke Störungen können ungeeignet sein. Keine automatische Musik-/Sprachumschaltung, die Originale überschreibt.
Abnahme: Eine einzige bewusst gewählte Rauschunterdrückung läuft; der Wechsel des Modells erzeugt eine neue Variante. Stille und Stereoquellen werden korrekt behandelt. AudioSR ist standardmäßig aus, mit Hörvorschau, Seed und Modellbezug.
Abnahme: Format-Fixture WAV→RNNoise-Raw→WAV hat erwartete Länge ohne Headerrauschen. AudioSR wird gegen Lowpass-, MP3- und verrauschte Fixtures verglichen; schlechte Ergebnisse sind keine erfolgreiche „Reparatur“.
Quellen: [RNNoise README](https://raw.githubusercontent.com/xiph/rnnoise/main/README), [AudioSR Grenzen](https://github.com/haoheliu/versatile_audio_super_resolution#understanding-the-impact-of-cutoff-patterns-on-audiosr-performance).

## 10. Stage-Reihenfolge und Ergebniszustände dürfen nicht verborgen sein

Stem-Separation, Speech-Cleanup, MIDI-Analyse und generative Erweiterung sind verschiedene Zweige. Mastering ist ein optionaler finaler Mix-Schritt; einzelne Stems nicht automatisch individuell pegelangleichen oder mastern.
TTA ist aktuell ein an das ZFTurbo-CLI weitergereichtes Flag. Laufzeit und Qualitätsgewinn sind hier nicht gemessen; einen verbindlichen Faktor „doppelt so lang“ oder garantierte Verbesserung nicht übernehmen.
Abnahme: Vorschau nennt Eingangsversion und geordnete Bearbeitungen; geänderte Vorstufe macht abhängige Ergebnisse sichtbar veraltet, ohne Originale zu löschen. Bestehende Stems werden für MIDI/Loops wiederverwendet.
Abnahme: Transkription mit `completed_tasks` plus `failed_tasks` ist teilweiser Erfolg; fehlende Drums dürfen nicht hinter einem einzigen grünen „fertig“ verschwinden. Retry betrifft nur den gewählten fehlgeschlagenen Zweig.
Codebezug: `modal_app_zfturbo_complete.py`, `run_zfturbo_inference`; `modal_app_transcription.py`, `final_status`.

## 11. Job-Start, Wiederaufnahme und Cancel brauchen dauerhafte Identitäten

Direkter Befund: Die aktuellen Handler speichern Geschäfts-`job_id`, verwerfen jedoch das von `.spawn()` zurückgegebene `FunctionCall`-Handle. Ohne dauerhaftes `function_call_id` ist ein gezieltes Cancel nicht zuverlässig abbildbar.
Persistentes Startledger vor dem Submit; Eingangs-Hashes, kanonische Parameter, explizite Seed-Werte und Modell-/Codeversionen gehören zur Reproduzierbarkeit. Idempotency-Key verhindert Doppelstart bei Doppelklick/Netzretry; „neue Variante“ erzeugt bewusst einen neuen Auftrag.
Abnahme: identischer Start zweimal führt zu einem Remote-Auftrag. HTTP-Timeout nach erfolgreichem Spawn löst keinen blinden zweiten Spawn aus; unsicherer Submit-Zustand wird zuerst abgeglichen. Neustart des lokalen Servers erkennt laufende Jobs wieder.
Abnahme: Geschützte Modal-ASGI-Cancelroute prüft eigene Job→Call-Zuordnung; sie nutzt serverseitig `FunctionCall.from_id(...).cancel(...)`. Der lokale Proxy-Token wird dafür nicht durch einen veröffentlichten Modal-API-Key ersetzt.
Abnahme: „Abbruch angefordert“ ist nicht sofort „abgebrochen“; Rennen mit erfolgreichem Ende sind definiert. Keine komplette App stoppen und keine fremden Container/Inputs abbrechen. Nach bestätigtem Abbruch starten keine abhängigen Stufen mehr.
Quelle: [Modal FunctionCall: `object_id`, `from_id`, `cancel`](https://modal.com/docs/reference/modal.FunctionCall). `terminate_containers=True` kann andere Inputs beeinflussen; im Plan nicht pauschal verwenden.

## 12. Versionen, Modellartefakte und Kosten sind Teil des Auftrags

Die vorhandenen Images enthalten teils offene `>=`-Abhängigkeiten. Bestehende Separation-Weights haben Hashes; dieses Prinzip auf neue Modelle, Sample-Bibliotheken und Runtime-Pakete ausdehnen. Code-Lizenz und Gewichte-Lizenz bleiben getrennte Felder.
Basic Pitch ist laut Upstream für einzelne Instrumente am stärksten; damit als auswählbarer MIDI-Weg nach Separation planen. Stable Audio Open hat bereits Dauer-/Step-Grenzen im Handler; zusätzliche Varianten vervielfachen Aufträge, nicht bloß UI-Karten.
Abnahme: Manifest je Export enthält Tool-/Paket-/Checkpoint-Versionen, Hashes, Seed, Parameter, Eingangsversion und gemessene Laufzeit. Unbekannte Lizenz oder fehlendes Modell führt zu „nicht verfügbar“ statt stillem Ersatz.
Abnahme: CPU-/GPU-Laufzeit, Kaltstart, Upload, Queue und Rendering getrennt messen; parallele Varianten haben definierte Grenzwerte. Ein Preview-Regler startet keinen vollständigen GPU-Job bei jeder Bewegung.
Quelle: [Basic Pitch: Ein-Instrument-Hinweis und Runtime-Varianten](https://github.com/spotify/basic-pitch); lokaler Code `modal_app_audio_generation.py`, `generate_audio`.

## Übergabehinweis

Keine dieser Prüfanforderungen wurde in dieser Recherche implementiert oder durch Render-/Hörtests abgenommen. Der private Modal-Edge-Schutz und der außerhalb des Repositorys gespeicherte Proxy-Token bleiben verbindlich; sämtliche neuen Routen müssen denselben Schutz erben.
