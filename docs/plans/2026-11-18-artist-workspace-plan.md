# Dreamtelligence Artist Workspace – vollständiger Umsetzungsplan

**Stand:** 18.11.2026 · **Adressat:** Sol 6.2 · **Status:** Plan zur Übergabe, noch keine Umsetzung dieses Plans.

Dieser Plan umfasst den vollständigen gewünschten Ausbau. Die Reihenfolge der Arbeitspakete dient einer sicheren Umsetzung; spätere Pakete gehören weiterhin zum Auftrag. Ein fertiger Zwischenstand mit drei Werkzeugen ersetzt nicht den vollständigen Funktionsumfang.

## 0. Auftrag, feste Vorgaben und Übergabe

**Produktziel:** Ein Künstler importiert Material einmal, bearbeitet es in nachvollziehbaren Schritten, hört Varianten zuverlässig gegeneinander und exportiert verwendbare Audiospuren, Loops, Samples und MIDI für seine DAW. Die Oberfläche soll ihn bei der Arbeit führen und Fortgeschrittenen präzise Kontrolle geben.

**Zu integrieren:** vorhandene Separation, automatisches Mastering, MuScriptor/Beat-/Akkordanalyse, Sprachbearbeitung und Stable-Audio-Generierung; zusätzlich Matchering-Referenzmastering, Rubber Band, Loop-/One-Shot-Export mit librosa, Audio-QA mit FFmpeg/pyloudnorm, bedienbare Pedalboard-Ketten, Basic Pitch, DeepFilterNet, RNNoise und optionales AudioSR.

**Verbindliche Nutzerentscheidungen:**

1. Keine Marketing-Landingpage, Preis-/Credit-/Checkout-Flows, Stripe-Initialisierung oder öffentliche Registrierung. Der deaktivierte Bestand bleibt erhalten.
2. Keine obere Website-Navigation. Projektaktionen gehören in den Arbeitsbereich; keine Leiste mit Home, Features, Preisen oder Service-Unterseiten.
3. Dreamtelligence-Farben: Weiß, Lavendel, dunkles Violett, blaue/rosa Akzente. Kein Petrol-/Grün-Design.
4. Bestehende Modal-Dienste bleiben privat. Ein Clone darf ohne eigene private Konfiguration keine Ressourcen des Betreibers benutzen können.
5. Desktop-Arbeit und Export in Ableton/Logic stehen im Mittelpunkt. Die Web-App ergänzt diese Arbeit, ohne eine vollständige DAW, einen Plug-in-Host für beliebige Hersteller oder ein Distributionsportal zu versprechen.
6. Jetzt ausschließlich planen. Keine Pakete, Cloud-Ressourcen oder neue Modelle wurden für diesen Plan installiert, gebucht oder ausgeführt.

**Maßgebliche Begleitdokumente:**

- [Privater Ist-Betrieb](../PRIVATE_MODE.md)
- [OSS-Auswahl und Lizenzquellen](../research/2026-11-18-audio-chain-candidates.md)
- [Technische Fallen und konkrete Prüfkriterien](../research/2026-11-18-artist-workspace-technical-notes.md)
- [Vorherige Funktionsprüfung der fünf Modal-Apps](../verification/2026-11-18-modal-audit.md)
- [Kopierfertiger Auftrag für Sol 6.2](2026-11-18-sol-6.2-handoff.md)

Bei Abweichungen zuerst den tatsächlichen Code und die konkreten Nutzerentscheidungen prüfen. Historische kommerzielle READMEs sind keine aktuelle Produktspezifikation.

## 1. Tatsächlicher Ausgangspunkt

Repository: `/Users/ozi/XO-master`, öffentlicher Remote `dreamtelligence/XO-master`; nicht mit `dreamtelligence/XO` verwechseln. Ausgangs-HEAD bei dieser Planung: `19b8cf373daf5a122da52ada6869f398873141b9`. **Der aktuelle lokale Stand enthält wesentliche uncommittete und ungetrackte Änderungen, die dieser HEAD nicht enthält.**

| Bereich | Heute vorhanden | Für den neuen Arbeitsplatz nötig |
| --- | --- | --- |
| Frontend | Rund 7.200 Zeilen `index.html`, Inline-JS/CSS, vier funktionale Kacheln, WaveSurfer/A/B-Teile | Gemeinsames Projekt, Asset-Auswahl, ein Transport, Werkzeuginspektor, persistente Varianten, nachvollziehbare Aufgaben |
| Lokaler Zugang | `dev_server.py`, Standardbibliothek, Loopback, Dateiallowlist, geschützter HTTP-Proxy | Validierte Projekt-/Datei-/Job-Interfaces und langlebiger lokaler Worker; bisherige Sicherheitsinvarianten übernehmen |
| Separation | SCNet XL IHF, Mel-Band RoFormer, Stemauswahl, optional Instrumental und TTA | Assets direkt weiterreichen, gemeinsame Zeitbasis, Vollständigkeitsprüfung, Auswahl zwischen kohärenter Gruppe und Vocal-Optimierung untersuchen |
| Mastering | Eigene Pedalboard-/SciPy-Kette, pyloudnorm, 16-/24-Bit-Ausgabe | Zusätzlich **echte Matchering-Bibliothek mit Referenztrack**, Vergleich, klare Zielwerte und Messung der Exportdatei |
| MIDI/Analyse | MuScriptor, beat_this, essentia, MIDI/JSON/Text | Tempo-Events korrekt schreiben, Basic Pitch, Grid-Korrektur, Auswahlbereich, MIDI-Ansicht und Exportzeitbasis |
| Sprache | MossFormer, Whisper, AST, DSP und Schnitt | Modellwahl DeepFilterNet/RNNoise, überprüfbare Schnittvorschläge und Zeitmapping, sinnvolles A/B |
| Generierung | Stable Audio Open 1.0 als geschützte API, bisher kein funktionales UI dafür | Prompts, Seeds, Dauer/Varianten, Jobanzeige, Vorhören und Übernahme als Projektmaterial |
| Sicherheit | Fünf Modal-ASGI-Apps mit `requires_proxy_auth=True`, privater Token außerhalb des Repos | Dieselben Regeln für alle neuen Interfaces; projektbezogene Asset- und Jobprüfung, keine offenen Compute-Routen |
| Zahlung/Marketing | Templates/Funktionsschalter aus; Originalhandler archiviert; aktive Commerce-Handler 410 | Deaktiviert lassen, keine Reaktivierung durch Frameworkwechsel |
| Verifikation | Neun Schutztests, reale vorherige Audio-Kurztests, privater Mastering-Test | Workflow-, DSP-, Persistenz-, Abbruch-, Browser- und Hörprüfungen für alle neuen Funktionen |

### 1.1 Vor dem Ausbau zu korrigierende Befunde

- `create_click_track_midi()` verwendet den übergebenen Tempo-Wert momentan nicht. Ein Test bei 120 BPM verdeckt den Fehler. `tempo_map.txt` ist nur eine Textliste, keine MIDI-Tempo-Map.
- Enhancement bildet eine Vorschau aus Original links und Bearbeitung rechts, gekürzt auf die kleinere Länge. Nach entfernten Pausen/Füllwörtern sind das keine zeitlich entsprechenden Inhalte.
- Uploadhandler verwerfen die von `.spawn()` zurückgegebene Call-ID. Ein verlässlicher Einzelabbruch und die Auflösung unklarer Starts benötigen diese Identität.
- Status-JSON, Vorschauen und Downloads unterscheiden sich zwischen den fünf Apps. Ein vorhandenes `completed` kann teilweise fehlende Ergebnisse verdecken.
- Die Separation kombiniert Ausgaben unterschiedlicher Modelle. Deren Summe darf nicht ungeprüft als exakte Rekonstruktion des Originals dargestellt werden.
- Browserseitiges Decodieren aller vollständigen Float32-Stems skaliert schlecht. Vorberechnete Peaks und begrenzte Hörfenster vorsehen.
- Titel, Kommentare und manche deaktivierten Texte versprechen Funktionen oder Eigenschaften, die der Code nicht belegt. Keine entsprechenden Versprechen in das neue UI kopieren.
- Mehrere Images verwenden offene Paketbereiche wie `>=`. Ein funktionsfähiger aktueller Container beweist keinen reproduzierbaren späteren Neubau.

## 2. Was ein Künstler konkret erledigen können muss

| Ablauf | Konkretes Ergebnis | Erfolgsnachweis |
| --- | --- | --- |
| Remix vorbereiten | Song importieren, Stems wählen, Vocal/Bass/Drums vorhören, Tempo ändern, Spuren synchron exportieren | WAVs starten auf derselben Projektzeit und passen zum exportierten Tempo |
| Sample-Kit erstellen | Drum-Stem analysieren, Treffer/Loops vorschlagen, Grenzen korrigieren, einzelne Dateien exportieren | Keine abgeschnittenen Anschläge, passende Fades/Release-Enden, sinnvolle Namen/Metadaten |
| Harmonie übernehmen | Bass/Melodie als MIDI, Akkorde/Beat als Zusatzdaten, manuelle Korrekturen | MIDI landet mit definiertem Tempo und Offset an der erwarteten Stelle |
| Mix fertigstellen | Eigenen Mix mit automatischem oder Referenzmastering bearbeiten, Zielwerte und tatsächliche Messwerte prüfen | Hörvergleich bei vergleichbarer Lautheit; finale Datei geprüft |
| Stimme aufbereiten | Aufnahme säubern, entfernte Stellen prüfen, einzelne Schnitte zurücknehmen, Ausgabe vergleichen | Original bleibt erhalten, keine versteckten Text-/Zeitsprünge |
| Sound erzeugen | Text, Dauer und Seed einstellen, eine begrenzte Variantenreihe erzeugen, passende Variante übernehmen | Jeder Take hat Audio, Parameter, Seed und Herkunft; kein versteckter GPU-Dauerloop |
| Bandbreite ergänzen | AudioSR gezielt auf eine Variante anwenden und kritisch vergleichen | Experiment ist ausdrücklich gekennzeichnet; Original und verwerfbare Variante bleiben getrennt |
| Projekt weiterführen | Browser schließen/neu laden, später Projekt und laufende/abgeschlossene Aufgaben wiederfinden | Keine verlorenen Assets und keine doppelt gestarteten Jobs |

## 3. Produktstruktur und bedienbare Innovationen

### 3.1 Ein Arbeitsbereich mit vier Einstiegsvorlagen

Der leere Zustand zeigt zuerst **„Dateien importieren“** und zuletzt benutzte lokale Projekte. Vier kompakte Startvorlagen dienen als Abkürzung: **Remix & Samples**, **Mix fertigstellen**, **Stimme bearbeiten**, **Sounds erzeugen**. Sie legen ein Projekt und eine sichtbare Arbeitsfolge an, lösen aber noch keinen Cloud-Auftrag aus.

Alle Einzelwerkzeuge sind unabhängig von einer Vorlage zugänglich. Ein Benutzer muss nicht erst einen Assistenten vollständig durchlaufen, um eine einzelne Datei zu mastern.

### 3.2 Fünf unterscheidbare Bereiche

1. **Bibliothek:** Originale, Stems, Varianten, MIDI, Loops, Samples und Referenzen. Suche, Filter, Umbenennen, Mehrfachauswahl, nachvollziehbare Herkunft.
2. **Arbeitsfläche:** synchronisierte Spuransicht, Wellenformen, Auswahlregionen, Beat-Grid, Slice-Marker; bei MIDI stattdessen Piano-Roll/Drum-Raster im selben Kontext.
3. **Werkzeug-Inspektor:** Einstellungen zum ausgewählten Asset bzw. zur Auswahl. Ein Werkzeug besteht aus verständlichem Zweck, Eingängen, relevanten Reglern, Vorschau und genau einer klaren Renderaktion.
4. **Transport:** gemeinsames Play/Pause/Stop, Position, Loop, Abhörlautstärke, Solo/Mute, A/B und Lautheitsabgleich. Kein zweiter unkontrollierter Player in Ergebnisdialogen.
5. **Aufgaben-/Exportleiste:** Queue, tatsächliche Phase, abgeschlossene Ergebnisse, Fehler, gezielter Abbruch und Exportkorb. Aufklappbar; sie verdeckt nicht den einzigen Startknopf.

### 3.3 Funktionen mit echtem Arbeitsnutzen

- **Ergebnis direkt weiterverwenden:** Jeder Stem, Take und Render bietet „Weiter mit …“. Kein Herunterladen und erneutes manuelles Hochladen zwischen internen Schritten.
- **Auswahlbezogene Werkzeuge:** Ein markierter Drum-Bereich bietet Slice/Loop, ein fertiger Mix Mastering, MIDI enthält keine wirkungslosen Audiofilter. Nicht kompatible Kombinationen werden erklärt.
- **Bearbeitungsrezepte:** Sichtbare, veränderbare Schritte mit Eingang/Ergebnis. Vorlagen enthalten konkrete Werte und speichern ihre Version. Keine unkontrolliert durch ein Sprachmodell erzeugten Befehle.
- **Varianten mit Herkunft:** „Vocal → 128 BPM → +2 Halbtöne → EQ“ bleibt als nachvollziehbare Ableitung erhalten. „Neue Variante“ ersetzt nie die freigegebene Version.
- **Präziser Vergleich:** Original, zuletzt freigegebene Variante und neue Vorschau sind gezielt vergleichbar; A/B nutzt dieselbe Inhaltsposition oder ein explizites Schnittmapping.
- **Exportkorb:** Material aus mehreren Zweigen wird als ein konsistentes DAW-Paket vorbereitet. Unterschiedliche BPM-/Zeitbasen werden vor dem Export sichtbar.
- **Gezielte Neuberechnung:** Ein geänderter EQ führt nicht zu erneuter Separation. Ein anderes Transkriptionsmodell überschreibt keine vorhandene MIDI-Version.
- **Manuelle Korrektur statt Scheingenauigkeit:** BPM, halbes/doppeltes Tempo, erster Downbeat, Slice-Grenzen und Noten sind korrigierbar. Herkunft „erkannt“/„manuell“ bleibt gespeichert.

Nicht Teil des Auftrags sind ein allgemeiner KI-Chat, Voice-Cloning, Songpublishing, Social Feeds, Marketplace, Collaboration in Echtzeit oder ein beliebiger Audio-Unit/VST-Shop.

## 4. Layout, Stil und Interaktion

### 4.1 Desktop-Aufteilung

```text
Arbeitsbereich – keine Website-Navigation
┌─────────────────────────────────────────────────────────────────────────────┐
│ Projektname / gespeichert                 [Importieren] [Exportkorb (4)]    │
├─────────────────┬─────────────────────────────────────┬─────────────────────┤
│ BIBLIOTHEK      │ ARBEITSFLÄCHE                       │ AUSGEWÄHLTES WERKZEUG│
│ Originale       │ Zeit / Takte / Auswahl              │ Eingang: Vocal v1   │
│ > Song.wav      │ Original ━━━━━━━━━━━━━━━━━━━━━━━━   │ Tempo & Tonhöhe     │
│ Stems           │ Vocal   ━━━━━━━━━━━━━━━━━━━━━━━━   │ 123 → [128] BPM     │
│ > Vocal         │ Drums   ━━━│━━━│━━━│━━━│━━━       │ Tonhöhe [+2]        │
│ > Drums         │ Bass    ━━━━━━━━━━━━━━━━━━━━━━━━   │ [Auswahl vorhören]  │
│ Varianten       │                                     │ [Variante rendern]  │
│ Loops / MIDI    │ [Werkzeug hinzufügen]               │                     │
├─────────────────┴─────────────────────────────────────┴─────────────────────┤
│ ▶ / Pause / Stop  01:12.000  Loop  A/B  Pegelabgleich  Abhörlautstärke      │
│ Aufgaben: 1 läuft, 2 warten · „Stems werden getrennt“ [Details / Abbruch]    │
└─────────────────────────────────────────────────────────────────────────────┘
```

Die obere Zeile ist eine **Projekt-Aktionszeile innerhalb des Arbeitsbereichs**, keine zurückkehrende Website-Navigation. Projektwechsel über den Projektnamen bzw. die leere Startansicht. Keine globale Reihe von Home-/Tool-/Preislinks.

### 4.2 Größen und Verhalten als Umsetzungsvorgabe

- Ab etwa 1280 px: Bibliothek 240–280 px, Inspektor 320–360 px, Arbeitsfläche flexibel. Panels verstellbar und einklappbar; Mindestbreite der eigentlichen Bearbeitung wahren.
- 900–1279 px: ein Seitenpanel geöffnet, das andere als Drawer. Keine vier gequetschten Spalten.
- Unter 900 px: zentrale Datei-/Spuransicht, Inspektor als eigener Drawer/Sheet; Transport erreichbar. Kernauswahl, Vorhören, Jobstart und Download bleiben bedienbar.
- Unter 600 px: Spuren/Listen und Einzelwerkzeugansicht statt winziger DAW-Gesamtansicht. Mobile Dateiimporte und Downloads testen; Desktop bleibt das primäre Ziel.
- Nur der Inhaltsbereich scrollt horizontal für Timeline/Piano-Roll. Projektaktionen und Buttons dürfen nicht unzugänglich außerhalb des Viewports liegen.
- Sichtbarer Primärbutton benennt die Aktion: „Stems trennen“, „Loops erzeugen“, „MIDI erstellen“, „Vorschau rendern“, „Master rendern“, „Sounds erzeugen“. Kein unbeschrifteter Play-Knopf als Compute-Start.
- Sobald Eingänge fehlen, erklärt der deaktivierte Button den konkreten Grund. Ein leeres Ergebnis zeigt nicht einfach eine grüne Fertig-Meldung.

### 4.3 Dreamtelligence-Designsystem

| Token | Wert | Verwendung |
| --- | --- | --- |
| Hintergrund | `#F6F1FC` | ruhige Arbeitsfläche |
| Oberfläche | `#FFFFFF` | Karten, Inspektor, Dialoge |
| Haupttext | `#1C1629` | Überschriften, Text |
| Primär | `#311081` | Primäraktionen, Auswahl, Fokus |
| Hellblau | `#96B1FF` | Akzent, Visualisierung; kein weißer Kleinschrifttext darauf |
| Rosa | `#FADCEC` | Varianten-/Vergleichsakzente |
| Linie | `#EBEAF6` | dekorative Trennlinien |
| Sekundärtext | `#655E73` | Hinweise, Metadaten |

Quelle: vorhandene `--dt-*`-Tokens der Dreamtelligence-Website in `/Users/ozi/dreamtelligence.de/app/globals.css`. Farben als gemeinsame Tokens definieren; keine neuen `!important`-Schichten auf die alte CSS-Kaskade stapeln. Typografie aus dem aktuellen Entwurf übernehmen, sauber lokal bündeln bzw. nur lizenzierte lokale Schriftdateien verwenden. Kein ungeprüftes Kopieren kommerzieller Fonts.

Spur-/Statusfarben ergänzen Text, Symbole und Muster. Warnungen dürfen orange/rot sein; Erfolg braucht keinen grünen Markenbereich. Fokus und interaktive Grenzen brauchen ausreichenden Kontrast; die sehr helle dekorative Linie allein genügt dafür nicht.

### 4.4 Zugänglichkeit und Tastatur

- Alle Aktionen sind mit Tastatur erreichbar; Drag-and-drop besitzt Dateiauswahl-Alternative, Sortieren besitzt Hoch/Runter-Aktionen.
- Space: Play/Pause, Escape: Auswahl/Popover schließen, Cmd/Ctrl+Z: lokale Bearbeitung rückgängig, Cmd/Ctrl+Shift+Z: wiederherstellen; nicht innerhalb von Texteingaben abfangen.
- Loopgrenzen und Slider sind zusätzlich numerisch bedienbar. Fokusmanagement, sichtbare Labels, eindeutige Dialogtitel, `aria-live` nur für relevante Jobänderungen.
- Kein Autoplay; AudioContext erst nach Benutzeraktion starten/fortsetzen. Keine Pegelsprünge beim Variantenwechsel.
- Animationen respektieren `prefers-reduced-motion`. Wellenformen besitzen eine textuelle Zusammenfassung und zugängliche Zeit-/Regionsfelder.
- Undo ändert eine Bearbeitungsbeschreibung. Es kann keinen schon angefallenen Cloud-Verbrauch rückgängig machen und darf keinen erneuten GPU-Auftrag auslösen.

## 5. Gemeinsames Projekt- und Audiomodell

### 5.1 Fachbegriffe

- **Projekt:** lokale Arbeitseinheit mit Name, Sample-Rate, Tempo-/Taktinformationen, gewünschter Nutzung und Speicherort.
- **Asset:** unveränderliche Datei oder eindeutig versioniertes Analyseartefakt. Original, Stem, Audio-Variante, MIDI, Loop, Sample und Referenz sind Rollen, keine frei zugänglichen Dateipfade.
- **Region:** Auswahl in einem konkreten Audio-Asset, gespeichert als ganzzahlige Sample-Indizes in dessen Sample-Rate; `end` exklusiv.
- **Spur/Clip:** Anordnung eines Assets in der Projektzeit. Asset-Zeit, Clip-Offset und Projektzeit sind getrennt.
- **Bearbeitungsschritt:** Operation mit festen Eingangs-Asset-IDs, Parametern, Engine-Version und Seed, falls benötigt.
- **Run:** unveränderlicher Snapshot einer angeforderten Kette bzw. Variante mit eigenem Ergebnisbaum.
- **Job:** auszuführende technische Arbeit eines Schritts, mit lokalem und gegebenenfalls entferntem Ausführungsbezug.
- **Rezept:** speicherbare Vorlage für Schritte und Parameter; kein zweiter Asset-/Job-Datenspeicher.
- **Exportpaket:** konkrete, geprüfte Zusammenstellung von Dateien und Manifest mit definierter Zeitbasis.

### 5.2 Nicht destruktiv und dauerhaft

Originale sind schreibgeschützt. Abgeleitete Dateien bekommen neue IDs; ein Name ist nur eine Anzeigeeigenschaft. Projekte dürfen denselben Blob dedupliziert nutzen, ohne sich gegenseitig umzubenennen oder zu löschen. Referenzen auf vorhandene Dateien werden nicht durch bloße Dateinamen hergestellt.

Ein Parameterwechsel speichert zunächst einen Entwurf. Bereits gerenderte Ergebnisse bleiben einem alten Snapshot zugeordnet und werden bei geänderter Vorstufe als „basiert auf älterem Stand“ gekennzeichnet. Neue Nachfolger nutzen die konkret ausgewählte Version, niemals stillschweigend „die neueste Datei“.

Projektzustand, Jobzustand und Versionshistorie liegen serverseitig in einer lokalen SQLite-Datenbank. Browserzustand enthält Auswahl, Zoom und Panelzustände; Browser-Storage ist kein alleiniger Speicher für Audio oder Projektgeschichte. Autosave hat bestätigte Revisionen und zeigt „Speichert … / Gespeichert / Nicht gespeichert“.

### 5.3 Zeitbasis und Audioformate

- Originalformat/-Sample-Rate/-Bit-Tiefe/-Kanalzahl erhalten und erfassen. Bei Projektanlage 44,1 oder 48 kHz wählen; sinnvolle Voreinstellung aus erster Datei, sonst 48 kHz. Abweichende Quellen werden als Ableitung konvertiert.
- Interne Bearbeitung verlustfrei, vorzugsweise Float32; keine wiederholten MP3-Konvertierungen. Dithering kontrolliert erst beim quantisierenden finalen PCM-Export.
- Modellein-/ausgänge haben explizite Adapter: Separation 44,1 kHz Stereo, vorhandenes Sprachmodell 48 kHz Mono, RNNoise korrektes 48-kHz-Raw-Format, Stable Audio modellabhängige Rate. Das Original bleibt unverändert.
- Jede Konvertierung speichert tatsächliche Rate, Länge, Kanalabbildung, Zeitoffset und Engine-Version. Kein stilles Stereo→Mono beim normalen Musikexport.
- Gemeinsam exportierte Stems erhalten gleiche Startreferenz, Sample-Rate und Dauer; Ausklänge und zulässige Endverlängerung sind eine explizite Exportentscheidung.
- Tempo ist nicht gleich Playback-Rate. Original-Beats, korrigiertes Grid, Zieltempo, Audio-Stretch und MIDI-Tempo-Events werden als zusammengehörige Zeitabbildung behandelt.
- Analyseschätzungen ohne belastbare Konfidenz liefern `confidence=null` mit Herkunft. Keine erfundenen Prozentanzeigen oder „Studioqualität“-Scores.

## 6. Werkzeuge – vollständige Funktionsspezifikation

### 6.1 Import und Projektbibliothek

Mehrere Dateien per Auswahl/Drop importieren, sichtbarer Upload-/Validierungsfortschritt, sichere Namen, Duplikaterkennung per Inhaltshash, Rollen „Material“ oder „Referenz“. Probe/Decode serverseitig anhand des Inhalts, nicht allein Dateiendung/MIME. Defekte, leere, DRM-geschützte oder zu große Eingaben nachvollziehbar abweisen. Mehrkanaldateien benötigen eine klare Downmix-/Kanalauswahl; Basisumfang ist Mono/Stereo.

Import erzeugt Original, technische Metadaten, platzsparende Peaks und eine hörbare Vorschau. Schwere Beat-/Tonart-/Modellanalysen starten erst durch Auftrag/Vorlage. Projekt umbenennen/duplizieren/archivieren/als Paket sichern; mehrfach verwendete Assets zeigen ihre Verwendung vor dem Entfernen.

### 6.2 Analyse und Qualitätscheck

Technik: Dauer, Kanäle, Sample-Rate, Codec/Bit-Tiefe, Sample-Peak, True Peak, LUFS, LRA, Stillebereiche, nicht-finite Samples und erkannte Übersteuerung. Musik optional: Beat-/Downbeat-Zeiten, BPM, Takt und Tonart/Akkorde aus vorhandenen Engines. Manuelle Tempo-/Downbeat-Korrektur wird gespeichert.

Vorher/Nachher zeigt gemessene Werte, Ziel, Messmethode und Toleranz getrennt. Stille oder zu kurze Signale dürfen „nicht messbar“ ergeben. Ausgangsprüfung immer auf **der tatsächlich erzeugten Exportdatei** nach Resampling/Encoding. Ein vorhandener Limiter ist kein True-Peak-Nachweis. Vergleichbare Abhörlautheit ist ein eigener Monitor-Schalter, keine heimliche Änderung am Export.

### 6.3 Stem-Trennung

Presets: Gesang/Instrumental, vollständige Gruppe und benutzerdefinierte Stems. TTA nur als bewusste Qualitätsoption, mit tatsächlich gemessenem Zusatzaufwand; kein fest versprochener Faktor aus altem UI.

Engine-Details sind im erweiterten Bereich. Prüfen, ob zusätzlich zu Hybrid-Vocals eine zusammengehörige SCNet-Stemgruppe ausgegeben werden kann. Auswahl verständlich erklären: optimierter Einzel-Vocal versus zusammengehörige Remix-Gruppe. Für eine Gruppe Kanalzeitbasis und gemeinsames Processing erhalten; eine Summe aus verschiedenen Modellen darf nicht als mathematisch identisch zum Original behauptet werden.

Ergebnisse: eigenständige Assets und eine Stemgruppe, synchron hörbar, Solo/Mute/Gain, Original-Vergleich, „Weiter mit“ Slice/Tempo/MIDI/Effekte. Fehlende erwartete Stems ergeben `partial` oder Fehler, niemals stilles Vollerfolgssignal.

### 6.4 Loop-/Sample-Labor

Modi **Loops** und **One-Shots**. Vorschläge kommen aus vorhandenen Beats/Downbeats bzw. librosa-Onsets/Backtracking. Künstler kann Grenzen, ersten Downbeat, Tempo, Vorlauf, Release-Ende und Snap ändern.

- Loops: freie Region, 1/2/4/8/16 Takte, Loop-Vorhören, gridbasiertes Verschieben, optionale Naht-/Fade-Behandlung.
- One-Shots: Empfindlichkeit, Mindestabstand, Mindestlänge, Vorlauf, Ausklang, Fades, Auswahl/Verwerfen einzelner Treffer. Kicks/Snares nicht ohne belegte Klassifikation automatisch als sicher erkannt beschriften; zunächst Treffer-/Sample-Namen erlauben.
- Grenzen können an Nullstellen korrigiert werden; ursprüngliche Transiente und gewählter Ausklang bleiben erhalten. Keine pauschalen langen Fades auf jeden Schlag.
- Optionales Einzel-Sample-Pegeln bleibt getrennt von gemeinsamem Stem-Gain. Bei Stemgruppen keine automatische unabhängige Normalisierung.
- Ausgabe: editierbare Regionen, WAV-Einzeldateien/ZIP, Vorschau und Manifest mit Quelloffset, BPM, Takt, Tonartschätzung, Fades und Rate. Keine ungefragte Neuberechnung der Stems.

### 6.5 Tempo und Tonhöhe mit Rubber Band

Eingang: einzelner Clip, Loop oder ausgewählte Stemgruppe. Felder: Quell-BPM (erkannt/manuell), Ziel-BPM, Tonhöhe in Halbtönen/Cents, Formant-/Transientenoptionen soweit die gepinnte Engine sie tatsächlich unterstützt. Einsteiger sehen Tempo und Tonhöhe; erweiterte Einstellungen zeigen keine nicht implementierten Regler.

Grenzen als konservativer Start: Quell-/Ziel-BPM 30–300 und Pitch ±12 Halbtöne; diese sind UI-Produktgrenzen, keine Qualitätsgarantie. Extremfälle ausdrücklich als klanglich zu prüfend behandeln. Größere Bereiche erst nach Tests erweitern.

Rubber-Band-Offlinemodus nutzen; tatsächliche Ausgabelänge auslesen. Gleiche globale Zeitabbildung für gemeinsam bearbeitete Spuren, Stereo nicht kanalweise auseinanderziehen. Die gleiche Ratio allein beweist keine Phasenkohärenz; entsprechende Tests sind Pflicht. Instrumental und Vocal werden nicht unbemerkt verschieden lang.

Vorschau auf einer Auswahl, anschließend bewusster Vollrender. „Mit MIDI übertragen“ verwendet dieselbe Zeitabbildung/Tempo-Map. Ein reiner Tonhöhenwechsel ändert Notenwerte inklusive relevanter Pitch-Bends konsistent; Audio ohne MIDI darf separat bleiben.

Für MIDI gelten präzise Regeln: Halbtöne verschieben melodische Notennummern; vorhandene relative Pitch-Bend-Kurven dabei nicht ein zweites Mal transponieren. GM-Drums standardmäßig ausnehmen. Werte außerhalb 0–127 führen zu erklärter Validierung, nicht heimlichem Clamping. Cents werden nicht als ganze Noten gerundet: nur mit ausdrücklich definiertem Bend-/Tuningmodus und geprüftem RPN-Bereich übertragen; andernfalls Audio-Cents getrennt bearbeiten und die nicht übertragbare MIDI-Änderung erklären. Konkurrierende polyphone Bend-Kurven nicht ungeprüft auf einen Kanal zusammenlegen.

### 6.6 MIDI, Akkorde und Beat-Grid

MuScriptor und Basic Pitch sind auswählbare Engines mit erklärtem Einsatzzweck; Basic Pitch bevorzugt einzelne instrumentale Stems, MuScriptor kann vorhandene Mehrinstrument-/Drumwege bedienen. Beat/Akkorde/Tonart können unabhängig angefordert werden. Keine doppelte Modellinferenz, wenn vorhandene identische Analyse genügt.

Anzeige: Piano-Roll oder GM-Drum-Raster, Notenliste, Spurname/Instrumentzuordnung, Tempo/Takt, Quellregion. Bearbeitung: Noten auswählen/verschieben, Länge, Velocity, Löschen/Hinzufügen, Quantisierungsstärke und Undo. Kein komplettes Notensatzsystem oder DAW-Kompositionseditor.

Export als Standard-MIDI mit korrektem Anfangstempo und Takt-Events; variable Tempi nur mit echter Tempo-Map. Für konstanten Projektmodus die Umrechnung ausdrücklich festlegen. Texttempo-Listen ergänzen, ersetzen aber keine MIDI-Events. In Regionen hineinragende Noten werden nach dokumentierter Clip-/Überhangregel behandelt. Negative lokale Zeiten sind unzulässig.

Hörvorschau per dokumentiertem GM-/Synth-Weg mit lizenzgeprüften Soundfonts oder eigener einfacher Vorschau; nicht als Rekonstruktion des ursprünglichen Instruments bezeichnen. Tempo-/Quantisierungskorrektur verändert keine Originaldatei.

### 6.7 Effekte und kleiner Remix-Mixer

Pedalboard ist vorhanden und wird als geordnete, speicherbare Kette bedienbar: Gain, Hoch-/Tiefpass, parametrischer EQ, Kompressor, Noise Gate, Limiter; Hall/Delay als bewusste kreative Ergänzung. Pro Effekt Bypass, Reset, verständliche Parameter mit Einheiten und sichere Grenzen. Reihenfolge per Drag **und** Tastatur ändern.

Vorschau und Export benutzen dieselbe DSP-Implementation/Chain-Version. Parameteränderungen starten keinen GPU-Auftrag. Leichte Abhör-Gains/Mute/Solo reagieren direkt; klangverändernde DSP-Vorschauen werden aus dem zentralen Renderweg erzeugt und bei veralteten Parametern entsprechend markiert. Kein unehrlicher Browserfilter als angeblich identischer Export.

Remix-Mixer: begrenzte Projektspuren, Gain/Pan/Mute/Solo, Position/Clipregion, gemeinsamer Stereo-Bounce. Kein Mikrofon-Recording, keine beliebigen VST-Installationen, Automation oder Multibus-DAW im Grundumfang. Erweitern erst bei belegtem Bedarf.

Effektzustände über Audioblöcke erhalten, pro neuem Job sauber zurücksetzen. Delay-/Hall-Tail hat definierte Maximaldauer und Exportoption „Ausklang erhalten / auf Länge schneiden“.

Gleicher DSP-Code allein garantiert bei einem Ausschnitt keine Gleichheit zum Vollrender: Compressor/Hall brauchen definierten Vorlauf/Zustand, Mastering/Referenzanpassung gegebenenfalls eine Analyse des vollständigen Eingangs. Eine schnelle Auswahlprobe ist als vorläufig markiert, wenn dieser Kontext fehlt. Eine verbindliche Ergebnisvorschau stammt aus dem vollständigen Render oder aus einem nachweislich entsprechenden, eingefrorenen Analyse-/DSP-Zustand.

### 6.8 Automatisches und Referenz-Mastering

Zwei klare Modi: **Automatisch** mit der bestehenden Kette und **An Referenz orientieren** mit echter Matchering-Bibliothek. Referenztrack ist ein eigenes Asset mit eigener Vorschau; keine URL-Downloads fremder Tracks.

Automatisch: Intensität, Ziel-Lautheit und gewünschter Headroom/True-Peak-Grenzwert; vorhandene Bass-/EQ-Optionen nur zeigen, wenn ihre echte Wirkung geprüft ist. Referenzmodus verarbeitet Target plus Reference; technische Limits und Anpassungen des Referenzpegels dokumentieren. Er ersetzt nicht jedes Detail des Referenzmixes.

Vorhören von Original, Auto- und Referenzvariante bei optional gleichem Abhörpegel. Ausgangs-QA nach finalem Format; Ziele sind keine garantierten Plattformstandards. Übersteuerung und Zielverfehlung erzeugen einen verständlichen Hinweis bzw. blockieren einen als konform angeforderten Export. Bewusster Export eines nicht konformen kreativen Ergebnisses benötigt eindeutige Kennzeichnung, kein falsches Prüfzeichen.

Mastering ist für fertige Mixe vorgesehen. Stems werden nur auf ausdrücklichen Auftrag einzeln gemastert; ein automatisches Master auf jeder Spur würde die gemeinsamen Pegelverhältnisse ändern.

### 6.9 Sprachbearbeitung und Schnittprüfung

Rauschunterdrückung ist eine Auswahl: vorhandener MossFormer, DeepFilterNet oder RNNoise. **Nicht alle drei standardmäßig hintereinander.** Weitere Schritte sind Pegel/DSP, optional Füllwort-/Pausenvorschläge und AST-basierte Störsegmentvorschläge.

Sprachtranskript dient als Hilfe zum Prüfen und Navigieren. Entfernen ist ein eigener bearbeitbarer Schnitt: vorgeschlagene Stellen markieren, vorhören, bestätigen/ablehnen und zurücknehmen. Füllwörter sind sprach-/kontextabhängig; keine Garantie vollständiger oder verlustloser Erkennung.

Ein Edit-Decision-Log mit Zuordnung Quellzeit↔Ergebniszeit ist Pflicht für zeitverändernde Bearbeitungen. Reines Denoise vergleicht gleiche Position, Schnitte nutzen entsprechendes Quellsegment oder schalten A/B nur für vergleichbare Auswahl frei. Original links/Bearbeitung rechts wird nicht als normale Stereoausgabe verkauft.

Mono-/Stereoentscheidung und Stillebehandlung sind ausdrücklich dokumentiert. RNNoise erhält korrekt konvertiertes Raw-PCM ohne WAV-Header. Ergebnis ist eine neue WAV-Variante plus Schnitt-/Verarbeitungsprotokoll.

### 6.10 Text-to-Audio und Varianten

Bedienbare Oberfläche für die vorhandene Stable-Audio-API: Prompt, optionale Negativbeschreibung, Dauer, Seed, Variantenanzahl; erweiterte Steps/Guidance nur innerhalb serverseitiger Grenzen. Dauergrenze aus Capability-Interface beziehen; vorhandenes Modell maximal 47 Sekunden, keine endlose Songgenerierung versprechen.

Voreinstellung ein Take; Batch maximal drei Takes sequenziell, jeder als eigener Job. Seed bei Zufall vor dem Start festlegen und speichern. Prompt/Parameter bleiben editierbar; „noch eine Variante“ startet sichtbar neue Arbeit. Gleicher Seed ist ein Reproduktionshilfsmittel, keine zugesicherte Bitidentität über unterschiedliche Runtimes.

Ergebnisse als Takes mit Vorhören, Auswahl, Verwerfen, Umbenennen und „Als Projektmaterial übernehmen“. Loop-Vorschlag und BPM-Anpassung sind anschließende Werkzeuge; eine Promptangabe „128 BPM“ ist keine bewiesene Taktgenauigkeit. Keine zusätzlichen Cloud-LLM-Aufrufe zum unbemerkten Übersetzen oder Prompt-Erweitern.

### 6.11 AudioSR als kontrolliertes Experiment

Integration des überprüften Basic-Checkpoints, nicht eines beliebigen lizenzunklaren Speech-Downloads. Tool heißt **„Bandbreite ergänzen – experimentell“**. Standardmäßig aus; keine automatische Stufe eines jeden Masterings.

Auswahlvorschau, Modell-/Seed-/Parameterbezug, Originalbeibehalt und hörbarer Vergleich. Zweck ist generative Hochfrequenzerweiterung bandbegrenzter Signale. Keine Behauptung, verlorene Originaldetails wiederherzustellen oder jede MP3-Datei zu reparieren. Rausch-/Hall-/MP3-Fälle getrennt testen und schlechte Resultate ohne Erfolgslabel verwerfen können.

### 6.12 Exporte und DAW-Pakete

- Einzeldatei, ausgewählte Assets, Stemgruppe, Looppack, One-Shot-Kit, MIDI oder vollständiges Projekt-/DAW-Paket.
- Wahl von WAV PCM16/24 und Float32, sofern sinnvoll unterstützt; MP3 ausdrücklich als Hör-/Austauschkopie. Keine formatabhängigen Regler ohne Wirkung.
- Gemeinsame Sample-Rate, Offset und Länge für ausgerichtete Spuren; Loops zusätzlich als kompakte Ausschnitte mit Originaloffset im Manifest.
- MIDI-Tempo/-Takt und Audio-Stretch müssen zueinander passen. Referenzdateien werden nicht automatisch mitgepackt.
- Einheitliche sichere Benennung, beispielsweise `Projekt_Vocal_128BPM_Plus2st_v03.wav`. Tonart nur als sichere manuelle Angabe oder gekennzeichnete Schätzung.
- `manifest.json`, lesbare Exportnotiz, bearbeitungsbezogene Herkunft, Software-/Modellversionen, Seeds, Sample-Raten, Quelloffsets und QA-Werte.
- „Ableton/Logic-Paket“ bedeutet zunächst standardisierte WAV/MIDI/ZIP-Dateien mit Importanleitung. Keine zugesagten nativen `.als`-/Logic-Projektdateien oder funktionierendes Browser→DAW-Drag-and-drop ohne eigenen Kompatibilitätsnachweis.
- Projektpakete enthalten relative Referenzen und optional explizit ausgewählte Audiodateien, niemals private Tokens, absolute private Konfigurationspfade oder fremde Projektinhalte.

## 7. Zielarchitektur und begründete Stack-Entscheidung

**Planentscheidung:** modulares React-/TypeScript-Frontend mit Vite; lokales FastAPI-Backend mit SQLite und einem zuständigen Worker; bestehender Modal-Workspace für entfernte Verarbeitung. Kein öffentlicher Mehrbenutzerbetrieb in diesem Ausbau.

| Teil | Entscheidung | Begründung / Grenze |
| --- | --- | --- |
| Web-UI | React + TypeScript + Vite; eigene CSS-Tokens | Varianten, Timeline, Inspektor und Queue brauchen geteilten, typisierten Zustand. Die bestehende große Inline-Datei ist dafür eine schlechte Erweiterungsstelle. |
| Serverzustand im UI | Ein Query-Cache für Projekte/Assets/Jobs, vorzugsweise TanStack Query | Abfragen, Invalidierung, Polling und veraltete Antworten zentral behandeln. Ein zusätzlicher globaler State-Framework-Stack ist nicht nötig. |
| Lokaler UI-Zustand | React-State/Reducer | Auswahl, Zoom, Panels und Transport getrennt von bestätigten Projektrevisionen halten. |
| Audio-Transport | Ein Web-Audio-Modul mit gemeinsamer Clock | Synchronität und A/B nicht auf viele unabhängig startende HTML-Audioelemente verteilen. |
| Wellenformen | Vorberechnete Peaks; WaveSurfer für Darstellung, falls die gepinnte Version die benötigten Interaktionen erfüllt | Keine Vollfile-Decodierung nur für eine Wellenform; WaveSurfer ist weder Render-Engine noch vollständiger Editor. |
| Lokaler Server | FastAPI/Pydantic, Uvicorn mit genau einem zuständigen App-/Scheduler-Prozess | Bereits Python-DSP und Modal vorhanden; validierte Interfaces und Streaming-Dateien statt immer weiterer Sonderfälle im bisherigen Standardbibliotheksproxy. |
| Persistenz | SQLite lokal, Metadaten/Jobs; Dateien im privaten Dataverzeichnis | Für einen lokalen Einzelbenutzer reicht das. Keine Audio-BLOBs oder Datenbankdateien auf einem gemeinsam beschriebenen Netzwerk-/Modal-Volume. |
| CPU-Arbeit | Lokaler begrenzter Prozess-Worker für FFmpeg, Slices, Rubber Band, Effekte, Matchering und Export | Verwendbare lokale Vorschauen und kein GPU-Start für jeden DSP-Regler. Reine DSP-Funktionen gemeinsam wiederverwenden. |
| Modellarbeit | Bestehende geschützte Modal-Apps; getrennte CPU-/GPU-Entrypoints je Bedarf | Basic Pitch/leichte Sprachfilter müssen nicht erst MossFormer/MuScriptor auf einer GPU laden. AudioSR bekommt einen isolierten Modellpfad. |
| Assets in Modal | Begrenzter gemeinsamer privater Staging-Cache für neue Workspace-Aufträge | Input einmal übertragen und zwischen Modellschritten referenzieren; bestehende App-Volumes und alte Ergebnisse bleiben erhalten. |
| Zugang | Lokaler Same-Origin-Server + privater Modal-Proxy-Token | Weder Browser noch Git-Clone bekommen den Schlüssel. Kein offener Vercel-Rechenproxy. |

### 7.1 Bewusst nicht neu einführen

- Next.js/SSR ist für diesen privaten Audio-Arbeitsplatz nicht erforderlich. Keine neue SEO-/Marketing-Architektur.
- Supabase/Neon als Projekt-DB würden aktuell Konto-/Netzwerk-/Mandantenkomplexität erzeugen. Erst bei ausdrücklich gewünschtem Mehrbenutzerbetrieb neu bewerten.
- Vercel als öffentliche Steuerung, AWS/S3 als neue Speicherschicht, Runpod als neuer GPU-Anbieter und weitere bezahlte Dienste sind aktuell nicht nötig. Deshalb keine Anbieterbuchung, kein automatischer Fallback und keine erfundenen Preisvergleiche.
- Kein Redis/Celery/Kafka/Kubernetes für die lokale Einzelbenutzer-Queue. Ein dauerhafter lokaler Worker genügt zunächst.
- Kein allgemeiner Node-Editor als Pflichtbedienung. Intern ist die Verarbeitung ein gerichteter Graph; Künstler sehen eine verständliche Schrittreihe und Herkunft.

Wenn diese Annahmen geändert werden, vorher aktuelle Anbieterbedingungen, Kosten, Rechte, Datenhaltung und Limits vergleichen und einen eigenen ADR erstellen. Dieser Plan ist keine Freigabe für einen öffentlichen Cloud-Dienst.

### 7.2 Laufzeit, Installation und Start

- Vorhanden bei Planung: Node `26.8.2`, npm `11.19.1`, globales Python `3.14.7`, Modal-CLI/SDK `1.5.5` in eigener pipx-Umgebung. Nichts davon stillschweigend ersetzen.
- Backend/DSP in einer **projektbezogenen Python-3.11-Umgebung**, weil vorhandene Audio-/Modellpakete nicht pauschal mit globalem 3.14 kompatibel sind. Konkrete Paketstände vor Installation gegen Primärquellen prüfen, danach locken.
- Kein `pip install` ins globale Python und keine Änderung der bestehenden Modal-pipx-Umgebung. GPU-Gewichte bleiben in Modal; kleine lokale DSP-/Preview-Abhängigkeiten und deren Platzbedarf vorher prüfen.
- Normaler Künstlerstart: ein dokumentierter Launcher bzw. `npm start`, der den gebauten Frontend-Stand und das lokale Backend auf `http://localhost:8765` startet. Der Launcher benutzt ausdrücklich den Python-Pfad der Projektumgebung.
- Entwicklungsmodus darf Vite auf `127.0.0.1:5173` und Backend auf `127.0.0.1:8765` nutzen, mit `strictPort` und explizit erlaubtem Entwicklungs-Origin. Vites `changeOrigin` allein löst die Origin-/CSRF-Prüfung nicht. Im Normalbetrieb kein zweiter Origin.
- Lockfiles für JS und Python einchecken, konkrete Binär-/Modellversionen erfassen. Keine neuen offenen CDN-Imports und keine ungeprüften `latest`-/`>=`-Rebuilds für kritische Audiowege.
- Optionaler Legacy-Modus bleibt geschützt erreichbar, bis die Abnahme der neuen UI abgeschlossen ist; er ist kein öffentlicher Ersatzpfad und aktiviert keinen Commerce-Code.

## 8. Modulaufteilung und Dateien

Die folgende Struktur benennt Verantwortungen. Dateien nach Bedarf zusammenhalten; nicht für jeden Datentyp eine leere Abstraktion erstellen.

```text
web/
  package.json, package-lock.json, vite.config.ts
  src/
    app/             App, Projektwechsel, bestätigter Projektzustand
    workspace/       Bibliothek, Spuren/Regionen, Inspektor, Varianten, Exportkorb
    tools/           konkrete Panels + gemeinsame Operation-Registry
    audio/           Transport, A/B, Fensterpuffer, Peaks/MIDI-Vorschau
    api/             genau ein HTTP-Client und Query-/Job-Anbindung
    styles/          Dreamtelligence-Tokens und Komponentenregeln
studio/
  app.py             lokale FastAPI-Anwendung und Sicherheitsmiddleware
  models.py          validierte Requests/Responses und Zustände
  store.py           SQLite, Migrationen, Revisions-/Jobtransaktionen
  assets.py          sichere Imports, Datei-/Blob-Verwaltung, Range/Peaks
  pipeline.py        Vorprüfung, Abhängigkeiten, Cache-/Run-Snapshots
  jobs.py            Queue, Zustandsübergänge, Recovery, Cancel
  modal_adapter.py   erlaubte entfernte Interfaces, Token, Transfer, Normalisierung
  worker.py          genau ein zuständiger lokaler Dispatcher
audio_core/
  analysis.py, slicing.py, stretch.py, effects.py
  mastering.py, midi.py, speech.py, export.py
  registry.py        verfügbare Operationen/Engines und ihre Schemas
modal_app_*.py       vorhandene Deployments, weiter geschützt, versionierte Erweiterungen
tests/
  security/          bestehende Schutzinvarianten erhalten/erweitern
  audio/             DSP-/Format-/Timing-Fixtures
  workflow/          Import → Run → Artefakte → Export/Recovery
web/...tests...      UI/Transport/Browser-Ende-zu-Ende
disabled/            archivierter Marketing-/Commerce-/Legacy-Bestand
docs/plans/          Plan, Fortschritt, spätere ADRs
docs/verification/   reale Prüfnachweise und Benchmarks
```

**Kleine gemeinsame Interfaces:**

- `AssetStore`: importieren, Metadaten/Peaks lesen, sicheres Artefakt öffnen, Verwendung prüfen, kontrolliert entfernen.
- `Pipeline`: Entwurf prüfen, unveränderlichen Run anlegen, berechenbare Nachfolger bestimmen.
- `JobRunner`: anfordern, Status lesen, Abbruch anfordern, Ergebnisse übernehmen. Zwei reale Adapter: lokaler Prozess und geschütztes Modal. Der Aufrufer kennt keine privaten Cloud-URLs.
- `AudioTransport`: laden/Play/Pause/Seek/Loop, Monitor-Gain/Solo/A/B setzen; genau eine Clock und ein zuständiger Pufferbesitzer.
- `Exporter`: Paket vorbereiten, rendern/prüfen, freigegebene Artefakte/Manifest bereitstellen.

Eine Engine-/Parametervalidierung wird von UI-Schema, Vorschau und Vollrender gemeinsam verwendet. Keine zweite Handvoll unterschiedlicher Fetch-/Polling-/Downloadfunktionen in jedem Werkzeug.

## 9. Datenmodell und Verträge

### 9.1 Lokale Tabellen / Entitäten

| Entität | Pflichtinhalt |
| --- | --- |
| `projects` | UUID, Name, Revision, Projekt-Sample-Rate, Tempo-/Taktmodell, Nutzungszweck, Zeitstempel |
| `assets` / `blobs` | UUID, Projektbezug, Inhaltshash, Rolle/Typ, sichere interne Referenz, tatsächliches Format, Sampleanzahl, Kanäle, Provenienz |
| `clips` / `regions` | Asset-Version, Projektstart, Sample-Grenzen, Fades, Loop-/Slice-Metadaten |
| `analysis` | Asset-/Engine-/Versionsbezug, Schema-Version, Messwerte mit Einheiten und Verfügbarkeit |
| `recipes` / `drafts` | Operationen, geordnete Eingänge, Entwurfsrevision, UI-Parameter |
| `runs` / `steps` | eingefrorener Graph, Eingangs-Hashes, kanonische Parameter, Seeds, Modell-/Codebezug, Cache-Schlüssel |
| `jobs` | UUID, Step/Run, Zustand, lokaler Prozess/Remote-Job/Call-ID, Phase, Fehlercode, Cancel-Anforderung, Zeiten |
| `job_events` | monotone ID, Job, Zustand/Phase, redigierte Details; keine Audiodaten/Tokens |
| `exports` | Paketmanifest, Ausgabeparameter, Messresultat, Asset-Auswahl und Freigabestatus |
| `settings` / `schema_version` | lokale Einstellungen, Quoten und nummerierte Migrationen; keine Browser-Cloud-Schlüssel |

SQLite-Transaktionen, Foreign Keys, kurze Schreibtransaktionen, eindeutige Constraints und getestete Migrationen. Audio liegt in privaten Dateien. Löschungen beachten Referenzen, aktive Jobs und einen recoverbaren Papierkorb; Bibliotheksentfernen ist nicht gleich Original vom Mac löschen.

### 9.2 Operation-Registry

Jede Operation beschreibt: ID, Schema-Version, geeignete Eingangs-/Ausgangstypen, unterstützte Regionen/Kanäle/Raten, Parameter mit Einheiten/Grenzen, Preview-Fähigkeit, lokale/entfernte Ausführung, verfügbare Engines, Modell-/Lizenzstatus und Abhängigkeiten.

Status einer Engine: `ready`, `needs_setup`, `unavailable`, `license_restricted`, `experimental`. Das ist ein tatsächlicher Capability-Status, kein Ersatz für die Implementierung. Für die Endabnahme müssen alle im aktuellen privaten Nutzungsprofil zulässigen Engines real bedienbar und geprüft sein.

### 9.3 Lokale HTTP-Interfaces

Alle Pfade sind Same-Origin und validiert. Namen/Details dürfen bei Implementierung verbessert werden, die fachlichen Garantien bleiben:

| Interface | Zweck / wichtige Regel |
| --- | --- |
| `GET /api/capabilities` | Engines, Versionen, Verfügbarkeit und echte Limits ohne Secrets |
| `GET /api/session` | kurzlebiger lokaler CSRF-/Sessionbezug, keine Modal-Credentials |
| `GET/POST /api/projects` | lokale Projekte lesen/anlegen |
| `GET/PATCH /api/projects/{id}` | Projektdaten; konkurrierende Revision mit 409 abweisen |
| `POST /api/projects/{id}/assets` | Streaming-Import, Rolle, technische Vorprüfung, sichere Asset-ID |
| `GET /api/assets/{id}` | Metadaten/Herkunft; Server prüft Projektzuordnung |
| `GET /api/assets/{id}/peaks` | vorberechnete Peaks, Dauer, Auflösung |
| `GET /api/assets/{id}/audio` | erlaubte Datei, HEAD/Range/206/416; kein frei übergebener Dateipfad |
| `POST /api/assets/{id}/previews` | begrenzte Vorschau aus Bereich + konkretem Run-/Parameterbezug |
| `POST /api/projects/{id}/runs/validate` | Typen, Parameter, Speicher, Verfügbarkeit, Ausführungsort und bekannte Risiken prüfen; startet keine Modelle |
| `POST /api/projects/{id}/runs` | unveränderlicher Auftrag, Idempotency-Key, 202 + Run-/Job-IDs |
| `GET /api/runs/{id}` / `GET /api/jobs/{id}` | bestätigter Zustand, echte Phase, Teilergebnisse und erlaubte Folgeaktionen |
| `POST /api/jobs/{id}/cancel` | dauerhafte Abbruchanforderung; nur konkrete eigene Arbeit |
| `POST /api/projects/{id}/exports` | geprüften Export aus konkreten Versionen erstellen |
| `GET /api/exports/{id}` / `/download` | Status bzw. geprüftes Paket; keine fremden Pfade |
| `POST /api/projects/import-package` | versioniertes Projektpaket, sichere ZIP-/Quotenprüfung |

Einheitliche Fehler: `code`, verständliche Meldung, ob Wiederholen sicher ist, Job-/Request-ID und gegebenenfalls feldbezogene Fehler. Keine Tokens, Vollpfade, Stacktraces oder fremden Dateien als Benutzerfehlermeldung. `401/403` Auth/Sicherheitsfehler, `409` Konflikt/unklarer identischer Auftrag, `413` Limit, `422` Parameter, `503` fehlende Fähigkeit; nicht alles in pauschales 500 umwandeln.

### 9.4 Beispiel eines eingefrorenen Run-Auftrags

```json
{
  "project_id": "project-uuid",
  "draft_revision": 12,
  "idempotency_key": "new-request-uuid",
  "steps": [
    {
      "id": "stretch-vocal",
      "operation": "time_pitch",
      "inputs": [{"asset_id": "vocal-asset-uuid", "sha256": "content-hash"}],
      "region": null,
      "parameters": {"source_bpm": 123, "target_bpm": 128, "semitones": 2},
      "engine": "rubberband",
      "engine_version": "resolved-pinned-version"
    }
  ]
}
```

Server ergänzt verifizierte Hashes, Model-/Codeversion, tatsächliche Defaults und Seed; Werte aus dem Browser nicht als Beweis übernehmen. Derselbe Idempotency-Key mit anderem Request-Hash ergibt 409. Gleiche Inhalte als neuer bewusster Run sind zulässig, können aber verfügbare identische Artefakte wiederverwenden.

## 10. Audiotransfer und große Dateien

### 10.1 Ein konkretes heutiges Limit zuerst beseitigen

Die alten Handler erlauben je nach Werkzeug 50/100 MB und übergeben komplette `audio_data`-Bytes an `.spawn()`. Die Modal-Webgrenze und das SDK-/gRPC-Argumentlimit sind unterschiedliche Dinge. Laut aktueller Primärdokumentation können Web-Bodies bis 4 GiB, SDK-Payloads dagegen nur etwa 100 MB groß sein; das ist kein nutzbares Versprechen für einen 512-MB-Bytes-Parameter.

**Ziel:** Neue Workspace-Aufträge übertragen keine großen Audiodateien als Function-Argument. Eine geschützte Upload-Session schreibt kontrollierte Teile in einen privaten Staging-Cache. Nach vollständiger Größen-/Hashprüfung und bestätigtem Commit startet der Worker mit einer intern validierten Asset-Referenz.

### 10.2 Transfervertrag

1. Lokaler Import ist bereits abgeschlossen und gehasht; Original bleibt lokal.
2. Bei tatsächlich benötigtem Cloud-Schritt Upload-Session mit Projekt-/Asset-/Requestbezug anlegen.
3. Als Startwert 8-MiB-Teile mit Index, Länge und Hash übertragen; bestätigter Fortschritt zählt nur nach dauerhafter Speicherung. Gleicher Teil/Hash ist idempotent, anderer Inhalt am selben Index ein Konflikt.
4. Unterbrechung ermittelt bestätigte Teile und setzt fort; keine vollständige blinde Wiederholung. Upload ist ein eigener Zustand, noch kein GPU-Run.
5. Abschluss prüft Gesamtgröße/Hash, erstellt gültiges Inputmanifest und committed eine Ready-Markierung.
6. Modell-Worker lädt den Stand neu, prüft Manifest/Projekt/Hash und öffnet nur diesen freigegebenen internen Pfad.
7. Ergebnisse werden nach vollständiger Speicherung angemeldet, lokal übertragen, nachgeprüft und als neue Assets committed. Erst dann ist ein lokaler Download/Cache-Bezug bestätigt.

Die vorhandenen Volumes/Jobs nicht pauschal löschen oder umbauen. Neuer Cache liegt in einem klar abgegrenzten Namespace, vorzugsweise einem eigenen begrenzten Modal-Volume für den Workspace. Keine Migration fremder Apps/Volumes. Dateinamen und Asset-IDs bestimmen niemals frei einen Cloud-Zielpfad.

Das gemeinsame Staging-Volume ausdrücklich an **jede empfangende ASGI-Funktion und jeden konsumierenden CPU-/GPU-Worker aller beteiligten Apps** mounten. Die heute getrennten App-Volumes erfüllen diese Bedingung nicht automatisch. `input_ref` enthält nur serverseitig auflösbare Upload-/Asset-ID, Namespace und Hash; niemals einen vom Client bestimmten absoluten Pfad.

Teile werden unveränderlich pro Index und Hash gespeichert; keine parallel appendende gemeinsame Audiodatei. Genau ein Finalize-Schreiber prüft alle Teile und den Vollhash, erstellt die Zieldatei und das READY-Manifest und bestätigt erst nach nachgewiesenem Commit. Unbestätigte oder unterbrochene Commits gelten nicht als empfangene Teile. Worker lesen erst nach passendem Reload und gültigem READY-Beleg.

8 MiB ist der anfängliche Chunk-Startwert für geeignete Verbindungen. Für langsame Netze eine kleinere feste Session-Teilgröße zwischen 256 KiB und 8 MiB aushandeln; die Größe einer bestehenden Session nicht still ändern. Geänderte Upload-Sessions sind noch keine neuen Compute-Aufträge.

API-Calls sollen kurz bleiben; Uploadteile und Start/Status getrennt halten. Keine langen GPU-Aufgaben innerhalb eines einzelnen Web-Requests oder automatische Weiterleitung privater Header an Redirect-Ziele. Die belegte HTTP-Zeitgrenze liegt bei 150 Sekunden; vorhandene lokale 120-Sekunden-Timeouts ebenfalls bewusst behandeln.

### 10.3 Konservative, konfigurierbare Produktgrenzen

Anfangswerte, die in Phase 0 mit tatsächlichem Platz/Material überprüft und im Capability-Interface veröffentlicht werden:

- Lokal höchstens 512 MiB pro Audiofile, 30 Minuten, Mono/Stereo im Basispfad; maximal 2 GiB pro Importbatch.
- Standardmäßig ein schwerer lokaler DSP-Job und ein GPU-Modelljob gleichzeitig. Variantenbatch maximal drei, sequenziell.
- Lokales Workspace-Budget zunächst 5 GiB, Vorschaucache 1 GiB, mindestens 2 GiB freier Plattenplatz als harte Reserve. Bei größerem Bedarf bewusst ändern, nicht alte Nutzerdateien selbständig entfernen.
- Vor einem Run benötigten Platz für Eingänge, temporäre Render, mehrere Stems und finalen ZIP abschätzen. Bei zu wenig Platz **vor** kostenpflichtiger Modellarbeit blockieren.
- Vorschauen bevorzugt etwa 15–30 Sekunden; lange Vollrenders nur bewusst. Keine automatische Segmentierung von Musik durch Modelle, deren Überlappungs-/Stitch-Verhalten nicht geprüft ist.
- Im neuen Cloud-Namespace zunächst maximal zwei aktive Upload-Sessions, zusammen höchstens 2 GiB Input-Staging und höchstens 8 GiB Ergebnis-/Arbeitsdateien. Reservierungen vor Aufnahme/Spawn prüfen; diese Quoten betreffen ausschließlich dieses Projekt, nicht andere Workspace-Daten.
- Verwaiste unvollständige Uploads nach einer Stunde ohne bestätigte Aktivität bereinigen, aktive bestätigte Transfers nicht abbrechen. Erfolgreiche Input-/Ergebnisspeicherung folgt der gesonderten Job-Retention. Cleanup und Quoten sind tatsächlich zu implementieren und zu testen.
- Vor GPU-Start zusätzlich die **decodierte** Sample-/Kanal-/Dauer-/Byteausdehnung prüfen. Ein kleines komprimiertes File darf keinen unbegrenzten Decode-/Temp-Speicherverbrauch auslösen.

Grenzwerte sind Planvorgaben, keine bereits gemessenen Leistungsdaten. Falls ein konkretes Modell engere Grenzen benötigt, vor Start verständlich darstellen und keine verlustbehaftete Verkleinerung verstecken.

## 11. Jobsteuerung, Idempotenz, Abbruch und Recovery

### 11.1 Ein verantwortlicher Scheduler

SQLite speichert die lokale Queue. Genau ein Dispatcher claimt Arbeit transaktional; mehrere Uvicorn-Prozesse dürfen nicht jeweils einen Scheduler starten. CPU-Arbeit in separaten begrenzten Prozessen, nicht im ASGI-Eventloop. Polling/Netzwerkbeobachtung blockiert nicht den CPU-Worker. Kleine Housekeeping-Aufgaben dürfen BackgroundTasks verwenden; die Renderqueue darf nicht allein daraus bestehen.

Lokale wiederholte Anforderung erzeugt eine bekannte Run-/Job-ID. Prozessneustart fragt bekannte Remote-Jobs ab und behandelt lokale abgebrochene Prozesse konservativ. Browser-Refresh erzeugt nur Leseanfragen.

### 11.2 Zustände und erlaubte Übergänge

```text
draft → validating → queued → transferring → submitting → remote_queued/running
                                  │              │                 │
                                  │              └→ submission_unknown
                                  └→ failed/cancelled               │
running → finalizing → completed / partial / failed / output_unconfirmed
beliebiger aktiver Zustand → cancel_requested → cancelled ODER bereits completed
```

`blocked`, `reserved`, `submission_unknown`, `output_unconfirmed`, `offline` und `cancel_requested` sind reale Zustände mit passenden Benutzeraktionen. Ein Abbruchklick ist kein Beweis eines beendeten GPU-Jobs. Teilweise Transkription hat erfolgreiche und fehlgeschlagene Zweige; gezieltes Wiederholen startet nur ausgewählte fehlende Arbeit.

Progress ist phasenbezogen: Import, Transfer, Warten, Modell, Vorschau, Resultatprüfung. Wo kein verlässlicher Fortschritt vorliegt, unbestimmte Anzeige statt erfundener Prozent-/ETA-Werte. Vorliegende Laufzeiten können als historische Beobachtung mit Kontext angezeigt werden.

### 11.3 Entfernte Idempotenz ohne falsches Exactly-once-Versprechen

- Neue geschützte Startinterfaces akzeptieren eine vom lokalen Backend erzeugte Request-/Job-UUID und einen kanonischen Request-Hash.
- Atomarer Claim, beispielsweise `Modal.Dict.put(..., skip_if_exists=True)`, verhindert paralleles Starten für einen noch vorhandenen Claim. Request, Claim, Ausführung und Ergebnis bleiben trotzdem getrennte Vorgänge.
- Request-Identität, Hash, Modell-/Parameterversion und dauerhafte Submit-/Start-/Resultatbelege zusätzlich im geschützten Namespace festhalten. Dict-Einträge verfallen nach sieben Tagen ohne Zugriff; sie sind kein dauerhaftes Projektarchiv.
- `.spawn()`-Handle/Call-ID serverseitig speichern. Der Worker registriert beim tatsächlichen Start zusätzlich seine eigene `current_function_call_id()` als Recovery-Beleg, bevor DSP beginnt.
- Keine konkurrierenden Writer überschreiben dieselbe mutable Statusdatei. Vorzugsweise getrennte immutable Submit-, Worker-start-, Cancel- und Resultatbelege plus ein daraus abgeleiteter Status. Volume-Commit ist kein verteilter Lock.
- Die Erfolgsantwort darf erst eine zugesicherte Zuordnung behaupten, wenn deren Beleg dauerhaft vorliegt. Terminale Resultate werden nicht durch später eintreffende „queued“-Meldungen überschrieben.

| Ausfallfenster | Behandlung |
| --- | --- |
| Claim gespeichert, Spawn noch nicht erfolgt | `reserved`; prüfen, nicht per kurzer Lease einen zweiten Start erlauben |
| Spawn möglicherweise angenommen, Bestätigung/Call-ID verloren | `submission_unknown`; bekannte Request-ID/Workerbelege abgleichen, keine automatische neue GPU-Ausführung |
| Worker fertig, Ergebnisse noch nicht bestätigt committed | `output_unconfirmed`; Artefakte prüfen/übernehmen, nicht sofort neu rendern |
| Alter Claim abgelaufen, historische UUID ohne eindeutigen Beleg | fail-closed bzw. bewusste manuelle Auflösung; kein „Dict leer heißt nie gelaufen“ |
| Identische UUID, anderer Inhalt | 409, keine Arbeit |
| Browser/Client wiederholt bestätigte Anforderung | dieselbe Job-/Resultatreferenz zurückgeben |

Versprechbar ist ein konservativer Schutz vor automatischen Doppelstarts bei unklarer Bestätigung. **Garantierte Exactly-once-GPU-Ausführung ist mit Claim, Spawn und Volume nicht belegt.** Bei nicht auflösbarer Unsicherheit darf der Job bis zur bewussten Entscheidung blockiert bleiben.

### 11.4 Gezielter Abbruch

Abbruchanforderung zuerst dauerhaft speichern, auch wenn die Call-ID noch fehlt. Worker prüft sie beim Start und vor Folgestufen. Lokale Prozesse mit eigener Prozessgruppe stoppen; keine globalen FFmpeg-/Python-Prozesse beenden.

Entfernter Abbruch erfolgt über eine geschützte Modal-Route, die eigene Geschäftsjob-ID → Call-ID auflöst. Kein beliebiger `call_id` aus dem Browser, kein kompletter Modal-API-Key auf dem Mac als neue Laufzeitpflicht. Der Gateway darf `.cancel()` nur für zugeordnete eigene Arbeit aufrufen.

`terminate_containers=True` nicht pauschal benutzen; es kann andere Inputs treffen. Falls eine isolierte Ausführung wirklich Containerabbruch benötigt, Isolation und Wirkung vorab testen. Ein spät erfolgreicher Job und eine Abbruchanforderung haben eine klare Prioritätsregel: bestätigte vollständige Ergebnisse können als „vor Abbruch fertig“ erhalten bleiben; Nachfolger starten nach angefordertem Abbruch nicht mehr automatisch.

### 11.5 Retry und Versionscache

GET-Status/Transferteile dürfen begrenzt mit Backoff wiederholt werden. POST-Starts nur mit denselben Identitäten und dem entfernten Idempotenzvertrag; niemals generisches automatisches Retry mit neuer UUID.

Cache-Schlüssel enthält Eingangsinhalte, Region/Offsets, geordnete Operationen, kanonische Parameter, Engine-/Code-/Checkpoint-Version, Outputrate/-kanäle und Seed. Ein Cachetreffer wird erst nach Artefakt-/Hashprüfung verwendet. Nach Änderungen nur betroffene Nachfolger neu berechnen. Keine Cross-Project-Ausgabe ohne geprüftes Eigentum/Referenzmodell.

## 12. Zentraler Player, Vorschauen und Speicher

- Ein AudioContext und eine gemeinsame Transportzeit. Quellen an derselben Clock planen, nicht nacheinander per mehreren `audio.play()` starten.
- Langdateien erhalten Peaks und streambare Einzelvorschauen. Multitrack-/Regionshören arbeitet mit begrenzten vorbereiteten Audiofenstern; kein komplettes Songprojekt gleichzeitig als viele Float32-Buffer laden.
- Ziel für decodiertes Audiomaterial zunächst höchstens 128 MiB im Browser. Fensterlänge/Prefetch dynamisch aus Kanalzahl, Rate und aktiven Quellen berechnen; alte Buffer und Object-URLs freigeben. Das ist ein zu prüfendes Budget, kein bereits erreichter Messwert.
- Vorbereitete Auswahlen nutzen dieselbe Zeitreferenz; Seek kann kurz auf nötige Daten warten. Dabei sichtbarer Ladezustand statt vorlaufendem falschem Playhead. Übergänge an Fenstergrenzen prüfen.
- WaveSurfer benutzt vorhandene Peaks/Dauer und ist an den zentralen Transport gebunden. Falls die konkrete Version nicht sauber entkoppelbar ist, kleine eigene Peaks-Darstellung wählen statt zwei Audiozustände synchronisieren zu wollen.
- A/B mit kurzem clickfreiem Übergang, passender Inhaltszeit und getrenntem Monitor-Pegel. Schnitte/Stretch benötigen Time-Mapping; normale Stereoassets bleiben normale Stereoassets.
- Effekte werden für Vorschau und Export mit derselben DSP-Kette gerendert. Debounce nur für lokale, begrenzte Vorschau; GPU-Aufrufe ausschließlich durch eine ausdrückliche Render-/Generierungsaktion.
- Neue Presets/Parameter machen eine alte Vorschau sichtbar veraltet. „Aktuelle Vorschau“ bezieht sich auf einen konkreten Parameter-Hash.
- Schnelle Auswahlprobe und verbindliche Ergebnisvorschau klar unterscheiden. Preroll, Tail und ein gemeinsamer eingefrorener Analysezustand gehören zum Preview-Vertrag; ein Vollmix-Mastering darf nicht ohne Hinweis nur aus der Statistik des Ausschnitts abgeleitet werden.
- Browserpause, Hintergrundtab, Sleep/Resume und AudioContext-Suspend behandeln. Tastendruck und App-Jobstatus dürfen nicht verwechseln, ob gerade Audio oder Compute läuft.
- Audio-/Download-Interfaces müssen Range/206/Content-Range/416 korrekt behandeln; keine gesamte Datei trotz Range als vermeintlich partiellen Body deklarieren.

## 13. Sicherheit, Privatsphäre und Datenlebenszyklus

### 13.1 Unverhandelbare Invarianten

1. Jede bestehende und neue Modal-Webroute bleibt mit `requires_proxy_auth=True` geschützt, einschließlich Health, Upload, Status, Cancel, Vorschau und Download.
2. Token bleibt außerhalb des Repos, aktuell `~/.config/dreamtelligence-xo/modal.json`, Rechte 600. Kein `VITE_*`-Secret, kein Token im HTML, localStorage, Querystring, Source-Map, Export, Log oder Screenshot.
3. Ohne Konfiguration kein Modal-Zugriff, auch nach UI-Umbau. Ein öffentlicher Fork erhält keine funktionsfähigen Betreiberzugänge.
4. Laufzeitserver bindet nur Loopback. Host-/Origin-/Fetch-Site-Prüfung übernehmen und für neue Mutationen durch serverseitigen CSRF-/Sessionbezug ergänzen; normale Browserclients benötigen keine Login-Oberfläche.
5. Entwicklungs-Origin nur bei ausdrücklichem Dev-Modus, exakte Host/Port-Zuordnung; kein pauschales `Access-Control-Allow-Origin: *` als Reparatur.
6. Kein öffentlich erreichbarer anonymer Same-Origin-Proxy auf Vercel. Ein späterer öffentlicher Dienst braucht einen eigenständigen Auth-/Autorisierungs-/Quota-/Datenschutzplan.

### 13.2 Verarbeitung und Dateisicherheit

- Jede Asset-/Job-/Exportoperation prüft Projektbezug. UUID allein ist keine Berechtigung, auch wenn die erste Version nur einen lokalen Benutzer hat.
- Keine frei wählbaren Cloud-URLs, Modell-Downloads oder Dateipfade aus Browserrequests. Modellregistrierung und Upstreams sind serverseitig erlaubte, gepinnte Konfiguration.
- Uploadgröße, tatsächlicher Audioinhalt, Dauer, Kanäle, Ausgabegröße und Speicherbedarf serverseitig begrenzen. FFmpeg/CLI-Argumente als Listen, kein `shell=True` oder Zusammenbauen aus untrusted Strings.
- Demuxer-/Protokollzugriffe beschränken; keine indirekten URL-/Playlist-/Concat-Zugriffe auf beliebige lokale/entfernte Dateien. Nur validierte private Inputdateien verarbeiten.
- Projekt-ZIP-Import gegen Pfadtraversal, Symlinks, Zip-Bombs, Überzahl/Übergröße, Hash- und Schemakonflikte schützen. Extrahieren nur in isoliertes temporäres Verzeichnis, erst nach Prüfung übernehmen.
- Statische Auslieferung ausschließlich aus Build-Verzeichnis/erlaubten Assets. Keine `.git`, `.env`, Konfiguration, Datenbank, Originalaudios oder Arbeitsverzeichnisse über einen generischen Static-Mount.
- Skripte/Fonts bündeln; CSP nach Umbau ohne Inline-JavaScript bzw. fremde Script-CDNs. Erforderliche dynamische Styles eng dokumentieren; kein Stripe-/Supabase-SDK laden.

### 13.3 Lokale und entfernte Aufbewahrung

Private Daten unter einem eigenen Benutzer-Datenverzeichnis, z.B. `~/Library/Application Support/Dreamtelligence XO/`; Cache getrennt, nicht auf Desktop/Repo. Verzeichnisrechte restriktiv setzen. Projektbackup als tatsächlicher konsistenter SQLite-Snapshot plus referenzierte Assets, mit Wiederherstellungstest.

Originale werden nicht automatisch gelöscht. Vorschauen/Cache dürfen nur nach belegter Unbenutztheit und dokumentierter LRU-/Größenregel entfernt werden. Laufende Jobs und nicht gesicherte Ergebnisse sind geschützt. Das UI zeigt Cachegröße und kontrollierte Bereinigung.

Cloud-Staging und Ausgaben erhalten eine getestete Retention: beispielsweise nach lokaler verifizierter Übernahme und spätestens 24 Stunden nach terminalem Job, sofern nicht anders konfiguriert. Das ist erst eine Zusage, wenn Cleanup tatsächlich existiert, läuft und fehlschlagende Löschung sichtbar wird. Noch laufende/unklare Jobs nicht blind löschen. Alte bestehende Jobdateien nie pauschal als Teil dieser Migration beseitigen.

Die Upload-/Cloud-Speicherquoten aus §10.3 gelten zusätzlich zur lokalen Quote. Kleine dauerhafte Identitäts-/Submit-/Resultatbelege separat von löschbaren Audiodateien halten, damit Audio-Retention nicht versehentlich den Idempotenzbezug löscht. Entfernte Audiodaten können ablaufen, während das geprüfte lokale Projekt weiter benutzbar bleibt; fehlende Remote-Dateien dürfen keinen automatischen Neurender auslösen.

Kein EU-only-, DSGVO-Konformitäts-, Trainings- oder 24h-Löschversprechen aus alten Texten übernehmen, solange es nicht für den tatsächlichen Betrieb belegt ist. „Lokal“ und „Cloud“ dürfen als Entscheidungshilfe sichtbar sein; interne Container-/FastAPI-Details gehören nicht in den normalen Künstlerablauf.

### 13.4 Grenzen der Garantie

Gültige Workspace-/Proxy-Zugangsdaten und lokale Kontozugriffe bleiben berechtigt bzw. sicherheitsrelevant. Der neue Schutz verhindert die Nutzung **allein durch einen Clone**, nicht den Missbrauch eines absichtlich weitergegebenen Tokens oder eines kompromittierten Mac-Benutzerkontos. Bestehende fremde Modal-Apps, globale Spend-Limits, Workspace-Mitglieder, Stripe-Abos und andere Projekte nicht verändern.

## 14. Modell-, Lizenz- und Verfügbarkeitsregister

Vor einer Integration Code, Binär-Build und konkrete Gewichte getrennt dokumentieren: URL, Version/Commit, SHA256, Lizenz, angenommene Bedingungen, freigegebener Nutzungsfall, Engine-Image und Status. Keine pauschale Aussage „alles Open Source, also kommerziell frei“.

| Baustein | Recherchierter Ausgangspunkt | Umsetzungsregel |
| --- | --- | --- |
| librosa | ISC für die DSP-Bibliothek | Exakte Version/Notice festhalten; keine Gewichte für Onset-Schnitt nötig |
| FFmpeg | LGPL/GPL abhängig vom Build | Tatsächliche Buildoptionen und Filter prüfen; nicht nur Paketnamen notieren |
| Pedalboard | GPLv3, weitere gebündelte Abhängigkeiten | Vorhandene Nutzung inventarisieren; keine beliebigen Fremd-Plug-ins ohne eigene Lizenz-/Linux-Prüfung |
| Rubber Band | GPLv2 oder später; Anbieter bietet kommerzielle Lizenz für andere Verteilungsbedingungen | Privaten Betrieb und spätere Verteilung getrennt behandeln; keine Lizenz automatisch kaufen |
| Matchering | GPLv3 | Bibliothek wirklich integrieren und Lizenz-/Quellenpflichten für die gewählte Verpackung prüfen |
| Basic Pitch | Apache-2.0 im Repository | Gewähltes Modellformat/Artefakt/Runtime pinnen und Paketabhängigkeiten testen |
| DeepFilterNet | Maintainer-Klarstellung: Code und Repository-Gewichte MIT/Apache-2.0 | Konkretes Artefakt und dazugehörigen Lizenzbeleg erfassen |
| RNNoise | BSD-3-Clause für Code | Gewählte Modell-/Binary-Artefakte separat erfassen |
| AudioSR | Code MIT; originaler Basic-Checkpoint als Apache-2.0 markiert | Basic-Pfad integrieren, keinen Speech-Checkpoint ohne sichtbare klare Lizenz übernehmen |
| MuScriptor large | CC BY-NC 4.0 + Modellbedingungen | Für kommerzielle Projekte nicht einfach als freigegeben behandeln; alternative Engine anbieten |
| Stable Audio Open 1.0 | Eigene Stable-Audio-Community-Lizenz | Aktuelle Modellbedingungen lesen, keine vereinfachte Umsatz-/Noncommercial-Zeile als alleinigen Rechtsnachweis verwenden |
| SCNet/Mel-Band/MossFormer/Whisper/AST/beat_this/essentia/Soundfonts | Bestehende technische Nutzung, keine vollständige Freigabe aus dieser Planung | Code-/Checkpoint-/Samplelizenz und Zweck einzeln erfassen; essencias tatsächlichen Lizenzumfang ebenfalls prüfen |

Projekt bekommt einen vorgesehenen Nutzungsfall, z.B. privates Experiment oder Veröffentlichung/kommerzielles Projekt. Die Engine-Auswahl erklärt tatsächliche Einschränkungen und verhindert unzulässige automatische Verarbeitung. Der private Testmodus dieser ersten App ist keine allgemeine Freigabe für jede spätere Künstlerveröffentlichung.

Fehlende Setup-/Lizenzfreigabe ist ein klarer Zustand mit erklärtem Grund. Sie ist kein Anlass, heimlich ein anderes Modell oder einen bezahlten Anbieter zu verwenden. Falls eine konkrete Engine rechtlich nicht verfügbar gemacht werden kann, Grund belegen und Freigabe/Alternative klären; keine fertige Funktion vortäuschen.

Das Projekt-MIT-Label muss vor einer Weiterverteilung gegen tatsächlich kombinierte GPL-/Modellbestandteile geprüft werden. Eine Prozessgrenze allein ist keine pauschale rechtliche Freistellung.

## 15. Umsetzungspakete mit verbindlichen Ergebnissen

Die Reihenfolge ist der Standard. Nach jedem Paket realen Pfad prüfen, Fehler korrigieren und Status dokumentieren; keine Sammlung ungeprüfter Oberflächen produzieren. Die Größen S/M/L sind relative Aufwands-/Risikoklassen, keine zugesagten Arbeitstage.

| ID | Paket / Größe | Abhängigkeit | Konkretes Ergebnis und Austrittskriterium |
| --- | --- | --- | --- |
| P0 | Ausgangsstand, Modelle und Grenzen · M | keine | Dirty/untracked Stand vollständig erfassen und sichern; Tests reproduzieren; Lizenz-/Modell-/Paketregister, Platzbedarf, echte Limits und Baseline festhalten. Kein Verlust des privaten Schutzes. |
| P1 | Projekt-/Asset-Fundament · L | P0 | Lokales Backend, SQLite-Migration, privater Dateispeicher, sicherer Import, Peaks, Projektliste, Capability-/Session-Interface. Import → Browserreload → Original/Metadaten wiederfinden real funktionsfähig. |
| P2 | Verlässliche entfernte Arbeit · L | P1 | Geschützte Upload-Sessions, Asset-Referenzen statt großer RPC-Bytes, Job-/Call-ID-Belege, Status-/Cancel-/Idempotenzvertrag für fünf Apps. Doppelklick und Timeout nach möglichem Spawn starten nicht automatisch zweimal. |
| P3 | Neue Arbeitsfläche und vorhandene Operatoren · L | P1/P2 | React-Workspace mit Bibliothek, gemeinsamen Spuren, Inspektor, Transport und Aufgaben; bestehende Separation, Auto-Mastering, MIDI und Sprache über echte Adapter bedienbar. Cloud-Ergebnis ohne manuelles Re-Upload direkt übernehmen. |
| P4 | Gemeinsame Bearbeitungsfolge und Varianten · L | P3 | Validierter Run-Graph, Entwürfe/Snapshots, Herkunft, Undo von Edits, Vergleich und Cache-Invalidierung. Änderung eines Nachfolgers nutzt vorhandene Vorstufen weiter. |
| P5 | Analyse, Beat-Grid und Sample-Labor · L | P4 | Technische QA, Musik-Analyse, manuelle Grid-Korrektur, Loop-/One-Shot-Vorschläge mit hörbarer Grenzkorrektur und tatsächlichen WAV-Exporten. |
| P6 | Rubber Band · M/L | P4/P5 | Tempo/Pitch für Einzelclip und Gruppe, Auswahlvorschau, Vollrender, synchrones Ergebnis und Zeitmapping. Stereo-/Mehrspur-/MIDI-Zeittests bestehen. |
| P7 | MIDI-Workbench und Basic Pitch · L | P4/P5 | Bestehender Tempoexport korrigiert; zweiter MIDI-Weg, Piano-Roll/Drumansicht, begrenzte Notenedits, richtige Tempo-/Takt-/Regionsausgabe. Tatsächlicher DAW-Import mit nicht-120-BPM-Datei geprüft. |
| P8 | Pedalboard-Ketten und Remix-Bounce · L | P4/P6 | Bedienbare Effekte, Reihenfolge/Bypass, konsistente Vorschau/Vollausgabe, Tail-Regeln, einfacher Mixer und Stereo-Bounce. Kein neuer GPU-Job für Effektslider. |
| P9 | Referenz-Mastering und finaler Audio-Check · M/L | P4/P8 | Matchering wirklich integriert; Referenz auswählen, Render vergleichen, finale QA nach gewähltem Exportformat. Bestehender Automodus bleibt nutzbar. |
| P10 | Sprach-Workbench · L | P4/P8 | Auswahl MossFormer/DeepFilterNet/RNNoise, Vorschläge für Füllwörter/Pausen/Störsegmente, bestätigbare EDL-Schnitte, Zeitmapping und korrektes A/B. Original erhalten, Stereo-/Raw-Formatfälle geprüft. |
| P11 | Sound-Generierung und AudioSR · L | P4/P2 | Bestehende Stable-Audio-API vollständig bedienbar; Seeds/Takes/Übernahme. AudioSR-Basic als bewusstes Experiment mit Originalerhalt und Lizenz-/Modellbezug. Jede sichtbare Aktion erzeugt ein reales geprüftes Ergebnis. |
| P12 | DAW-Pakete, Batch und Projektpakete · L | P5–P11 | Exportkorb über Zweige hinweg, ausgerichtete WAVs, MIDI, Loop-/Samplepakete und Manifest; sichere Projektpaket-Wiederherstellung. Batchgrenzen und gezielter Teilretry funktionieren. |
| P13 | Vollabnahme, Migration und Betrieb · L | P0–P12 | Feature-/Sicherheits-/Browser-/DSP-/Recovery-Matrix vollständig belegen, relevante Hörvergleiche und lange Dateien prüfen, dokumentierten Normalstart und Rollback übergeben. Nur dann neue UI zum Standard machen. |

### 15.1 Zuerst ein vollständiger vertikaler Pfad

Während P1–P4 nicht zunächst sämtliche Toolpanels dekorieren. Zuerst **Projekt → Import → echte Separation → auswählbarer Stem → einfache verlustfreie Auswahl → Vorschau → WAV-Export → Reload/Projektwiederaufnahme** bauen. Dabei das endgültige Asset-/Job-/Sicherheitsmodell benutzen. Danach vorhandene Operatoren und die Erweiterungen an denselben Interfaces ergänzen.

Diese erste Strecke ist ein Architektur-/Integrationsnachweis, keine Reduzierung des Gesamtauftrags. P5–P13 bleiben verpflichtend.

### 15.2 Erwartete spätere Änderungen an vorhandenen Dateien

- `dev_server.py`: kompatibler Launcher/Entrypoint für die neue lokale App; Dateirechte, Loopback, Fehlerfälle und private Konfiguration bewahren. Neue Hauptimplementation unter `studio/`.
- `index.html` / `dreamtelligence-redesign.css`: aktuellen geschützten Bestand als Legacy erhalten; neue UI unter `web/`, keine weitere riesige Inline-Erweiterung.
- `modal_app_zfturbo_complete.py`: Referenz-Input, Vollständigkeit/Alignierung, Idempotenz/Call-ID/Cancel und gegebenenfalls kohärenter Stemgruppenmodus.
- `modal_app_matchering.py`: Legacy-Automatik erhalten, gemeinsamen DSP-Code verwenden, echter Referenzmodus; große Eingänge per Asset-Referenz.
- `modal_app_transcription.py`: Tempo-/MIDI-Korrektur, Basic-Pitch-/Analyse-Entrypoints nach tatsächlichem Bedarf, getrennte Ergebnisse/Partial-Status.
- `modal_app_enhancement.py`: Inputreferenz, getrennte Noise-Engines, EDL/Zeitmapping, A/B-Artefakte, keine zwingende GPU-Initialisierung bei CPU-Modi.
- `modal_app_audio_generation.py`: stabile Jobidentitäten, UI-kompatible Capabilities/Seeds, neuer isolierter AudioSR-Pfad mit passenden Images. Existierenden Generator nicht durch unklare neue Abhängigkeiten destabilisieren.
- `api/*.js` / `disabled/`: Commerce-410 und Archiv erhalten. Kein neuer öffentlicher Compute-Proxy in diese Vercel-Handler.
- `package.json`, Lockfiles, Python-Projektdateien: neue Start-/Build-/Testwege, alte Manifestdaten archiviert. Tatsächliche Lizenzen und Branding korrigieren.
- `vercel.json`: keinen ungesicherten Backendpfad veröffentlichen. Falls später nur ein statischer Viewer publiziert wird, er hat keine Betreiberzugänge und muss ohne Backend ehrlich „nicht eingerichtet“ anzeigen.
- `tests/test_private_mode.py`: Sicherheitsziele erhalten; bei Frameworkwechsel an passender Stelle migrieren und erweitern. Nicht löschen, weil die neue App ein anderes Testwerkzeug verwendet.
- `README.md`, `docs/PRIVATE_MODE.md`, Architektur/Setup, ADRs und Verifikationsnachweise: gleichzeitig zum tatsächlichen Betriebsstand aktualisieren.

## 16. Test-, Qualitäts- und Abnahmeplan

### 16.1 Wiederverwendbare Fixtures

Kleine, deterministisch generierte Dateien für automatische Tests: Impulse an Anfang/Mitte/Ende; Stereo mit gleicher und gegenphasiger Komponente; feste Sinustöne; Transienten/Drumsequenz; 90/123/150 BPM; 3/4 und 6/8; variable Tempoabschnitte; Stille, NaN/Inf-korruptes Float-WAV, sehr kurzer Clip, Intersample-Peak-Beispiel und Hall-/Delay-Impuls.

Zusätzlich reale, rechtmäßig nutzbare Materialtypen für Hör-/Modellevaluation: dichter Songmix, isolierte Vocals/Bass/Drums, trockene und verrauschte deutsche/englische Sprache, Aufnahme mit Hall, bandbegrenztes Audio und verlustbehaftete MP3. Quellen/Nutzungsrechte festhalten; keine beliebigen fremden Songs ins Repository oder in Cloudtests laden.

Automatische Tests verwenden keine heimlich kostenpflichtigen Modellaufrufe. Ein klar getrennter, expliziter Live-Testlauf nutzt den bestehenden privaten Zugang, begrenzte kurze Fixtures und nachweisbar echte Verarbeitung. Unit-Mocks prüfen Ausfallfenster/Logik, ersetzen aber diesen Live-Nachweis nicht.

### 16.2 Funktions- und Fehlerfallmatrix

| ID | Prüfung | Abnahmekriterium |
| --- | --- | --- |
| T01 | Clone ohne Konfiguration | UI startet, kein Modal-Auftrag möglich, klare Setup-Anzeige, keine Betreiber-Credentials in Dateien/Bundle |
| T02 | Direktzugriff Cloud | Alle alten/neuen Health-, Start-, Upload-, Cancel-, Preview-/Downloadrouten ohne/falschen Token abgewiesen |
| T03 | Lokaler fremder Zugriff | DNS-Rebinding-/Host-/Origin-/Fetch-Site-/CSRF-Fälle scheitern; kein Request erreicht bezahlte Verarbeitung |
| T04 | Datei-/Projektisolation | Fremde Asset-ID, Pfadtraversal, Dotfile, Query-Manipulation, Symlink/ZIP-Traversal liefern keine Daten |
| T05 | Dauerhafter Import | Rename, Neustart und Browserreload erhalten Original, Hash, Metadaten und Verwendungen; defekter Import ist nicht halb sichtbar |
| T06 | Vollständige Separation | Alle angeforderten Ausgaben tatsächlich vorhanden; fehlende Spur ergibt partial/failed. Kanalzahl, Dauer und Startoffset gemessen |
| T07 | Region/Loop/Sample | Exklusive Endindizes, Start/Ende, kurze/leere/überlappende Regionen, Transienten/Fades und Release-Regeln stimmen |
| T08 | Tempo/Pitch | Gewähltes Zieltempo/Intervall messbar; Stereo-/Gruppensynchronität an Anfang/Mitte/Ende geprüft; keine ungeprüfte Phasenkohärenzbehauptung |
| T09 | MIDI | Tempo-/Takt-Events, Notendauer/-offset, Bend-/RPN-Regeln, ausgenommene Drums, Notenbereich, Regionclip und Audio/MIDI-Zielzeit stimmen bei nicht-120-BPM-Fixtures |
| T10 | Effekte | Geordnete/bypasste Kette, Chunkzustände, Reset pro Job, Preroll/Tails und gemeinsame Analyse korrekt; vorläufige Auswahlprobe von verbindlichem Ergebnis unterschieden |
| T11 | Mixer/Bounce | Gain/Pan/Mute/Solo, Clip-Offsets und gemeinsame Länge korrekt; Monitor-Gain verändert keinen Export |
| T12 | Mastering | Automatik und Reference erzeugen echte Varianten; unpassende Referenz ergibt Fehler/Hinweis; finale Messung auf quantisierter/encodierter Datei |
| T13 | QA | Sample-Peak nicht mit True Peak verwechselt; Stille/kurze Dateien korrekt „nicht messbar“; Zielverfehlung nicht als bestanden markiert |
| T14 | Sprache | Genau gewählter Denoiser, korrektes RNNoise-Format, EDL bestätigbar, A/B inhaltssynchron, kein Original-L/Ergebnis-R als gewöhnlicher Stereoexport |
| T15 | Generierung | Caps serverseitig, Seeds/Takes sichtbar, max. Varianten begrenzt, Ergebnisübernahme ohne manuelles Re-Upload |
| T16 | AudioSR | Original erhalten; Lowpass-/MP3-/Rausch-/Hallbeispiele getrennt gehört; schlechte Erweiterung verwerfbar, keine erlogene Reparaturbewertung |
| T17 | Job-Recovery | Doppelklick, Browserreload, Serverrestart, HTTP-Ack-Verlust und späte Resultate behandelt; kein automatisches neues GPU-Render bei unklarem Start |
| T18 | Cancel | Vor Start, während Upload, Remote-Queue, lokalem DSP, laufender GPU und finalisierendem Ergebnis geprüft; kein Stopp ganzer Apps/fremder Inputs |
| T19 | Cache/Varianten | Änderung nur eines Nachfolgers spart Vorstufen; inkompatibler Hash/Version wird nicht wiederverwendet; Original bleibt auswählbar |
| T20 | Export/DAW | Dateien technisch korrekt, gemeinsamen Spuren gleiche Zeitbasis, MIDI importierbar, Manifest vollständig, ZIP/Projektimport sicher und wiederherstellbar |
| T21 | Storage/Offline | Platzmangel vor Compute, Cachebereinigung, fehlendes Cloudresultat, Mac-Sleep und Netzwerkabbruch verständlich; keine automatischen Original-Löschungen |
| T22 | UI/A11y | Alle Primäraktionen sichtbar, Keyboard ohne Drag-Zwang, Fokus/Dialoge, Responsive/Zoom, ausreichend Kontrast; kein Autoplay |
| T23 | Deaktivierter Bestand | Keine aktive obere Navigation/Marketing-/Kauf-/Login-Flows, keine Stripe-/Supabase-SDK-Requests oder Credit-Schreibvorgänge |
| T24 | Build-/Secret-Schutz | Gebautes JS/CSS/Source-Maps/Export/Logs ohne Token, Versionpins vollständig, Image-Neubau für relevante Änderungen geprüft |

### 16.3 Browserprüfung und reale Künstlerabläufe

Brave/Chromium und Safari auf dem tatsächlichen Mac prüfen, nicht nur Chrome-Snapshots. Desktop mindestens 1440×900 und 1280×800, Tablet etwa 1024×768, schmal etwa 390×844; zusätzlich 200%-Zoom. Browserinstallation nur wenn tatsächlich nötig und autorisiert, keine wiederholten Installversuche statt vorhandener alternativer Oberfläche.

Folgende echte Ende-zu-Ende-Szenarien dokumentieren:

1. Song → Stems → Vocal-Tempo/Pitch → Loop + MIDI → ausgerichtetes DAW-Paket.
2. Drum-Stem → korrigierte One-Shots → Paket importieren und Treffer in einer DAW vorhören.
3. Mix + Referenz → Reference-Master → lautheitsangepasstes A/B → 24-Bit-WAV samt tatsächlicher True-Peak-Messung.
4. Sprachaufnahme → gewählter Noise-Filter → einzelne Schnittvorschläge bestätigen/zurücknehmen → korrekt zugeordnetes A/B → WAV.
5. Prompt → zwei begrenzte Takes → eine Variante übernehmen → Slice/Tempo → Export.
6. AudioSR-Auswahl → Original/Experiment hören → Experiment verwerfen bzw. als ausdrücklich gewählte Variante übernehmen.
7. Laufenden Job durch Browserreload/Serverrestart wiederfinden, gezielt abbrechen und ein anderes Projekt weiter bedienen.

Für die ersten Durchläufe klare Primäraktionen direkt aus der leeren Ansicht verfolgen. Ein Test, der interne Funktionen über die Konsole aufruft, belegt nicht die Auffindbarkeit für Künstler. Ein Download mit WAV-Header allein belegt keine musikalische Qualität.

DAW-Importtests in separaten temporären Testprojekten durchführen; keine bestehenden Sessions oder globalen Audio-/Plug-in-Einstellungen des Nutzers verändern. Ist eine Ziel-DAW nicht verfügbar, den fehlenden realen Importnachweis ausdrücklich offenlassen statt ihn aus einem formal korrekten MIDI-Header abzuleiten.

### 16.4 Leistungsziele und Messung

Zunächst Messbasis festhalten: Mac-Modell/CPU/RAM, Browser, Paket-/Image-/Modellversion, Clipdauer/-format und Warm-/Kaltzustand. Keine Hardware-Seriennummern oder privaten Audiodaten in öffentliche Reports.

Planungsziele zur Messung, nicht bereits erfüllte Zusagen:

- Alltägliche UI-Reaktion überwiegend unter 100–200 ms; schwere Arbeit blockiert weder Cursor noch Transportbedienung.
- Bereits vorbereitete Auswahl startet nach Benutzeraktion zügig; neue Render zeigen echte Warte-/Pufferzustände.
- Große Projektansicht lädt Peaks/Metadaten, nicht sämtliche unkomprimierten Quellen. Budget für decodiertes Audio durch Instrumentierung prüfen.
- Jobs messen Upload, Queue/Kaltstart, Modell, Render, Ergebnisübertragung und QA getrennt. Durchsatz/Kosten nicht aus einem synthetischen 8-Sekunden-Clip auf ganze Songs hochrechnen.
- Vor Freigabe mindestens mehrere kurze und mehrminütige Projekte prüfen; Cold/Warm und verfügbare Speichergrenzen getrennt berichten.

Wenn ein Ziel nicht erreicht wird, Ursache am gemeinsamen Modul beheben. Begründete Grenzwerte nach Messung anpassen und dokumentieren; keinen garantierten „Echtzeit“- oder Kostenclaim daraus machen.

## 17. Lizenz-/Sicherheits-/Qualitätsgates für „fertig“

Ein Arbeitspaket ist erst abgeschlossen, wenn die Funktion vom sichtbaren Einstieg bis zum tatsächlich nutzbaren Ergebnis durchgängig funktioniert. Für den vollständigen Auftrag zusätzlich:

- Jede angeforderte Funktion ist über ein echtes Werkzeug erreichbar und besitzt sinnvolle Defaults, validierte Parameter, passenden Eingangsbezug, Preview/Run-Status, Ergebnis und Export oder eine belegte externe Sperre.
- Keine dekorativen Regler, „kommt bald“-Buttons, synthetisch vorgetäuschten Erfolgszustände oder versteckten ungeschützten Ersatzendpunkte.
- Die beiden MIDI-Wege, drei Rauschfilter, beide Masteringmodi, Stable-Audio-Generierung und der zulässige AudioSR-Basic-Pfad sind jeweils im zulässigen Nutzungsprofil tatsächlich getestet; ein sichtbarer Capability-Eintrag allein reicht nicht.
- Projekt-/Datei-/Jobzustand über Reload/Neustart erhalten; keine sicheren Originale überschrieben und keine ungeklärte Doppelbeauftragung versteckt.
- Cache/Quota/Cancel/Partial-/Offlinefälle und alle vorbestehenden Schutztests bestehen. Keine erneute öffentliche Modal-Nutzung allein durch einen Clone.
- Audio-/MIDI-Timing, Stereo, Tails und Exportqualität haben passende automatische Tests und dokumentierte Hör-/DAW-Prüfungen.
- Branding und fehlende Top-Navigation entsprechen dem Nutzerwunsch; der Künstler muss den Jobstart ohne Erklärungen in der Entwicklerkonsole finden.
- Benutzerhilfe erklärt Eingang, Wirkung, Grenzen, Speicherung und Cloud-Ausführung, ohne den normalen Arbeitsbereich mit Implementierungsdetails zu überladen.
- Readme, normaler Start, saubere Neuinstallation, Modellsetup, Versionen, Lizenzinventar, Backup/Restore, Fehlerdiagnose und Rollback sind aktuell.
- Screenshots der zentralen Zustände, kleine rechtmäßig nutzbare Beispielausgaben und ein ehrlicher Verifikationsbericht liegen vor.
- Die Abnahme unterscheidet „technisch bestanden“, „menschlich klanglich geprüft“ und „noch offen“. Keine Produktions-/Kommerzialfreigabe behaupten, die nicht geprüft wurde.

Eine tatsächliche Lizenzsperre oder fehlende externe Freigabe wird mit Quelle und konkretem Restschritt festgehalten. Sie darf nicht dazu führen, dass ein rechtlich unklares Artefakt still eingebaut oder die ganze restliche Kette unvollständig liegen gelassen wird.

## 18. Migration, Betrieb und Rollback

1. Den **aktuellen Arbeitsbaum inklusive ungetrackter Dateien** zuerst als Ausgangsstand erfassen. Ein frischer Worktree nur von HEAD würde die jüngsten Sicherheits-/UI-Arbeiten verlieren. Kein `reset --hard`, `git clean`, Überschreiben fremder Arbeit oder unkontrolliertes Pull/Merge.
2. Änderungen auf nachvollziehbarem Implementierungszweig sichern; nur aufgabenbezogene Dateien und niemals die private Config stagen. Kein automatischer Push, Merge oder öffentlicher Deploy aus diesem Plan.
3. Neues Frontend und Backend zunächst neben dem geschützten Bestand entwickeln. Bestehende Modelldeployments/Resultate behalten; Erweiterungen versioniert und abwärtskompatibel vornehmen.
4. Lokal SQLite vor Schemawechsel über geeignete Backup-Methode sichern; Wiederherstellung mit passenden App-/Schema-Versionen testen. Migrationsfehler dürfen nicht still eine leere Datenbank erzeugen.
5. Modal-Updates paketweise an klaren App-/Image-Versionen prüfen. Neue Upload-/Jobinterfaces und Schutztests zuerst, dann zusätzliche Modellpfade. Andere Workspace-Apps und globale Budget-/Mitgliedschaftseinstellungen unberührt lassen.
6. In der finalen UI laufen Aufträge über validierte Geschäftsinterfaces. Der alte rohe `/api/modal/*`-Durchgriff darf kein Umgehen von Queue/Idempotenz/Quoten für neue Mutationen ermöglichen; im neuen Standard schließen bzw. strikt auf Legacy-Migration begrenzen.
7. Erst nach vollständiger Abnahme neue UI als Standard. Legacy-/Commerce-Code archiviert lassen und die alte Hauptseite nicht zusätzlich unbemerkt weiter veröffentlichen.
8. Rollback bedeutet frühere **geschützte** UI-/Backend-/Schema-Version, nicht erneutes Abschalten von Modal-Auth. Ein alter Cloud-Deploy ohne Schutz ist kein zulässiges Sicherheitsrollback.
9. Für einen später ausdrücklich angeforderten öffentlichen Deploy zuerst getrennten Freigabeplan: Nutzerautorisierung, sichere Job-/Datenzuordnung, Quoten/Budget, Storage, rechtlicher Betriebsumfang, Lizenzmodell und Zahlungsfragen. Nicht während dieses privaten Ausbaus dazuerfinden.

## 19. Zu Beginn zu bestätigende Annahmen – keine Blockade für die Planung

Diese Punkte sind als Standardannahmen im Plan entschieden. Sol 6.2 soll sie zu Beginn kurz gegen den dann aktuellen Stand prüfen und nur bei materiellen Abweichungen gezielt nachfragen:

- Zuerst private Einzelbenutzer-App auf dem vorhandenen Mac; kein öffentliches SaaS.
- Alle genannten Funktionen gehören zum vollständigen Umfang; AudioSR bleibt bewusst experimentell/opt-in und nicht universelle Pflichtstufe.
- Desktop ist primär; Mobile bekommt benutzbare Kernabläufe, keinen verkleinerten kompletten Timeline-Editor.
- Vorhandener privater Modal-Workspace bleibt die Modell-Infrastruktur; keine neue Anbieterbuchung.
- Exporte sind interoperable Audiodateien/MIDI/Manifeste, keine ungeprüften proprietären DAW-Projektgeneratoren.
- Keine beliebigen VST-/AU-Plugins, Stimmenklone oder zusätzlichen KI-Chat-/Bezahlmodule.
- Nutzer-Material für klangliche Endabnahme muss rechtmäßig nutzbar sein. Bis geeignete reale Fixtures vorliegen, technische und musikalische Qualität getrennt ausweisen.
- Exakte Engine-/Paket-/Checkpoint-Stände und deren Rechte werden vor Einbau konkretisiert. Ein fehlender Benchmark wird nicht durch eine erfundene Schätzung ersetzt.

## 20. Fortschritt und konkrete Übergabe von Sol 6.2

Bei Umsetzung eine kurze Fortschrittsdatei mit P0–P13 und T01–T24 führen: `offen / läuft / geprüft / gesperrt`, zugehörige Commits/Dateien, tatsächliche Testbefehle, Befunde und offene externe Abhängigkeiten. Diese Datei beschreibt den finalen Stand, nicht nur eine Liste begonnener Oberflächen.

Nach jedem zusammenhängenden Paket die relevanten Semantica-Entscheidungen aktualisieren. Bestehende historische Erkenntnisse nicht als aktuellen Live-Zustand ausgeben. Neue Architekturentscheidungen begründen und im Repo kurz festhalten.

Die finale Übergabe enthält: Startbefehl und URL, bedienbare Kernabläufe, Funktionsmatrix aller Engines, echte Testergebnisse, Screenshots, Beispielpakete, gemessene Grenzen/Kosten unter benannter Last, Lizenzregister und verbleibende Sperren. Kein „alles fertig“, wenn eine Kernfunktion nur eine Platzhalterkarte oder nicht erreichbare API ist.

## 21. Primärquellen und Nachschlagepunkte

Quellen sind technische Ausgangspunkte, keine Zusage eines bestimmten künftigen Paketstands. Vor Integration die konkret gewählte Version erneut prüfen und pinnen.

- [React: Zustands-/UI-Struktur](https://react.dev/learn/thinking-in-react)
- [Vite: Start, Build und unterstützte Laufzeiten](https://vite.dev/guide/)
- [FastAPI: BackgroundTasks und Grenzen für schwere Aufgaben](https://fastapi.tiangolo.com/tutorial/background-tasks/)
- [SQLite: lokale Anwendungsdateien, Einzelwriter und Netzwerkdateisysteme](https://www.sqlite.org/whentouse.html)
- [Web Audio: gemeinsame Startzeit/Offsets](https://developer.mozilla.org/en-US/docs/Web/API/AudioBufferSourceNode/start)
- [Web Audio: Buffer versus Langdateien, Autoplay, Benutzerkontrolle](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API/Best_practices)
- [HTTP-Range-Verträge](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Range_requests)
- [WaveSurfer: Peaks, große Dateien, Grenzen](https://wavesurfer.xyz/docs/)
- [Modal: Proxy-Authentifizierung](https://modal.com/docs/guide/webhook-proxy-auth)
- [Modal: Web-Requests, Limits und Lebenszyklus](https://modal.com/docs/guide/webhooks)
- [Modal: HTTP-Timeouts](https://modal.com/docs/guide/webhook-timeouts)
- [Modal: SDK-/gRPC-Payload-Limits](https://modal.com/docs/guide/troubleshooting)
- [Modal Dict: Claim-Methode und Aufbewahrung](https://modal.com/docs/reference/modal.Dict)
- [Modal: FunctionCall und Cancel](https://modal.com/docs/reference/modal.FunctionCall)
- [Modal: Volume-Konsistenz](https://modal.com/docs/guide/volumes)
- [FFmpeg: Loudness, True Peak und weitere Filter](https://ffmpeg.org/ffmpeg-filters.html)
- [FFmpeg: tatsächlicher Lizenzumfang](https://ffmpeg.org/legal.html)
- [Rubber Band: Integration, Ausgabe-/Kanalverhalten](https://breakfastquay.com/rubberband/integration.html)
- [Rubber Band: Projekt und Lizenz](https://github.com/breakfastquay/rubberband)
- [Matchering: Referenzmodus und Nutzung](https://github.com/sergree/matchering)
- [librosa: Onsets/Schnittvorschläge](https://github.com/librosa/librosa/blob/main/librosa/onset.py)
- [Pedalboard: DSP-Prozess/Reset](https://spotify.github.io/pedalboard/reference/pedalboard.html)
- [Basic Pitch: Modell-/Runtime- und Instrumentgrenzen](https://github.com/spotify/basic-pitch)
- [pretty_midi: Zeiten/Takt-/Notencontainer](https://craffel.github.io/pretty-midi/containers.html)
- [DeepFilterNet](https://github.com/Rikorose/DeepFilterNet) und [Maintainer-Klarstellung für Gewichte/Code](https://github.com/Rikorose/DeepFilterNet/commit/7b14b89)
- [RNNoise: Formate und Anwendung](https://github.com/xiph/rnnoise)
- [AudioSR: Funktionsweise und Grenzen](https://github.com/haoheliu/versatile_audio_super_resolution), [Basic-Gewichte](https://huggingface.co/haoheliu/audiosr_basic)
- [MuScriptor large: Modellbedingungen](https://huggingface.co/MuScriptor/muscriptor-large)
- [Stable Audio Open 1.0: Modellkarte und Community-Lizenz](https://huggingface.co/stabilityai/stable-audio-open-1.0)

**Planungsabgrenzung:** Nur dieser Plan und Rechercheanhänge wurden in diesem Arbeitsschritt angelegt. Die geplante neue Architektur, Werkzeuge, Migrationsschritte und Abnahmetests sind noch nicht implementiert oder durchgeführt.
