import { useEffect, useRef, useState, useSyncExternalStore, type PointerEvent } from 'react'
import { type Asset, type Midi, type Note, type Project, type Region } from './api'
import { Num } from './tools'
import { seconds, type PositionClock } from './transport'

export function TransportTime({ clock }: { clock: PositionClock }) {
  return <output className="transport-time">{seconds(useSyncExternalStore(clock.subscribe, clock.current))}</output>
}

function Playhead({ clock, length, width }: { clock: PositionClock; length: number; width: number }) {
  const position = useSyncExternalStore(clock.subscribe, clock.current)
  return <span className="playhead" style={{ left: position / length * width }} />
}

export function Wave({ asset, length, position, offset = 0, region, beats = [], markers = [], onRegion, onSeek }: {
  asset: Asset; length: number; position: PositionClock; offset?: number; region?: Region; beats?: number[]; markers?: Region[];
  onRegion?: (region: Region) => void; onSeek: (seconds: number) => void;
}) {
  const canvas = useRef<HTMLCanvasElement>(null)
  const drag = useRef<number | null>(null)
  const last = useRef<number | null>(null)
  const rate = asset.meta.rate!
  const samples = asset.meta.samples!
  const [width, setWidth] = useState(400)
  const size = asset.meta.seconds ?? 0
  useEffect(() => {
    const observer = new ResizeObserver(entries => setWidth(Math.max(1, Math.floor(entries[0].contentRect.width))))
    if (canvas.current) observer.observe(canvas.current)
    return () => observer.disconnect()
  }, [])
  useEffect(() => {
    if (!canvas.current) return
    const view = canvas.current.getContext('2d')
    if (!view) return
    const density = Math.min(devicePixelRatio, 2)
    canvas.current.width = width * density
    canvas.current.height = 60 * density
    view.scale(density, density)
    view.fillStyle = '#f3eefb'
    view.fillRect(0, 0, width, 60)
    const w = size / length * width
    const start = offset / length * width
    view.fillStyle = '#eae2f7'
    view.fillRect(start, 0, w, 60)
    if (region) {
      view.fillStyle = '#d4c9f4'
      view.fillRect(start + region.start / rate / length * width, 0, (region.end - region.start) / rate / length * width, 60)
    }
    view.fillStyle = '#6346a9'
    const peaks = asset.meta.peaks ?? []
    for (let x = Math.max(0, Math.floor(start)); x < Math.min(width, start + w); x += 2) {
      const peak = peaks[Math.floor((x - start) / w * peaks.length)] || 0.015
      view.fillRect(x, 30 - 26 * peak, 1.35, 52 * peak)
    }
    view.fillStyle = '#a99ac7'
    for (const beat of beats) view.fillRect(beat / length * width, 0, 0.8, 60)
    view.fillStyle = '#a44072'
    for (const marker of markers) {
      view.fillRect(start + marker.start / rate / length * width, 3, 2, 54)
      view.fillRect(start + marker.end / rate / length * width, 3, 1, 54)
    }
  }, [asset, width, length, size, offset, region, rate, beats, markers])

  const get = (event: PointerEvent<HTMLCanvasElement>) => {
    const rect = event.currentTarget.getBoundingClientRect()
    return Math.max(0, Math.min(length, (event.clientX - rect.left) / rect.width * length))
  }
  return <div className="wave">
    <canvas ref={canvas} role="img" aria-label={`Wellenform für ${asset.name}, ${seconds(size)}`} onPointerDown={event => {
      drag.current = get(event); last.current = event.clientX; event.currentTarget.setPointerCapture(event.pointerId)
    }} onPointerUp={event => {
      if (drag.current === null) return
      const from = drag.current, to = get(event)
      if (onRegion && Math.abs(event.clientX - (last.current ?? event.clientX)) > 4) {
        const start = Math.min(samples - 1, Math.max(0, Math.round((Math.min(from, to) - offset) * rate)))
        const end = Math.max(start + 1, Math.min(samples, Math.round((Math.max(from, to) - offset) * rate)))
        onRegion({ start, end })
      } else onSeek(to)
      drag.current = null
    }} onPointerCancel={() => { drag.current = null }} />
    <Playhead clock={position} length={length} width={width} />
  </div>
}

export function Piano({ asset, view, change, edit }: { asset: Asset; view?: Midi; change: (view: Midi) => void; edit: () => void }) {
  const model = view ?? asset.meta.midi
  const [track, setTrack] = useState(0)
  const [index, setIndex] = useState(0)
  if (!model?.tracks.length) return <p className="hint">Dieses MIDI enthält keine darstellbaren Notenspuren.</p>
  const current = Math.min(track, model.tracks.length - 1)
  const item = model.tracks[current]
  const notes = item.notes
  const active = Math.min(index, notes.length - 1)
  const value = notes[active]
  const update = (next: Note[]) => change({ ...model, tracks: model.tracks.map((entry, i) => i === current ? { ...entry, notes: next } : entry) })
  const field = (at: number, n: number) => {
    if (!value) return
    const copy = [...value] as Note
    copy[at] = n
    update(notes.map((note, i) => i === active ? copy : note))
  }
  const maxTime = Math.max(1, notes.reduce((max, [, end]) => Math.max(max, end), 0))
  const low = notes.reduce((min, [, , pitch]) => Math.min(min, pitch), 84)
  const high = notes.reduce((max, [, , pitch]) => Math.max(max, pitch), 36)
  return <div className="piano">
    <div className="inline"><label className="field"><span>{item.drums ? 'Drum-Raster' : 'Piano-Roll'}</span><select value={current} onChange={event => { setTrack(Number(event.target.value)); setIndex(0) }}>{model.tracks.map((part, i) => <option value={i} key={i}>{part.name || `Spur ${i + 1}`} {part.drums ? '· GM Drums' : `· Programm ${part.program + 1}`}</option>)}</select></label><button onClick={edit}>MIDI-Werkzeug öffnen</button></div>
    <div className="piano-roll" role="img" aria-label={`${notes.length} Noten, Tonhöhe ${low} bis ${high}`}>
      {notes.slice(0, 1200).map(([a, b, pitch], i) => <span key={i} className={i === active ? 'note selected' : 'note'} title={`Note ${pitch} · ${seconds(a)}`} style={{ left: `${a / maxTime * 100}%`, width: `${(b - a) / maxTime * 100}%`, top: `${(high - pitch) / (high - low + 1) * 100}%` }} onClick={() => setIndex(i)} />)}
    </div>
    <div className="inline">
      <label className="field"><span>Note</span><select disabled={!notes.length} value={active} onChange={event => setIndex(Number(event.target.value))}>{notes.map(([a, , pitch], i) => <option value={i} key={i}>{i + 1} · {seconds(a)} · {pitch}</option>)}</select></label>
      <button onClick={() => { update([...notes, [value?.[1] ?? 0, (value?.[1] ?? 0) + .25, item.drums ? 36 : 60, 90]]); setIndex(notes.length) }}>Note hinzufügen</button>
      <button disabled={!value} onClick={() => update(notes.filter((_, i) => i !== active))}>Entfernen</button>
    </div>
    {value && <div className="field-grid four">
      <Num label="Start · s" value={value[0]} min={0} step={.001} onChange={n => field(0, n)} />
      <Num label="Länge · s" value={Number((value[1] - value[0]).toFixed(4))} min={.001} step={.001} onChange={n => field(1, value[0] + n)} />
      <Num label="Tonhöhe" value={value[2]} min={0} max={127} onChange={n => field(2, n)} />
      <Num label="Velocity" value={value[3]} min={1} max={127} onChange={n => field(3, n)} />
    </div>}
  </div>
}

export function RegionEditor({ project, asset, region, set, slices, setSlices, addLabel, onPlay, detected }: {
  project: Project; asset: Asset; region: Region; set: (region: Region) => void; slices: Region[]; setSlices: (slice: Region[]) => void;
  addLabel: string; onPlay: (region: Region) => void; detected: Region[];
}) {
  const rate = asset.meta.rate!
  const max = asset.meta.samples!
  const [snap, setSnap] = useState(false)
  const [show, setShow] = useState(false)
  const change = (key: 'start' | 'end', time: number) => {
    const origin = project.draft.downbeat ?? 0
    const [, denominator] = project.meter.split('/').map(Number)
    const quarter = 60 / project.bpm * 4 / denominator
    const position = Math.round((snap ? Math.round((time - origin) / quarter) * quarter + origin : time) * rate)
    set({ ...region, [key]: key === 'start' ? Math.max(0, Math.min(region.end - 1, position)) : Math.min(max, Math.max(region.start + 1, position)) })
  }
  const display = (value: number) => Number((value / rate).toFixed(5))
  return <div className="region-panel">
    <div className="inline section-heading"><h3>Auswahl</h3><button onClick={() => set({ start: 0, end: max })}>Ganze Datei</button></div>
    <div className="region-grid">
      <Num label="Start · s" value={display(region.start)} min={0} max={display(region.end - 1)} step={.001} onChange={value => change('start', value)} />
      <Num label="Ende · s" value={display(region.end)} min={display(region.start + 1)} max={display(max)} step={.001} onChange={value => change('end', value)} />
      <button aria-pressed={snap} onClick={() => setSnap(!snap)}>Raster</button>
      <button onClick={() => onPlay(region)}>Auswahl hören</button>
    </div>
    <div className="inline">
      <button onClick={() => { setSlices([...slices, { ...region, name: `${addLabel} ${slices.length + 1}` }]); setShow(true) }}>{addLabel} hinzufügen</button>
      {!!detected.length && <button onClick={() => { setSlices(detected); setShow(true) }}>{detected.length} Vorschläge übernehmen</button>}
      {!!slices.length && <button aria-expanded={show} onClick={() => setShow(!show)}>{slices.length} Markierungen {show ? 'ausblenden' : 'anzeigen'}</button>}
    </div>
    {show && !!slices.length && <div className="slice-list">{slices.map((slice, index) => <div key={index} className="slice">
      <input aria-label={`Name von Markierung ${index + 1}`} value={slice.name || ''} onChange={event => setSlices(slices.map((item, i) => i === index ? { ...item, name: event.target.value } : item))} />
      <button onClick={() => { set(slice); onPlay(slice) }}>{seconds(slice.start / rate)}–{seconds(slice.end / rate)}</button>
      <button aria-label={`Markierung ${index + 1} durch aktuelle Auswahl ersetzen`} onClick={() => setSlices(slices.map((item, i) => i === index ? { ...item, start: region.start, end: region.end } : item))}>Setzen</button>
      <button aria-label={`Markierung ${index + 1} entfernen`} onClick={() => setSlices(slices.filter((_, i) => i !== index))}>×</button>
    </div>)}</div>}
  </div>
}
