import type { RefObject } from 'react'
import { BookOpen, X } from 'lucide-react'
import { categories, effectName, pluginModules, tools } from './tools'

const toolGuide = {
  qa: ['Misst die wahrgenommene Lautheit und die lautesten Spitzen. Zeigt außerdem leise Abschnitte und mögliche Übersteuerungen.', 'Prüfe einen Mix vor dem Export oder vergleiche die Messwerte von Original und fertiger Variante.'],
  separation: ['Teilt einen Song in einzelne Spuren wie Gesang, Schlagzeug, Bass und Begleitung. Du wählst die gewünschten Teile aus.', 'Isoliere einen Gesang für einen Remix, nimm nur die Drums als Ausgangsmaterial oder erstelle eine Instrumentalfassung. Höre die einzelnen Spuren auf Trennartefakte ab.'],
  detect: ['Schlägt Tempo, Taktraster und Tonart vor. Mit Grid + Anschläge markiert es zusätzlich mögliche Startpunkte für einzelne Samples.', 'Übernimm ein passendes Tempo unter Beat-Grid und erster Downbeat. Setze dort den ersten Taktanfang von Hand, wenn das Raster versetzt ist. Prüfe vorgeschlagene Treffer vor dem Schneiden.'],
  loop: ['Schreibt die markierte Region oder eine gewünschte Anzahl von Takten als WAV-Loop. Kurze Fades können Knackser an den Grenzen glätten.', 'Schneide etwa zwei Takte Drums aus und höre sie im Loop ab, bevor du sie in deine DAW ziehst.'],
  oneshot: ['Speichert einzelne Treffer als eigene WAV-Dateien. Wenn du mehrere Treffer markiert hast, kannst du sie in einem Durchgang herausschneiden.', 'Baue dir ein Sample-Kit aus Kicks, Snares, Percussion oder kurzen Vocal-Schnipseln.'],
  stretch: ['Mit Rubber Band kannst du Tempo und Tonhöhe getrennt voneinander ändern. Die Tonartwahl verschiebt einen Clip innerhalb von Dur oder Moll.', 'Passe einen Loop an dein Projekttempo an oder transponiere einen Vocal-Clip. Wähle Tonart rendern · Tempo beibehalten, um nur die Tonhöhe zu ändern.'],
  transcription: ['Schlägt aus einer Musikaufnahme je nach Auswahl Melodie- und Schlagzeug-MIDI, Akkorde, Tonart oder ein Beat-Raster vor.', 'Verschaffe dir einen Überblick über einen ganzen Song oder nutze die MIDI-Spuren als Ausgangspunkt für ein neues Arrangement. Prüfe Noten und Akkorde nach Gehör.'],
  basic_pitch: ['Erkennt Noten und Tonhöhenbewegungen im markierten Audiobereich und schreibt sie als MIDI.', 'Wandle eine Basslinie, Gitarrenmelodie oder einzelne Instrumentenspur in bearbeitbare Noten um. Gib der MIDI-Spur in deiner DAW ein Instrument.'],
  midi: ['Öffnet eine vorhandene MIDI-Datei zur Bearbeitung. Du kannst einzelne Noten anpassen, löschen oder ergänzen und die Fassung transponieren oder ans Raster rücken.', 'Korrigiere erkannte Noten oder passe die Tonhöhe und Länge einer MIDI-Phrase an dein Arrangement an.'],
  effects: ['Wendet mehrere Effekte in der Reihenfolge des Racks auf einen Clip an. Mit „Live hören“ wirken die Regler während der Wiedergabe auf einen Ausschnitt von bis zu 30 Sekunden.', 'Vergleiche A · Quelle und B · Effekt an derselben Stelle. Vergrößere das Display für beide Spektren. Speichere den Ausschnitt als WAV oder rendere den ganzen Clip als Variante.'],
  mix: ['Fasst ausgewählte Spuren zu einer Stereodatei zusammen. Jede Spur hat Einstellungen für Pegel, Links-rechts-Position, Ausschnitt und Startzeit.', 'Erstelle einen schnellen Remix aus Stems oder mische zusätzliche Spuren unter ein vorhandenes Arrangement.'],
  mastering: ['Bearbeitet den fertigen Mix für die Ausgabe. Du wählst, wie stark der Eingriff sein soll und welche Lautheit und Spitzengrenze du anstrebst.', 'Erzeuge eine abhörfertige Fassung und vergleiche sie auf ähnlicher Lautheit mit deinem Mix.'],
  reference: ['Matchering nimmt einen Referenztrack als klanglichen Maßstab für die Bearbeitung deines Mixes.', 'Importiere über + Referenz importieren einen anderen Track mit einer Klangbalance, die dir gefällt. Wähle deinen Mix, stelle die Referenz im Inspektor ein und höre das Ergebnis im Vergleich.'],
  enhancement: ['Versucht, Sprache klarer hervorzuheben und störende Hintergründe zu reduzieren. Auf Wunsch kannst du Vorschläge für Pausen oder Störstellen anfordern.', 'Arbeite an Dialog, Podcast oder Voice-over. Höre leise Wörter und Wortenden nach dem Rendern ab, bevor du Schnittvorschläge übernimmst.'],
  deepfilter: ['Reduziert Hintergrundrauschen in einer Sprachaufnahme.', 'Probiere es bei einer Aufnahme mit Lüfter, Straßenrauschen oder einem unruhigen Raum. Vergleiche den bereinigten Ausschnitt mit der Quelle.'],
  rnnoise: ['Dämpft Hintergrundgeräusche in einer Sprachspur.', 'Teste es als schnelle Alternative für Mikrofon- oder Gesprächsaufnahmen. Vergleiche die Verständlichkeit und den Klang mit DeepFilterNet oder MossFormer.'],
  cut: ['Entfernt markierte Bereiche aus der Sprachaufnahme und schreibt eine gekürzte Version.', 'Markiere eine lange Pause, einen Fehlstart oder eine Störstelle. Höre die Auswahl und bestätige sie als Schnitt, bevor du die neue Fassung erzeugst.'],
  generation: ['Erzeugt aus einer Textbeschreibung kurze Sounds und legt bis zu drei einzelne Takes ab.', 'Beschreibe etwa einen trockenen Percussion-Hit, eine körnige Fläche oder einen Übergang. Wähle einen Take zum Weiterbearbeiten und schneide ihn bei Bedarf als Loop oder One-Shot.'],
  audiosr: ['AudioSR ergänzt versuchsweise hohe Frequenzen bei einem ausgewählten Audioausschnitt von bis zu 15 Sekunden.', 'Teste es an einer dumpfen oder schmalbandigen Aufnahme. Entscheide per Hörvergleich, ob der neu erzeugte Höhenanteil hilfreich klingt.'],
} satisfies Record<(typeof categories)[number][1][number], [string, string]>

const rackGuide: Record<string, string> = {
  Gain: 'Macht das Signal leiser oder lauter. Setze es am Anfang zum Anpassen des Eingangspegels oder am Ende für den Ausgangspegel ein.',
  HighpassFilter: 'Dämpft sehr tiefe Frequenzen. Hilft zum Beispiel gegen Trittschall oder Rumpeln auf einer Stimme.',
  LowpassFilter: 'Dämpft hohe Frequenzen. Praktisch, um ein Sample weicher oder weiter entfernt wirken zu lassen.',
  PeakFilter: 'Hebt einen gewählten Frequenzbereich an oder senkt ihn ab. Damit kannst du beispielsweise eine störende Resonanz abschwächen.',
  Compressor: 'Fängt laute Stellen ab und gleicht Unterschiede zwischen leisen und lauten Passagen aus. Das kann eine Stimme oder einen Bass gleichmäßiger machen.',
  NoiseGate: 'Dämpft das Signal, wenn es unter eine eingestellte Lautstärke fällt. Nützlich gegen Geräusche zwischen Worten. Prüfe, ob leise Wortenden erhalten bleiben.',
  Limiter: 'Begrenzt sehr laute Spitzen. Platziere ihn am Ende der Kette, wenn einzelne Spitzen zu laut werden.',
  Reverb: 'Gibt einem trockenen Klang einen hörbaren Raum. Mit wenig Hall kannst du kurze Drums oder eine Stimme etwas räumlicher machen.',
  Delay: 'Erzeugt verzögerte Wiederholungen. Stelle Abstand, Anzahl der hörbaren Echos und Effektanteil für einen rhythmischen Effekt ein.',
  ChowTape: 'Färbt ein Signal wie ein Tonband. Mit Drive, Sättigung und Mix kannst du einen Bass, eine Stimme oder Drums von subtil warm bis deutlich angezerrt bearbeiten.',
  ChowMatrix: 'Erzeugt mehrere rhythmische Echos. Nutze Echozeit, Feedback und Effektpegel für Vocal-Enden, perkussive Muster oder Übergänge.',
  DragonflyPlate: 'Erzeugt einen dichten Plattenhall. Stelle Hallzeit, Effektanteil und die Pause vor dem Einsetzen des Halls ein. Gut für Vocals, Snares oder atmosphärische Flächen.',
}

const toolChapters = categories.map(([title, ids]) => ({ id: `handbuch-${ids[0]}`, title, ids }))
const chapters = [
  { id: 'handbuch-start', title: 'Schnellstart' },
  { id: 'handbuch-studio', title: 'Studio bedienen' },
  ...toolChapters,
  { id: 'handbuch-effekte', title: 'Alle Effekte' },
  { id: 'handbuch-export', title: 'Export und Projekte' },
]

export function Handbook({ dialogRef }: { dialogRef: RefObject<HTMLDialogElement | null> }) {
  return <dialog className="manual-dialog" ref={dialogRef} aria-labelledby="handbuch-titel">
    <header className="manual-header">
      <div className="manual-title"><BookOpen size={22} aria-hidden="true" /><div><h1 id="handbuch-titel">Handbuch</h1><small>Artist Workspace</small></div></div>
      <form method="dialog"><button type="submit" autoFocus aria-label="Handbuch schließen"><X size={16} aria-hidden="true" /> Schließen</button></form>
    </header>
    <div className="manual-layout">
      <nav className="manual-nav" aria-label="Inhaltsverzeichnis">
        {chapters.map(chapter => <a key={chapter.id} href={`#${chapter.id}`}>{chapter.title}</a>)}
      </nav>
      <article className="manual-content">
        <section id="handbuch-start">
          <h2>Schnellstart</h2>
          <p>Im Artist Workspace bereitest du Aufnahmen, Stems, Samples und MIDI für deine Musikprojekte vor. Du kannst Varianten direkt vergleichen und das Ergebnis in Ableton Live, Logic Pro oder einer anderen DAW weiterbearbeiten.</p>
          <ol>
            <li>Starte mit <strong>Dateien importieren</strong>, einem leeren Projekt oder einer Vorlage wie <strong>Remix &amp; Samples</strong>.</li>
            <li>Wähle den Clip in der <strong>Bibliothek</strong>. Ziehe in der Wellenform, wenn du nur einen Ausschnitt bearbeiten möchtest.</li>
            <li>Wähle im <strong>Inspektor</strong> das passende Werkzeug und starte es. Auf kleineren Bildschirmen erreichst du den Inspektor über <strong>Werkzeuge</strong>. Unter <strong>Aufgaben</strong> siehst du den Fortschritt und findest die Ergebnisse.</li>
            <li>Höre die neue Fassung an. Lege die Dateien, die du weiterverwenden möchtest, in den <strong>Exportkorb</strong>.</li>
          </ol>
        </section>
        <section id="handbuch-studio">
          <h2>Studio bedienen</h2>
          <div className="manual-entries">
            <div><h3>Bibliothek und Versionen</h3><p>Hier liegen Originale, Referenzen und Ergebnisse. Ein Klick öffnet einen Clip. Mit den Kästchen wählst du mehrere Spuren etwa für den Mix. Bearbeitungen erzeugen neue Dateien, und dein Original bleibt erhalten.</p></div>
            <div><h3>Wellenform und Auswahl</h3><p>Klicke in die Wellenform, um zur passenden Stelle zu springen. Ziehe für eine Auswahl oder tippe Start und Ende ein. Schalte für die Arbeit mit Musik das Lineal auf <strong>Takte</strong> und höre die markierte Stelle mit <strong>Auswahl hören</strong> ab.</p></div>
            <div><h3>Transport und Hörvergleich</h3><p>Unten findest du Wiedergabe, Stopp, Loop und Abhörpegel. Mit der Leertaste kannst du abspielen oder pausieren, wenn der Fokus gerade auf der Arbeitsfläche liegt. Bei einer bearbeiteten Variante kannst du zwischen Quelle A und Variante B wechseln.</p></div>
            <div><h3>Aufgaben und Bearbeitungsfolge</h3><p>Öffne Ergebnisse direkt über <strong>Aufgaben</strong>. Bei Teilergebnissen kannst du fehlende Teile erneut anstoßen, wenn die Option angezeigt wird. Mit der <strong>Bearbeitungsfolge</strong> kannst du Werkzeuge nacheinander anwenden, zum Beispiel erst schneiden und danach messen.</p></div>
          </div>
        </section>
        {toolChapters.map(chapter => <section key={chapter.id} id={chapter.id}>
          <h2>{chapter.title}</h2>
          <div className="manual-entries">{chapter.ids.map(id => <div key={id}>
            <h3>{tools[id][0]}</h3><p>{toolGuide[id][0]}</p><p>{toolGuide[id][1]}</p>
          </div>)}</div>
        </section>)}
        <section id="handbuch-effekte">
          <h2>Alle Effekte</h2>
          <p>Öffne <strong>Effektkette</strong> und füge ein Modul hinzu. Mit den Pfeilen änderst du die Reihenfolge. <strong>Bypass</strong> setzt ein Modul vorübergehend aus. Bei Hall und Delay lässt <strong>WAV-Ausklang</strong> im gespeicherten Ergebnis mehr Platz für die letzten Echos.</p>
          <p>Zum Vergleichen markierst du einen Bereich und wählst <strong>Ausschnitt rendern</strong>. Drehst du danach an einem Regler, erstellst du eine neue Vorschau für diese Einstellung.</p>
          <dl className="manual-rack">{Object.entries({ ...effectName, ...Object.fromEntries(Object.entries(pluginModules).map(([id, module]) => [id, module.name])) }).map(([id, label]) => <div key={id}>
            <dt>{label}</dt><dd>{rackGuide[id]}</dd>
          </div>)}</dl>
        </section>
        <section id="handbuch-export">
          <h2>Export und Projekte</h2>
          <div className="manual-entries">
            <div><h3>In der DAW weiterarbeiten</h3><p>Lege die gewünschten WAV- und MIDI-Dateien in den <strong>Exportkorb</strong> und wähle <strong>DAW-Paket erstellen</strong>. Sobald der Export fertig ist, kannst du das ZIP unter <strong>Aufgaben</strong> laden. Entpacke es und ziehe zusammengehörige Spuren an dieselbe Startposition in deiner DAW.</p></div>
            <div><h3>Format und Ausrichtung wählen</h3><p>WAV mit 24 Bit ist eine gute Wahl fürs Weiterbearbeiten. MP3 eignet sich als Hörkopie. <strong>Spuren ausrichten</strong> berücksichtigt die Startpositionen aus dem Projekt. Für ein einzelnes Ergebnis kannst du über <strong>Asset-Aktionen</strong> die Datei direkt herunterladen.</p></div>
            <div><h3>Projekt mitnehmen</h3><p>Mit <strong>Projektpaket sichern</strong> legst du eine Kopie des Projekts mit seinen Dateien an. Über <strong>Projektpaket öffnen</strong> auf der Startseite importierst du sie wieder. Im Menü beim Projektnamen kannst du das Projekt umbenennen, duplizieren oder archivieren.</p></div>
            <div><h3>Werkzeug gerade nicht verfügbar?</h3><p>Prüfe, ob der richtige Clip ausgewählt ist und ob das Werkzeug eine Referenz oder markierte Region braucht. Bei einem archivierten Projekt musst du es erst aktivieren. Das Projektprofil <strong>Veröffentlichung</strong> sperrt bestimmte KI-Werkzeuge.</p></div>
          </div>
        </section>
      </article>
    </div>
  </dialog>
}
