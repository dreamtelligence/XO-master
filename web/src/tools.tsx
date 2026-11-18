import type { ReactNode } from 'react'
import { AudioLines, AudioWaveform, Disc3, Maximize2, Power, Waves } from 'lucide-react'
import { Dial } from './controls'
import { FxScope } from './fx'
import { audio, keyName, midiHasNotes, pitchNames, type Asset, type Capabilities, type EffectStep, type Midi, type Project, type Region, type TonalKey, type Track } from './api'

export const tools: Record<string, [string, string, string]> = {
  qa: ['Audio prüfen', 'Lautheit, True Peak und Stille für die ausgewählte Datei messen.', 'Audio prüfen'],
  separation: ['Stems trennen', 'Gesang, Schlagzeug, Bass und Begleitung als einzelne Projektspuren übernehmen.', 'Stems trennen'],
  detect: ['Grid & Treffer erkennen', 'Tempo, Tonart und mögliche Sample-Grenzen für dieses Audio vorschlagen.', 'Audio analysieren'],
  loop: ['Loops schneiden', 'Die Auswahl oder ganze Takte als WAV-Loop ablegen.', 'Loops erzeugen'],
  oneshot: ['One-Shots schneiden', 'Korrigierte Treffer als einzelne WAV-Dateien ablegen.', 'Samples erzeugen'],
  stretch: ['Tempo & Tonhöhe', 'Tempo und Tonhöhe unabhängig bearbeiten. Passendes MIDI kann dieselbe Transposition übernehmen.', 'Tempo-Variante rendern'],
  transcription: ['MuScriptor & Musikanalyse', 'Mehrinstrument-MIDI, Drums, Akkorde oder Beat-Grid auswerten.', 'Analyse starten'],
  basic_pitch: ['Basic Pitch', 'Noten und Pitch Bends aus einer möglichst einzelnen Instrumentenspur erkennen.', 'MIDI erstellen'],
  midi: ['MIDI bearbeiten', 'Notenliste, Takt und konstantes Anfangstempo als neue MIDI-Version schreiben.', 'MIDI rendern'],
  effects: ['Effektkette', 'Baue deinen Sound aus Filtern, Band, Echo und Hall.', 'Ganzen Clip rendern'],
  mix: ['Remix-Mixer', 'Die markierten Spuren mit Clip-Grenzen, Gain, Panorama und Offset als Stereomix rendern.', 'Mix rendern'],
  mastering: ['Automatisches Mastering', 'Einen fertigen Mix mit der vorhandenen Mastering-Kette bearbeiten und messen.', 'Master rendern'],
  reference: ['Referenzmastering', 'Matchering passt den Mix an eine Referenzdatei aus dem Projekt an.', 'Referenzmaster rendern'],
  enhancement: ['MossFormer', 'Sprachrauschen entfernen. Die Bearbeitung erfolgt in Mono bei 48 kHz.', 'Stimme entrauschen'],
  deepfilter: ['DeepFilterNet', 'Lokale Rauschunterdrückung für Sprache. Ausgabe in Mono bei 48 kHz.', 'Stimme entrauschen'],
  rnnoise: ['RNNoise', 'Lokaler 48-kHz-Monofilter für Sprachrauschen.', 'Stimme entrauschen'],
  cut: ['Sprachschnitt', 'Bestätigte Schnitte anwenden und ihre Quellpositionen speichern.', 'Schnitte rendern'],
  generation: ['Text zu Audio', 'Aus einem Prompt bis zu drei einzeln gespeicherte Audio-Takes erzeugen.', 'Sounds erzeugen'],
  audiosr: ['Bandbreite ergänzen', 'Experiment mit AudioSR Basic auf einer Auswahl von bis zu 15 Sekunden.', 'Experiment rendern'],
}
export const templates = [
  { id: 'remix', title: 'Remix & Samples', detail: 'Stems, Grid, Loops und MIDI', icon: '∿', recipe: ['separation', 'detect', 'loop', 'stretch'] },
  { id: 'mix', title: 'Mix fertigstellen', detail: 'Messen, vergleichen und mastern', icon: '≋', recipe: ['qa', 'mastering', 'reference'] },
  { id: 'speech', title: 'Stimme bearbeiten', detail: 'Rauschen, Pausen und Schnitte', icon: '◉', recipe: ['enhancement', 'qa', 'cut'] },
  { id: 'generate', title: 'Sounds erzeugen', detail: 'Prompts, Takes und Varianten', icon: '✧', recipe: ['generation', 'loop', 'stretch'] },
]
export const categories = [
  ['Quelle & Grid', ['qa', 'separation', 'detect']],
  ['Loops & Tempo', ['loop', 'oneshot', 'stretch']],
  ['MIDI & Harmonie', ['transcription', 'basic_pitch', 'midi']],
  ['Mix & Master', ['effects', 'mix', 'mastering', 'reference']],
  ['Stimme & Sound', ['enhancement', 'deepfilter', 'rnnoise', 'cut', 'generation', 'audiosr']],
] as const
const cloud = new Set(['separation', 'transcription', 'enhancement', 'mastering', 'generation', 'audiosr'])

export const effects: Record<string, Record<string, [number, number, number, string]>> = {
  Gain: { gain_db: [-36, 18, 0, 'Pegel · dB'] },
  HighpassFilter: { cutoff_frequency_hz: [20, 18000, 80, 'Grenzfrequenz · Hz'] },
  LowpassFilter: { cutoff_frequency_hz: [20, 18000, 10000, 'Grenzfrequenz · Hz'] },
  PeakFilter: { cutoff_frequency_hz: [20, 18000, 1000, 'Mittenfrequenz · Hz'], gain_db: [-18, 18, 0, 'Pegel · dB'], q: [0.1, 10, .707, 'Güte Q'] },
  Compressor: { threshold_db: [-60, 0, -18, 'Schwelle · dB'], ratio: [1, 20, 2, 'Ratio'], attack_ms: [.1, 200, 20, 'Attack · ms'], release_ms: [1, 600, 100, 'Release · ms'] },
  NoiseGate: { threshold_db: [-80, -5, -45, 'Schwelle · dB'], ratio: [1, 20, 5, 'Ratio'], attack_ms: [.1, 200, 5, 'Attack · ms'], release_ms: [1, 600, 80, 'Release · ms'] },
  Limiter: { threshold_db: [-24, 0, -1, 'Schwelle · dB'], release_ms: [1, 500, 100, 'Release · ms'] },
  Reverb: { room_size: [0, 1, .4, 'Raumgröße'], wet_level: [0, 1, .25, 'Effektanteil'], dry_level: [0, 1, .75, 'Direktanteil'] },
  Delay: { delay_seconds: [.01, 2, .25, 'Verzögerung · s'], feedback: [0, .8, .25, 'Feedback'], mix: [0, 1, .25, 'Effektanteil'] },
  ChowTape: { tape_drive: [0, 1, .54, 'Drive'], tape_saturation: [0, 1, .64, 'Sättigung'], dry_wet: [0, 100, 70, 'Mix · %'] },
  ChowMatrix: { time_ms: [40, 1000, 375, 'Echozeit · ms'], feedback_percent: [0, 70, 40, 'Feedback · %'], wet: [-36, 0, -10, 'Effektpegel · dB'] },
  DragonflyPlate: { wet_level: [0, 100, 27, 'Mix · %'], decay_s: [.1, 5, 1.35, 'Hallzeit · s'], predelay_ms: [0, 100, 18, 'Predelay · ms'] },
}
export const effectName: Record<string, string> = { Gain: 'Gain', HighpassFilter: 'Hochpass', LowpassFilter: 'Tiefpass', PeakFilter: 'Parametrischer EQ', Compressor: 'Kompressor', NoiseGate: 'Noise Gate', Limiter: 'Limiter', Reverb: 'Hall', Delay: 'Delay' }
export const pluginModules = {
  ChowTape: { name: 'CHOW Tape', family: 'Band', glyph: Disc3 },
  ChowMatrix: { name: 'CHOW Matrix', family: 'Echo', glyph: AudioWaveform },
  DragonflyPlate: { name: 'Dragonfly Plate', family: 'Hall', glyph: Waves },
} as const
const defaultChain: EffectStep[] = [{ effect: 'Gain' }, { effect: 'Compressor' }]
export function effectParameters(settings: Record<string, unknown>) {
  const chain = (settings.chain as EffectStep[] | undefined) ?? defaultChain
  const hasTail = chain.some(step => !step.bypass && (step.effect === 'ChowMatrix' || step.effect === 'DragonflyPlate'))
  return { chain, tail: Number(settings.tail ?? (hasTail ? 2 : 0)) }
}

export function effectTitle(effect: string) {
  return pluginModules[effect as keyof typeof pluginModules]?.name ?? effectName[effect] ?? effect
}

export function EffectDials({ step, change }: { step: EffectStep; change: (step: EffectStep) => void }) {
  return <div className="dial-grid">{Object.entries(effects[step.effect] ?? {}).map(([key, [min, max, fallback, label]]) =>
    <Dial key={key} label={label} min={min} max={max} step={.01} value={Number(step[key] ?? fallback)} live
      onChange={value => change({ ...step, [key]: value })} />)}</div>
}

export function Num({ label, value, onChange, min, max, step = 1 }: { label: string; value: number; onChange: (value: number) => void; min?: number; max?: number; step?: number }) {
  return <label className="field"><span>{label}</span><input type="number" value={Number.isFinite(value) ? value : ''} min={min} max={max} step={step} onChange={event => { if (event.target.value !== '') onChange(Number(event.target.value)) }} /></label>
}
export function Check({ children, onChange, checked }: { children: ReactNode; onChange: (checked: boolean) => void; checked: boolean }) {
  return <label className="check"><input type="checkbox" checked={checked} onChange={event => onChange(event.target.checked)} />{children}</label>
}

type Props = {
  tool: string; setTool: (tool: string) => void; settings: Record<string, unknown>; change: (key: string, value: unknown) => void;
  asset?: Asset; assets: Asset[]; selected: Asset[]; project: Project; caps?: Capabilities; region?: Region;
  openSource?: () => void;
  rack: { selected: number; select: (index: number) => void; running: boolean; read: () => number[][] | undefined;
    expanded: boolean; expand: () => void; status: string; playback?: () => void; playing: boolean; render?: () => void };
  sourceKey?: TonalKey; estimatedKey?: TonalKey; setSourceKey: (value?: TonalKey) => void;
  setRegion: (region: Region) => void; slices: Region[]; setSlices: (slices: Region[]) => void; setGrid: (bpm: number, downbeat?: number) => void;
  tracks: Record<string, Track>; setTrack: (id: string, track: Track) => void;
  run: (tool: string, inputs: string[], params: Record<string, unknown>, count?: number) => void; busy: boolean;
}

export function Inspector(p: Props) {
  const { tool, asset, selected, project, settings, change, region } = p
  const [title, description, action] = tools[tool] || tools.qa
  const num = (key: string, fallback: number) => Number(settings[key] ?? fallback)
  const str = (key: string, fallback: string) => String(settings[key] ?? fallback)
  const boolean = (key: string, fallback = false) => Boolean(settings[key] ?? fallback)
  const ready = ['ready', 'experimental'].includes(p.caps?.tools[tool] ?? '')
  const usesMany = tool === 'mix' || tool === 'stretch'
  const refs = p.assets.filter(item => item.role === 'reference' && item.id !== asset?.id)
  const defaultReference = refs.find(item => item.hash !== asset?.hash) ?? refs[0]
  const reference = str('reference', defaultReference?.id || '')
  const identicalReference = tool === 'reference' && refs.find(item => item.id === reference)?.hash === asset?.hash && Boolean(asset)
  const inputs = tool === 'generation' ? [] : usesMany ? (selected.length ? selected : asset ? [asset] : [])
    : asset ? tool === 'reference' && reference ? [asset, ...refs.filter(ref => ref.id === reference)] : [asset] : []
  const { chain, tail } = effectParameters(settings)
  const rackIndex = Math.min(p.rack.selected, chain.length - 1)
  const rackStep = chain[rackIndex]
  const replaceStep = (value: EffectStep) => change('chain', chain.map((item, index) => index === rackIndex ? value : item))
  function addStep(effect: string) {
    const previous = settings.chain == null && Object.hasOwn(pluginModules, effect) ? [] : chain
    change('chain', [...previous, { effect }])
    p.rack.select(previous.length)
  }
  const readyPlugins = p.caps?.effect_plugins ?? {}
  const pluginMissing = tool === 'effects' && chain.some(step => !step.bypass && Object.hasOwn(pluginModules, step.effect) && !readyPlugins[step.effect])
  const needsAudio = tool !== 'midi' && tool !== 'generation'
  const supported = tool === 'midi' ? asset?.role === 'midi' && midiHasNotes(settings.view as Midi | undefined)
    : tool === 'generation' ? str('prompt', '').trim().length > 0
    : inputs.length > 0 && inputs.every(item => audio(item) || (tool === 'stretch' && item.role === 'midi')) && inputs.some(audio)
  const disabled = p.busy || !!project.archived || !ready || !supported || pluginMissing || (cloud.has(tool) && project.purpose === 'release') || (tool === 'reference' && (inputs.length !== 2 || identicalReference)) || (tool === 'cut' && !p.slices.length) || (tool === 'effects' && !chain.length)
  const rate = asset?.meta.rate || project.rate
  const duration = asset?.meta.samples || 0
  const sourceKey = p.sourceKey ?? p.estimatedKey
  const singleSource = audio(asset) && inputs[0]?.id === asset.id && inputs.filter(audio).length === 1
  const pitch = num('pitch', 0)
  const currentTonic = sourceKey && Number.isInteger(pitch) ? (sourceKey.tonic + pitch + 12) % 12 : ''
  const resultOnly = !supported && tool !== 'generation' && (asset?.role === 'analysis'
    || (asset?.role === 'midi' && !asset.meta.midi?.tracks?.length))
  const toolSelect = <label className="field tool-select"><span>Werkzeug</span><select value={tool} onChange={event => p.setTool(event.target.value)}>{categories.map(([name, ids]) => <optgroup key={name} label={name}>{ids.map(id => <option key={id} value={id}>{tools[id][0]}</option>)}</optgroup>)}</select></label>
  if (resultOnly) return <div className="inspector-content">{toolSelect}
    <p className="hint">{asset?.role === 'analysis' ? 'Die Auswertung steht auf der Arbeitsfläche.' : 'Für den Noteneditor wähle eine MIDI-Datei mit Noten.'}</p>
    {p.openSource && <button onClick={p.openSource}>Quelldatei öffnen</button>}
  </div>
  const options = (key: string, label: string, fallback: string, choices: [string, string][]) =>
    <label className="field"><span>{label}</span><select value={str(key, fallback)} onChange={event => change(key, event.target.value)}>
      {choices.map(([id, name]) => <option key={id} value={id}>{name}</option>)}
    </select></label>
  const field = (key: string, label: string, fallback: number, min: number, max: number, step = 1) =>
    <Num label={label} value={num(key, fallback)} min={min} max={max} step={step} onChange={value => change(key, value)} />
  const dial = (key: string, label: string, fallback: number, min: number, max: number, step = 1) =>
    <Dial label={label} value={num(key, fallback)} min={min} max={max} step={step} onChange={value => change(key, value)} />
  const check = (key: string, label: string, fallback = false) =>
    <Check checked={boolean(key, fallback)} onChange={value => change(key, value)}>{label}</Check>
  const checks = (key: string, defaults: string[], items: [string, string][]) => {
    const current = (settings[key] as string[] | undefined) ?? defaults
    return <div className="check-grid">{items.map(([id, label]) => <Check key={id} checked={current.includes(id)} onChange={enabled => change(key, enabled ? [...current, id] : current.filter(item => item !== id))}>{label}</Check>)}</div>
  }
  function submit(preview = false, keepTempo = false) {
    const params: Record<string, unknown> = { ...settings }
    for (const key of ['reference', 'count', 'snap', 'bars', 'mode_selection', 'fixedSeed']) delete params[key]
    if (tool === 'generation' && params.seed === undefined) params.seed = null
    if (tool === 'effects') Object.assign(params, { chain, tail })
    if (tool === 'stretch') {
      params.source_bpm = num('source_bpm', asset?.meta.bpm ?? project.bpm)
      params.target_bpm = keepTempo ? params.source_bpm : num('target_bpm', project.bpm)
      if (singleSource && sourceKey) params.source_key = sourceKey
    }
    if (tool === 'cut') params.cuts = p.slices
    if (tool === 'mix') params.tracks = Object.fromEntries(inputs.map(item => [item.id, p.tracks[item.id] || {}]))
    if (tool === 'midi') {
      params.view = settings.view ?? asset?.meta.midi
      params.origin = project.draft.downbeat ?? 0
    }
    if (tool === 'oneshot' || tool === 'loop') {
      let regions = tool === 'oneshot' && p.slices.length ? p.slices : region ? [region] : []
      if (tool === 'loop' && num('bars', 0) && region) {
        const [n, d] = project.meter.split('/').map(Number)
        regions = [{ ...region, end: Math.min(duration, region.start + Math.round(num('bars', 1) * n * 4 / d * 60 / project.bpm * rate)) }]
      }
      params.regions = regions.map(slice => ({ ...slice, fade_in: num('fade_in', 0), fade_out: num('fade_out', 0), snap_zero: boolean('snap_zero') }))
    }
    if ((preview || tool === 'basic_pitch') && region) {
      params.start = region.start
      params.end = preview ? Math.min(region.end, region.start + rate * (tool === 'audiosr' ? 15 : 30)) : region.end
    }
    if (preview) params.preview = true
    p.run(tool, inputs.map(item => item.id), params, num('count', 1))
  }

  const controls: Record<string, ReactNode> = {
    qa: <p className="hint">EBU R128 · Ergebnis enthält LUFS, LRA und True Peak. Messwerte erscheinen beim Analyse-Asset.</p>,
    separation: <>{checks('stems', ['vocals', 'drums', 'bass', 'other'], [['vocals', 'Gesang'], ['drums', 'Drums'], ['bass', 'Bass'], ['other', 'Begleitung'], ['instrumental', 'Instrumental']])}{check('tta', 'Zusätzliche Modellläufe (TTA)')}{check('coherent', 'Zusammengehörige SCNet-Gruppe ohne Instrumental')}<p className="hint">Die vorhandene Modellkombination verwendet Mel-Band für Gesang und SCNet für weitere Spuren.</p></>,
    detect: <>{options('mode', 'Analyse', 'loop', [['loop', 'Beat-Grid + Tonart'], ['oneshot', 'Grid + Anschläge + Tonart'], ['key', 'Nur Tonart']])}
      {str('mode', 'loop') === 'oneshot' && <div className="field-grid">{field('sensitivity', 'Schwelle', .07, .01, 1, .01)}{field('spacing', 'Abstand · ms', 100, 25, 2000)}{field('minimum', 'Mindestlänge · ms', 30, 10, 2000)}{field('pre', 'Vorlauf · ms', 8, 0, 100)}{field('tail', 'Ausklang · ms', 350, 30, 5000)}</div>}</>,
    loop: <>{options('bars', 'Looplänge', '0', [['0', 'Freie Region'], ...[1, 2, 4, 8, 16].map(n => [String(n), `${n} Takte ab Auswahlstart`] as [string, string])])}
      <div className="dial-grid">{dial('fade_in', 'Fade in · ms', 0, 0, 500)}{dial('fade_out', 'Fade out · ms', 0, 0, 500)}</div>{check('snap_zero', 'An nächsten Nulldurchgang setzen')}</>,
    oneshot: <><div className="dial-grid">{dial('fade_in', 'Fade in · ms', 0, 0, 500)}{dial('fade_out', 'Fade out · ms', 0, 0, 500)}</div>{check('snap_zero', 'An nächsten Nulldurchgang setzen')}</>,
    stretch: <>
      {singleSource && <div className="effect key-controls">
        <label className="field"><span>Quelltonart</span><select value={p.sourceKey ? `${p.sourceKey.mode}:${p.sourceKey.tonic}` : ''}
          onChange={event => { const [mode, tonic] = event.target.value.split(':'); p.setSourceKey(tonic === undefined ? undefined : { tonic: Number(tonic), mode: mode as TonalKey['mode'] }) }}>
          <option value="">{p.estimatedKey ? `Vorschlag · ${keyName(p.estimatedKey)}` : 'Tonart wählen …'}</option>
          {(['major', 'minor'] as const).flatMap(mode => pitchNames.map((_, tonic) => <option key={`${mode}:${tonic}`} value={`${mode}:${tonic}`}>{keyName({ mode, tonic })}</option>))}
        </select></label>
        {sourceKey && <><label className="field"><span>Zieltonart</span><select value={currentTonic} onChange={event => change('pitch', (Number(event.target.value) - sourceKey.tonic + 18) % 12 - 6)}>
          {currentTonic === '' && <option value="" disabled>Feinstimmung aktiv</option>}
          {pitchNames.map((_, tonic) => <option key={tonic} value={tonic}>{keyName({ tonic, mode: sourceKey.mode })}</option>)}
        </select></label><small>Dur oder Moll bleibt bei der Transposition erhalten.</small><button disabled={disabled || currentTonic === '' || !pitch} onClick={() => submit(false, true)}>Tonart rendern · Tempo beibehalten</button></>}
      </div>}
      {field('source_bpm', 'Quell-BPM', asset?.meta.bpm ?? project.bpm, 30, 300, .01)}<div className="dial-grid">{dial('target_bpm', 'Zieltempo · BPM', project.bpm, 30, 300, .01)}{dial('pitch', 'Tonhöhe · HT', 0, -12, 12, .01)}</div>{check('formant', 'Formanten erhalten')}</>,
    transcription: checks('tasks', ['melody', 'drums', 'chords', 'beat'], [['melody', 'Melodie / Instrumente'], ['drums', 'Drums'], ['chords', 'Akkorde / Tonart'], ['beat', 'Beat / Tempo']]),
    basic_pitch: <p className="hint">MIDI bezieht sich auf die gewählte Audioauswahl. Am besten eine isolierte Bass- oder Melodiespur verwenden.</p>,
    midi: <div className="field-grid">{field('quantize', 'Quantisierung (0–1)', 0, 0, 1, .05)}{field('transpose', 'Halbtöne', 0, -12, 12)}{field('clip_start', 'MIDI-Start · s', 0, 0, 1800, .01)}{field('clip_end', 'MIDI-Ende · s', 1800, 0, 1800, .01)}</div>,
    effects: <>
      {rackStep && <section className="rack-surface fx-module" data-effect={rackStep.effect} aria-label="Effektrack">
        <div className="rack-heading"><strong>{effectTitle(rackStep.effect)}</strong>
          <button className="plain" type="button" aria-label="Display vergrößern" title="Display vergrößern" aria-expanded={p.rack.expanded} onClick={p.rack.expand}><Maximize2 size={15} /></button>
        </div>
        <FxScope running={p.rack.running} read={p.rack.read} />
        <EffectDials key={rackIndex + rackStep.effect} step={rackStep} change={replaceStep} />
        <div className="rack-preview"><button type="button" className="primary" disabled={!p.rack.playback} onClick={p.rack.playback}>{p.rack.playing ? 'Live pausieren' : 'Live hören'}</button>
          <small role="status">{p.rack.status}</small></div>
      </section>}
      <div className="rack-chain" role="group" aria-label="Signalweg">{chain.map((entry, index) => {
        const Glyph = pluginModules[entry.effect as keyof typeof pluginModules]?.glyph ?? AudioLines
        const title = effectTitle(entry.effect)
        function move(direction: number) {
          const destination = index + direction
          const copy = [...chain]
          ;[copy[index], copy[destination]] = [copy[destination], copy[index]]
          change('chain', copy)
          p.rack.select(index === rackIndex ? destination : destination === rackIndex ? index : rackIndex)
        }
        return <div className="rack-step fx-module" data-effect={entry.effect} data-bypass={Boolean(entry.bypass)} key={index}>
          <button className="rack-step-name" type="button" aria-pressed={index === rackIndex} onClick={() => p.rack.select(index)}><Glyph size={15} />{title}</button>
          <button className="plain" aria-label={`Bypass ${title}`} aria-pressed={Boolean(entry.bypass)} onClick={() => change('chain', chain.map((item, at) => at === index ? { ...entry, bypass: !entry.bypass } : item))}><Power size={14} /></button>
          <button className="plain" aria-label={`${title} nach oben`} disabled={!index} onClick={() => move(-1)}>↑</button>
          <button className="plain" aria-label={`${title} nach unten`} disabled={index === chain.length - 1} onClick={() => move(1)}>↓</button>
          <button className="plain" aria-label={`${title} entfernen`} onClick={() => { change('chain', chain.filter((_, at) => at !== index)); if (index < rackIndex) p.rack.select(rackIndex - 1) }}>×</button>
        </div>
      })}</div>
      <label className="field"><span>Effekt hinzufügen</span><select value="" onChange={event => addStep(event.target.value)} disabled={chain.length >= 12 || !!project.archived}>
        <option value="" disabled>Effekt wählen</option>
        <optgroup label="VST3">{Object.entries(pluginModules).map(([id, module]) => <option key={id} value={id} disabled={!readyPlugins[id]}>{module.name}</option>)}</optgroup>
        <optgroup label="Studio-Effekte">{Object.entries(effectName).map(([id, label]) => <option key={id} value={id}>{label}</option>)}</optgroup>
      </select></label>
      <div className="inline">{field('tail', 'WAV-Ausklang · s', tail, 0, 5, .1)}{rackStep && <button type="button" className="plain" onClick={() => replaceStep({ effect: rackStep.effect, bypass: rackStep.bypass })}>Zurücksetzen</button>}</div>
    </>,
    mix: <div className="chain">{inputs.filter(audio).map(item => {
      const track = p.tracks[item.id] ?? { gain: 0, pan: 0, offset: 0, mute: false, solo: false }
      const set = (key: keyof Track, value: number | boolean) => p.setTrack(item.id, { ...track, [key]: value })
      return <div className="effect" key={item.id}><strong>{item.name}</strong><div className="field-grid">
        <Num label="Gain · dB" value={track.gain} min={-60} max={12} onChange={value => set('gain', value)} />
        <Num label="Panorama" value={track.pan} min={-1} max={1} step={.05} onChange={value => set('pan', value)} />
        <Num label="Projektstart · s" value={track.offset / project.rate} min={0} max={1800} step={.01} onChange={value => set('offset', Math.round(value * project.rate))} />
        <Num label="Clipstart · s" value={(track.start ?? 0) / item.meta.rate!} min={0} max={item.meta.seconds} step={.01} onChange={value => set('start', Math.round(value * item.meta.rate!))} />
        <Num label="Clipende · s" value={(track.end ?? item.meta.samples!) / item.meta.rate!} min={0} max={item.meta.seconds} step={.01} onChange={value => set('end', Math.round(value * item.meta.rate!))} />
        <div><Check checked={track.solo} onChange={value => set('solo', value)}>Solo</Check><Check checked={track.mute} onChange={value => set('mute', value)}>Mute</Check></div>
      </div></div>
    })}</div>,
    mastering: <>{options('intensity', 'Intensität', 'medium', [['low', 'Sanft'], ['medium', 'Mittel'], ['high', 'Stark']])}
      <div className="dial-grid">{dial('lufs', 'Lautheit · LUFS', -14, -30, -8, .1)}{dial('true_peak', 'True Peak · dBTP', -1, -6, -.1, .1)}</div></>,
    reference: <>{options('reference', 'Referenz im Projekt', defaultReference?.id || '', refs.length ? refs.map(item => [item.id, item.name]) : [['', 'Referenzdatei importieren']])}</>,
    enhancement: <>{check('suggestions', 'Transkript und Schnittvorschläge anfragen')}{check('disturbances', 'Störgeräusche zur Prüfung markieren (AST)')}</>,
    deepfilter: <p className="hint">Denoising mit Delay-Kompensation. Die Originaldatei bleibt im Projekt.</p>,
    rnnoise: <p className="hint">Sprache wird für den Modelllauf in 48 kHz Mono konvertiert.</p>,
    cut: <p className="hint">Im Arbeitsbereich einzelne Pausen oder erkannte Stellen zur Schnittliste hinzufügen. Nur die ausgewählten Bereiche werden entfernt.</p>,
    generation: <><label className="field"><span>Prompt</span><textarea rows={4} maxLength={800} value={str('prompt', '')} onChange={event => change('prompt', event.target.value)} placeholder="Trockene analoge Percussion mit kurzem metallischem Ausklang" /></label>
      <label className="field"><span>Negativprompt</span><textarea rows={2} maxLength={800} value={str('negative', '')} onChange={event => change('negative', event.target.value)} placeholder="Optional" /></label>
      <div className="field-grid">{field('seconds', 'Dauer · s', 8, 1, p.caps?.generation_seconds || 47, .5)}{field('count', 'Takes', 1, 1, 3)}{settings.seed !== null && settings.seed !== undefined && field('seed', 'Seed', 42, 0, 2147483645)}<Check checked={settings.seed != null} onChange={enabled => change('seed', enabled ? 42 : null)}>Fester Seed</Check></div>
      <details><summary>Modellparameter</summary><div className="field-grid">{field('steps', 'Schritte', 50, 10, 100)}{field('guidance', 'Guidance', 7, 1, 12, .1)}</div></details></>,
    audiosr: <>{field('seed', 'Seed', 42, 0, 2147483647)}<p className="hint">Ergänzt mögliche hohe Frequenzen. Ausgabe in Mono bei 48 kHz als getrennte Variante.</p></>,
  }

  return <div className="inspector-content">
    {toolSelect}
    <div className="tool-heading"><span className={cloud.has(tool) ? 'mode cloud' : 'mode'}>{tool === 'audiosr' ? 'Privates Modal · Experiment' : cloud.has(tool) ? 'Privates Modal' : p.caps?.online ? 'Workspace-Server' : 'Lokal'}</span><h2>{title}</h2><p>{description}</p></div>
    {needsAudio && tool !== 'mix' && <p className="input-chip">{inputs.length > 1 ? `${inputs.length} Eingaben` : asset ? asset.name : 'Wähle ein Audio-Asset'}</p>}
    <section className="controls">{controls[tool]}</section>
    <div className="render-actions">
      {pluginMissing && <p className="notice">Ein VST3 fehlt lokal. Du kannst das Modul im Rack auf Bypass setzen.</p>}
      {tool === 'effects' && <button disabled={disabled || !p.rack.render} onClick={p.rack.render}>Ausschnitt als WAV speichern</button>}
      {['stretch', 'deepfilter', 'rnnoise'].includes(tool) && <button disabled={disabled || !region || (tool === 'stretch' && inputs.length > 1)} onClick={() => submit(true)}>Auswahlvorschau rendern</button>}
      <button className="primary" disabled={disabled} onClick={() => submit(tool === 'audiosr')}>{action}</button>
      {disabled && !p.busy && <p className="hint">{project.archived ? 'Aktiviere das Projekt zuerst wieder.' : !ready ? 'Diese Engine ist in der lokalen Installation noch nicht eingerichtet.' : cloud.has(tool) && project.purpose === 'release' ? 'Für Veröffentlichungsprojekte ist dieses Modell hier nicht freigegeben.' : identicalReference ? 'Mix und Referenz enthalten dasselbe Audio. Wähle eine andere Referenzspur.' : tool === 'reference' && inputs.length !== 2 ? 'Wähle einen Mix und importiere eine Referenz.' : tool === 'cut' ? 'Füge mindestens einen bestätigten Schnitt hinzu.' : tool === 'effects' && !chain.length ? 'Füge mindestens einen Effekt hinzu.' : tool === 'generation' ? 'Gib einen Prompt ein.' : 'Wähle passendes Projektmaterial.'}</p>}
    </div>
  </div>
}
