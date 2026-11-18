# Hochwertige Open-Source-Effekte für den Artist Workspace

Recherche vom 18.11.2026, nur Primärquellen. Keine Installation, kein Render und kein Hörvergleich. Die Auswahl ist eine technische Empfehlung; eine Gleichwertigkeit mit konkreten Valhalla-/Waves-Produkten ist damit nicht belegt.

## Lokaler Einbau am 18.11.2026

Die Effektkette lädt **CHOW Tape 2.11.4**, **CHOW Matrix 1.3.0** und **Dragonfly Plate 3.2.10** im lokalen Renderprozess. Die geprüften macOS-VST3 liegen im `plugins`-Ordner des privaten Workspace-Datenverzeichnisses. Der Worker akzeptiert diese drei Paketidentitäten mit der geprüften SHA-256 der jeweiligen Binärdatei. Die Plugins werden nicht mit dem Repository oder Projektpaketen verteilt. Die Klangbewertung aus dem Rechercheteil bleibt offen.

Unter der Clip-Wellenform zeigt der Effekt-Hörvergleich den ausgewählten Ausschnitt, die gerenderte Variante und deren Ausklang. Der Pegelabgleich betrifft die Wiedergabe. Die exportierte WAV enthält das erzeugte Signal. Bei geänderten Reglern oder Schnittgrenzen braucht die Vorschau einen neuen Render.

## Kurze Auswahl

| Kandidat | Wofür sinnvoll | Lizenz und Einbindung |
| --- | --- | --- |
| **[CHOW Matrix](https://github.com/Chowdhury-DSP/ChowMatrix)** | Kreatives Multi-Tap-/Matrix-Delay mit individuellem Feedback, Panorama, Modulation, Pitch-Shifting, Diffusion und Verzerrung. Erste Wahl für rhythmische Delays und experimentelle Räume. | BSD-3-Clause im Projekt; Abhängigkeiten beim eigenen Distributionsbuild mitprüfen. VST3/AU und weitere Formate. [Offizielle Produkte](https://chowdsp.com/products.html) bestätigen universelle Intel-/Apple-Silicon-Mac-Binaries. |
| **[Dragonfly Reverb](https://github.com/michaelwillis/dragonfly-reverb)** | Hall, Room, Plate und separate Early Reflections: passende Auswahl für konventionelle Räume, Vocal-Plate und Drum-Room. | GPL-3.0. [Release 3.2.10](https://github.com/michaelwillis/dragonfly-reverb/releases/tag/3.2.10) bietet macOS-universal; [Plugin-Makefile](https://github.com/michaelwillis/dragonfly-reverb/blob/master/plugins/dragonfly-hall-reverb/Makefile) baut auch VST3. Pedalboard-Kompatibilität hier noch nicht praktisch geprüft. |
| **[Airwindows Galactic3 / Consolidated](https://www.airwindows.com/galactic3/)** | Große, modulierte Ambient-Räume mit Detune und kontrollierbarem Undersampling. Consolidated ergänzt zahlreiche Sättigungs-, Dynamik- und Stereo-Effekte. | DSP und Registry MIT; [Consolidated](https://github.com/baconpaul/airwin2rack) bietet VST3/AU und Mac-universal. Der Projekttext trennt die permissive DSP-Bibliothek ausdrücklich von GPL-Abhängigkeiten im fertigen Plugin-Build. |
| **[CHOW Tape Model](https://github.com/jatinchowdhury18/AnalogTapeModel)** | Physikalisch modellierte Bandsättigung für Drum-Bus, Bass und Mixfärbung; fachlicher DSP-Hintergrund mit DAFx-Paper. | Desktop GPLv3, VST3/AU, Mac-universal laut [Hersteller](https://chowdsp.com/products.html). Spotify führt genau dieses Plugin als [mit Pedalboard funktionierend](https://github.com/spotify/pedalboard/blob/master/COMPATIBILITY.md), VST3 auf Mac/Linux/Windows und AU auf Mac. |
| **[ZL Equalizer 2](https://zl-audio.github.io/plugins/zlequalizer2/manual/) + [ZL Compressor](https://zl-audio.github.io/plugins/zlcompressor/manual/)** | Präziser dynamischer EQ mit bis zu 24 Bändern, Mid/Side und EQ-Matching; Kompressor mit mehreren Verarbeitungsstilen, Sidechain-EQ, Lookahead und Oversampling. Gute Kandidaten für die präzise Mixbearbeitung. | Beide aktuell **AGPLv3**, Logos ausgenommen: [EQ-Quelle](https://github.com/ZL-Audio/ZLEqualizer), [Kompressor-Quelle](https://github.com/ZL-Audio/ZLCompressor). VST3; [Installation](https://zl-audio.github.io/help/plugin_installation/) erläutert ARM64-/Apple-M-Chip-Builds. Die frühere Equalizer-Version ist abgekündigt; Equalizer 2 verwenden. |
| **[Surge XT Effects](https://surge-synth-team.org/surge-effects/)** | Separate Audioeffekt-Version: Delay, mehrere Reverbs einschließlich Spring sowie Chorus, Flanger, Phaser, Rotary, Filter und kreative Verarbeitung. Kompaktes Zusatzpaket für Modulation/Sounddesign. | [GPL-3.0](https://github.com/surge-synthesizer/surge). VST3/AU; [Mac-Installer](https://github.com/surge-synthesizer/surge/blob/main/scripts/installer_mac/make_installer.sh) enthält die Effects-Komponenten für x86_64/arm64. [Offizielle Effektübersicht](https://surge-synthesizer.github.io/) und [Changelog](https://surge-synthesizer.github.io/changelog/). |

## Was im Projekt bereits vorhanden ist

Der aktuelle `audio_core/engines.py` enthält in der `EFFECTS`-Whitelist schon Pedalboard-**Delay, Reverb, Compressor, NoiseGate, Limiter und Filter**. Die Kette konstruiert die eingebauten Klassen über `getattr(pb, effect)`; ein Host für externe Plugins über `load_plugin` ist dort noch nicht eingebaut. Die oben genannten Plugins sind daher zusätzliche Kandidaten, keine bereits bedienbaren Workspace-Werkzeuge.

[Pedalboard](https://spotify.github.io/pedalboard/) unterstützt externe **VST3 auf macOS, Linux und Windows** sowie **Audio Units auf macOS**. Das ist der naheliegende Integrationsweg für den lokalen Python-Worker. Eine native Plugin-Oberfläche wird dadurch nicht automatisch zur Web-Oberfläche: Parameter, Presets und Zustände müssten im Workspace zugänglich und reproduzierbar gespeichert werden. Für eine spätere Linux-Ausführung werden passende Linux-Plugin-Binaries benötigt; Mac-AUs sind dafür ungeeignet.

## Empfehlung

Zuerst **CHOW Matrix + Dragonfly + CHOW Tape** für Delay, Reverb und analoge Färbung untersuchen. **ZL Equalizer 2/Compressor** decken die wichtigen Mixwerkzeuge ab; **Galactic3** ergänzt große kreative Räume. **Surge XT Effects** ist die praktische Ergänzung für Chorus/Flanger/Phaser und Spezialeffekte. Diese Reihenfolge ist eine Einschätzung aus Funktionsumfang und Integrationsweg, kein Klangranking.

Für das spätere Testen im Workspace: Original erhalten, Presets als neue Varianten rendern, pegelangepasstes A/B; bei Delay/Reverb die Ausklangzeit erhalten und bei Lookahead/Oversampling Latenz kompensieren. Plugin-Host, Tempo-Synchronisation, Parameterautomation, Sidechain und Wiederherstellung des Plugin-Zustands jeweils tatsächlich prüfen. Ohne diese Prüfungen bedeutet VST3-Unterstützung noch keine garantierte Kompatibilität.

Optional für einen späteren Linux-Worker: [LSP Plugins](https://lsp-plug.in/) bietet weitere Dynamik-/Multiband-/Mixwerkzeuge; das Projekt ist ausdrücklich auf GNU/Linux ausgerichtet und gehört deshalb nicht in die erste Mac-Auswahl.

Nicht Bestandteil der OSS-Auswahl sind bloß kostenlose Closed-Source-Plugins. Beim Weiterverteilen oder Einbauen von Quellcode die konkreten GPL-/AGPL-/Framework-Bedingungen prüfen; kostenloser privater Testbetrieb und Redistribution sind unterschiedliche Einsatzfälle. Keine juristische Freigabe in dieser Recherche.
