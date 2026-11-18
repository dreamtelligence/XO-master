import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { assetUrl, keyName, tonalKey, type Asset } from './api'
import { seconds } from './transport'

const names: Record<string, string> = {
  'tempo_map.txt': 'Tempoverlauf als Text', 'tempo_map.mid': 'Tempokarte für die DAW',
  'beat_analysis.json': 'Beat- und Taktanalyse', 'chord_analysis.json': 'Akkordanalyse',
  'chord_chart.txt': 'Akkordübersicht als Text', 'chord_progression.mid': 'Akkordfolge',
  'drums_timing.json': 'Drum-Analyse', 'drums_pattern.mid': 'Schlagzeug-Noten', 'click_track.mid': 'Klickspur',
  'melody_notes.json': 'Instrumenten-Analyse', 'melody_notes.mid': 'Instrumenten-Noten',
  'melody_simplified.mid': 'Vereinfachte Instrumenten-Noten', 'full_transcription.mid': 'Vollständige Transkription',
  'producer_summary.txt': 'Produktionsübersicht', 'daw_import_guide.txt': 'DAW-Importanleitung',
}
export function resultName(asset: Asset) {
  if (asset.role === 'analysis' && /^suggestions_[a-f0-9-]+\.json$/i.test(asset.name)) return 'Schnittvorschläge'
  if (asset.role === 'variant' && /^enhanced_[a-f0-9-]+\.wav$/i.test(asset.name)) return 'Entrauschtes Audio'
  const key = asset.name.toLowerCase()
  return Object.hasOwn(names, key) ? names[key] : asset.name
}

const number = new Intl.NumberFormat('de-DE', { maximumFractionDigits: 2 })
const numeric = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value)
const object = (value: unknown) => value !== null && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : undefined
const array = (value: unknown): unknown[] => Array.isArray(value) ? value : []
const string = (value: unknown) => typeof value === 'string' ? value : ''
const time = (value: unknown) => numeric(value) && value >= 0 ? seconds(value) : '–'

type Metric = [label: string, value: unknown]
export function ResultMetrics({ values }: { values: Metric[] }) {
  const present = values.filter(([, value]) => numeric(value) || (typeof value === 'string' && value.length > 0))
  return present.length ? <dl className="result-metrics">{present.map(([label, value]) => <div key={label}>
    <dt>{label}</dt><dd>{numeric(value) ? number.format(value) : String(value)}</dd>
  </div>)}</dl> : null
}

function ResultTable({ title, columns, rows }: { title: string; columns: string[]; rows: (string | number)[][] }) {
  const [limit, setLimit] = useState(16)
  return <section className="result-section"><h4>{title}</h4>{rows.length ? <>
    <div className="result-table" tabIndex={0} role="region" aria-label={title}><table aria-label={title}><thead><tr>{columns.map(column => <th scope="col" key={column}>{column}</th>)}</tr></thead>
      <tbody>{rows.slice(0, limit).map((row, i) => <tr key={i}>{row.map((value, col) => <td key={col}>{typeof value === 'number' ? number.format(value) : value}</td>)}</tr>)}</tbody>
    </table></div>
    {limit < rows.length && <button className="plain" onClick={() => setLimit(value => value + 32)}>Weitere anzeigen · {limit} von {rows.length}</button>}
  </> : <p className="hint">Keine Einträge erkannt.</p>}</section>
}

function TextReport({ asset }: { asset: Asset }) {
  const url = assetUrl(asset, 'download')
  const query = useQuery({ queryKey: ['text-report', asset.id], staleTime: Infinity, queryFn: async ({ signal }) => {
    // shortcut: Show the first 32 KiB inline. The complete file remains downloadable.
    const response = await fetch(url, { headers: { Range: 'bytes=0-32767' }, signal })
    if (!response.ok) throw new Error('Bericht konnte nicht geladen werden.')
    const total = Number(response.headers.get('content-range')?.split('/').at(-1))
    return { text: await response.text(), truncated: total > 32768 }
  } })
  return <section className="measure result-panel" aria-label="Textbericht">
    {query.data ? <><pre className="report-text" tabIndex={0}>{query.data.text}</pre>{query.data.truncated && <p className="hint">Vorschau der ersten 32 KiB</p>}</>
      : <p className="hint" role="status">{query.isError ? query.error.message : 'Bericht wird geladen …'}</p>}
    <a className="button" href={url}>Textbericht herunterladen</a>
  </section>
}

export function AnalysisResult({ asset }: { asset: Asset }) {
  const [rawOpen, setRawOpen] = useState(false)
  if (asset.suffix.toLowerCase() === '.txt') return <TextReport asset={asset} />
  const raw = asset.meta.report
  const report = object(raw)
  const key = tonalKey(report?.key)
  const detectedKey = key ? keyName(key) : string(object(report?.key)?.label)
  const speech = Array.isArray(report?.suggestions)
  const chords = Array.isArray(report?.chord_progression)
  const drums = object(report?.hit_counts)
  const instruments = Array.isArray(raw) ? raw.map(object).filter(item => typeof item?.instrument === 'string') : []
  const metrics: Metric[] = [
    ['Tempo · BPM', report?.tempo_bpm ?? report?.bpm], ['Taktart', report?.time_signature], ['Tonartvorschlag', detectedKey], ['Takte', report?.total_bars],
    ['Beats', Array.isArray(report?.beats) ? report.beats.length : undefined],
    ['Treffer', Array.isArray(report?.regions) ? report.regions.length : undefined],
    ['Vorschläge', speech ? array(report?.suggestions).length : undefined], ['Sprache', speech ? report?.language : undefined],
    ['Lautheit · LUFS', report?.lufs], ['True Peak · dBTP', report?.true_peak], ['Dynamik · LRA', report?.lra], ['Pegel · dBFS', report?.sample_peak],
  ]
  const suggestions = array(report?.suggestions).map(object).map(item => [time(item?.start), time(item?.end), string(item?.text) || ({ pause: 'Pause', filler: 'Füllwort', disturbance: 'Störgeräusch' } as Record<string, string>)[string(item?.kind)] || 'Schnittvorschlag'])
  const transcript = array(report?.transcript).map(object).map(item => [time(item?.start), string(item?.text)])
  return <section className="measure result-panel" aria-label="Analyseergebnis">
    <ResultMetrics values={metrics} />
    {report?.origin === 'librosa' && Object.hasOwn(report, 'key') && !key && <p className="hint">Tonart unklar</p>}
    {speech && <ResultTable title="Vorgeschlagene Schnittstellen" columns={['Start', 'Ende', 'Hinweis']} rows={suggestions} />}
    {!!transcript.length && <ResultTable title="Transkript" columns={['Start', 'Text']} rows={transcript} />}
    {chords && <ResultTable title="Akkordfolge" columns={['Zeit', 'Akkord', 'Dauer · s']} rows={array(report?.chord_progression).map(object).map(item => [
      time(item?.time), string(item?.chord), numeric(item?.duration) ? item.duration : '–',
    ])} />}
    {drums && <ResultTable title="Erkannte Schlagzeugtreffer" columns={['Instrument', 'Anzahl']} rows={Object.entries(drums).flatMap(([label, count]) => numeric(count) ? [[label, count]] : [])} />}
    {!!instruments.length && <ResultTable title="Erkannte Instrumente" columns={['Instrument', 'Noten']} rows={instruments.map(item => [string(item?.instrument), array(item?.notes).length])} />}
    {raw != null ? <details onToggle={event => setRawOpen(event.currentTarget.open)}><summary>Rohdaten anzeigen</summary>
      {rawOpen && <pre>{JSON.stringify(raw, null, 2)}</pre>}</details>
      : <a className="button" href={assetUrl(asset, 'download')}>Analysedatei herunterladen</a>}
  </section>
}

export function TempoMap({ asset }: { asset: Asset }) {
  const tempo = asset.meta.midi?.tempo ?? []
  const signature = asset.meta.midi?.signatures?.[0]
  if (!tempo.length && !signature) return <p className="measure hint">Für diese MIDI-Datei ist keine Vorschau verfügbar.</p>
  return <section className="measure result-panel" aria-label="MIDI-Tempokarte">
    <ResultMetrics values={[
      ['Anfangstempo · BPM', tempo[0]?.[1]], ['Tempoereignisse', tempo.length], ['Taktart', signature ? `${signature[1]}/${signature[2]}` : undefined],
    ]} />
    <p className="hint">Diese MIDI-Datei überträgt das Tempo in deine DAW.</p>
    <ResultTable title="Tempoverlauf" columns={['Zeit', 'BPM']} rows={tempo.map(([start, bpm]) => [time(start), bpm])} />
    <a className="button" href={assetUrl(asset, 'download')}>MIDI herunterladen</a>
  </section>
}
