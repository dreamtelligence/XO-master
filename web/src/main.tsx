import { createRoot } from 'react-dom/client'
import { AudioLines, ArrowDownToLine, ArrowRight, AudioWaveform, BookOpen, ChevronDown, Disc3, FolderOpen, Import, Layers3, LockKeyhole, Mic, Pause, Play, Plus, Repeat2, SlidersHorizontal, Sparkles, Square } from 'lucide-react'
import { QueryClient, QueryClientProvider, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useMemo, useRef, useState } from 'react'
import { api, assetUrl, audio, keyName, midiHasNotes, terminal, tonalKey, upload, type Asset, type Capabilities, type Draft, type EffectStep, type Midi, type Project, type Region, type Role, type Workspace } from './api'
import { Piano, RegionEditor, TimelineRuler, TransportTime, Wave } from './editor'
import { Dial, OutputMeter } from './controls'
import { FxCompare, FxScope, type FxSide } from './fx'
import { Handbook } from './manual'
import { AnalysisResult, ResultMetrics, resultName, TempoMap } from './results'
import studioGlass from './assets/studio-glass.jpg'
import { Check, EffectDials, effectParameters, effectTitle, pluginModules, Inspector, Num, templates, tools } from './tools'
import { seconds, selectionSeconds, sourcesFor, useTransport, type Source } from './transport'
import './studio.css'

const client = new QueryClient({ defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } } })
const roleLabels: Record<Role, string> = { original: 'Original', reference: 'Referenz', stem: 'Stem', variant: 'Variante', loop: 'Loop', oneshot: 'One-Shot', midi: 'MIDI', take: 'Take', analysis: 'Analyse', export: 'Paket' }
const stateLabels: Record<string, string> = { queued: 'Wartet', blocked: 'Wartet auf Eingang', running: 'Läuft', finalizing: 'Prüft', completed: 'Fertig', failed: 'Fehler', partial: 'Teilweise fertig', cancelled: 'Abgebrochen', offline: 'Verbindung unterbrochen', submission_unknown: 'Start unbestätigt', output_unconfirmed: 'Ausgabe unbestätigt' }
const contextKey = 'xo-workspace-project'
const templateIcons = { remix: Layers3, mix: SlidersHorizontal, speech: Mic, generate: Sparkles }
function BrandMark() { return <span className="brand-mark" aria-hidden="true"><AudioLines size={21} /></span> }
function Brand() { return <div className="brand"><BrandMark /><span>Dreamtelligence<small>Artist Workspace</small></span></div> }

function App() {
  const [project, setProject] = useState(() => localStorage.getItem(contextKey) || '')
  const [error, setError] = useState('')
  const [pending, setPending] = useState('')
  const openFile = useRef<HTMLInputElement>(null)
  const inputPackage = useRef<HTMLInputElement>(null)
  const handbook = useRef<HTMLDialogElement>(null)
  const openHandbook = () => handbook.current?.showModal()
  const query = useQueryClient()
  const projects = useQuery({ queryKey: ['projects'], queryFn: () => api<Project[]>('/projects') })
  const caps = useQuery({ queryKey: ['capabilities'], queryFn: () => api<Capabilities>('/capabilities') })
  function open(id: string) {
    setProject(id)
    if (id) localStorage.setItem(contextKey, id); else localStorage.removeItem(contextKey)
  }
  async function create(template?: string, files?: File[]) {
    if (pending) return
    if (files && files.reduce((size, file) => size + file.size, 0) > 2 * 1024 ** 3) { setError('Pro Import sind bis zu 2 GiB möglich.'); return }
    setError('')
    try {
      const plan = templates.find(item => item.id === template)
      setPending('Projekt wird angelegt …')
      const created = await api<Project>('/projects', 'POST', { name: files?.[0]?.name.replace(/\.[^.]+$/, '') || plan?.title || 'Neues Projekt', template: template || 'empty' })
      open(created.id)
      void query.invalidateQueries({ queryKey: ['projects'] })
      for (const file of files ?? []) {
        try { await upload<Asset>(`/projects/${created.id}/assets?filename=${encodeURIComponent(file.name)}`, file, progress => setPending(progress === 100 ? `${file.name} wird geprüft …` : `${file.name} wird importiert${progress == null ? '' : ` · ${progress}%`}`)) }
        catch (problem) { setError(`${file.name}: ${(problem as Error).message}`) }
      }
      void query.invalidateQueries({ queryKey: ['workspace', created.id] })
    } catch (problem) { setError((problem as Error).message) }
    finally { setPending('') }
  }
  return <>
    {project ? <ProjectView key={project} id={project} back={() => open('')} open={open} caps={caps.data} sharedPending={pending} openHandbook={openHandbook} />
      : <main className="welcome" onDragOver={event => { event.preventDefault() }} onDrop={event => { event.preventDefault(); const files = Array.from(event.dataTransfer.files); if (files.length) void create(undefined, files) }}>
      <header className="welcome-header"><Brand /><div className="welcome-header-actions"><span className="session-mark"><LockKeyhole size={13} aria-hidden="true" /> Privater Arbeitsbereich</span><button onClick={openHandbook}><BookOpen size={16} aria-hidden="true" /> Handbuch</button></div></header>
      <section className="welcome-main"><div className="welcome-hero">
        <div className="welcome-copy"><h1>Artist<br />Workspace<span>.</span></h1><p>Bearbeite Spuren, höre Varianten im Vergleich und exportiere Audio und MIDI für deine DAW.</p>
          <div className="inline"><button className="primary import-main" disabled={!!pending} onClick={() => openFile.current?.click()}><Import size={17} aria-hidden="true" /> Dateien importieren</button><button disabled={!!pending} onClick={() => void create()}><Plus size={16} aria-hidden="true" /> Leeres Projekt</button></div>
          <input hidden ref={openFile} type="file" accept="audio/*,.flac,.aiff,.wav" multiple onChange={event => { const files = Array.from(event.target.files ?? []); if (files.length) void create(undefined, files); event.target.value = '' }} />
        </div>
        <div className="hero-visual"><img src={studioGlass} alt="" width={1280} height={854} fetchPriority="high" /></div>
      </div>
      <section className="start-templates"><h2>Mit Vorlage starten</h2><div className="template-grid">{templates.map(item => {
        const Icon = templateIcons[item.id as keyof typeof templateIcons]
        return <button key={item.id} className={`template ${item.id}`} disabled={!!pending} onClick={() => void create(item.id)}>
          <span className="template-top"><span className="template-icon"><Icon size={21} aria-hidden="true" /></span><ArrowRight className="arrow" size={16} aria-hidden="true" /></span>
          <span><strong>{item.title}</strong><small>{item.detail}</small></span>
        </button>
      })}</div></section>
      <section className="recent"><div className="inline section-heading"><h2>Lokale Projekte</h2><button disabled={!!pending} onClick={() => inputPackage.current?.click()}><FolderOpen size={15} aria-hidden="true" /> Projektpaket öffnen</button></div>
        <input hidden ref={inputPackage} type="file" accept=".zip" onChange={async event => {
          const file = event.target.files?.[0]; event.target.value = ''
          if (!file) return
          setPending('Projektpaket wird geprüft …')
          try { const restored = await upload<Project>('/projects/import-package', file, () => {}); await query.invalidateQueries({ queryKey: ['projects'] }); open(restored.id) }
          catch (problem) { setError((problem as Error).message) }
          finally { setPending('') }
        }} />
        {projects.error ? <p className="notice">{projects.error.message}</p> : projects.data?.length ? <div className="project-list">{projects.data.map(item => <button key={item.id} onClick={() => open(item.id)}><strong>{item.name}</strong><span>{item.archived ? 'Archiviert' : `${item.bpm} BPM · ${item.meter}`}</span></button>)}</div> : <p className="hint">{projects.isPending ? 'Projekte werden geladen …' : 'Importierte und neu angelegte Projekte erscheinen hier.'}</p>}
      </section></section>
      {caps.data?.legacy && <a href="http://localhost:8766">Geschützten Legacy-Modus öffnen</a>}
    </main>}
    {(pending || error) && <div className={`toast ${error ? 'error' : ''}`} role={error ? 'alert' : 'status'}>{error || pending}{error && <button aria-label="Fehler schließen" onClick={() => setError('')}>×</button>}</div>}
    <Handbook dialogRef={handbook} />
  </>
}

function ProjectView({ id, back, open, caps, sharedPending, openHandbook }: { id: string; back: () => void; open: (id: string) => void; caps?: Capabilities; sharedPending: string; openHandbook: () => void }) {
  const query = useQueryClient()
  const data = useQuery({ queryKey: ['workspace', id], queryFn: () => api<Workspace>(`/projects/${id}`),
    refetchInterval: q => q.state.data?.jobs.some(job => !terminal.has(job.state)) ? 1000 : false })
  if (!data.data) return <main className="welcome"><Brand /><p className={data.error ? 'notice' : 'hint'}>{data.error?.message || 'Projekt wird geladen …'}</p><button onClick={back}>Zu den Projekten</button></main>
  return <WorkspaceView current={data.data} id={id} back={back} open={open} caps={caps} sharedPending={sharedPending} openHandbook={openHandbook} refresh={() => query.invalidateQueries({ queryKey: ['workspace', id] })} />
}

type Editable = Pick<Project, 'name' | 'rate' | 'meter' | 'purpose' | 'bpm'> & { draft: Draft; archived: boolean }

function WorkspaceView({ current, id, back, open, caps, sharedPending, refresh, openHandbook }: { current: Workspace; id: string; back: () => void; open: (id: string) => void; caps?: Capabilities; sharedPending: string; refresh: () => Promise<void>; openHandbook: () => void }) {
  const query = useQueryClient()
  const editable = (project: Project): Editable => ({ name: project.name, rate: project.rate, meter: project.meter, purpose: project.purpose, bpm: project.bpm, draft: project.draft, archived: !!project.archived })
  const [edit, setEdit] = useState(() => editable(current.project))
  const revision = useRef(current.project.revision)
  const saved = useRef(JSON.stringify(edit))
  const saving = useRef<Promise<void> | null>(null)
  const saveRejected = useRef(false)
  const undoStack = useRef<Editable[]>([])
  const redoStack = useRef<Editable[]>([])
  const [saveState, setSaveState] = useState('Gespeichert')
  const [active, setActive] = useState('')
  const [selection, setSelection] = useState<string[]>([])
  const [cart, setCart] = useState<string[]>([])
  const [pane, setPane] = useState<'library' | 'inspector' | ''>(() => window.innerWidth >= 900 ? 'library' : '')
  const [hideLibrary, setHideLibrary] = useState(false)
  const [hideInspector, setHideInspector] = useState(false)
  const [libraryWidth, setLibraryWidth] = useState(260)
  const [inspectorWidth, setInspectorWidth] = useState(340)
  const [projectMenu, setProjectMenu] = useState(false)
  const [exportMenu, setExportMenu] = useState(false)
  const [queue, setQueue] = useState(false)
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState<Role | 'all'>('all')
  const [error, setError] = useState('')
  const [pending, setPending] = useState('')
  const [running, setRunning] = useState(false)
  const [loop, setLoop] = useState(false)
  const [matched, setMatched] = useState(false)
  const [side, setSide] = useState<'base' | 'new'>('new')
  const [fxPlayback, setFxPlayback] = useState<{ id: string; side: FxSide } | null>(null)
  const [liveSide, setLiveSide] = useState<FxSide>('wet')
  const [rackExpanded, setRackExpanded] = useState(false)
  const [rackIndex, setRackIndex] = useState(0)
  const [audition, setAudition] = useState<{ id: string; start: number }>()
  const liveClip = useRef('')
  const rackPanel = useRef<HTMLElement>(null)
  const [fxMatched, setFxMatched] = useState(true)
  const [zoom, setZoom] = useState(1)
  const [bars, setBars] = useState(false)
  const [format, setFormat] = useState('pcm24')
  const [align, setAlign] = useState(true)
  const [strict, setStrict] = useState(false)
  const file = useRef<HTMLInputElement>(null)
  const role = useRef<'original' | 'reference'>('original')
  const dialog = useRef<HTMLDialogElement>(null)
  const pendingRun = useRef<{ signature: string; id: string; revision: number } | null>(null)
  const submitting = useRef(false)

  const player = useTransport(setError)
  const monitorTracks = useRef<Asset[]>([])
  const all = current.assets.filter(asset => !asset.hidden)
  const assets = all.filter(asset => asset.role !== 'export')
  const asset = assets.find(item => item.id === active) ?? (edit.draft.tool === 'effects'
    ? assets.find(item => audio(item) && !(item.meta.preview_render && item.meta.operation?.tool === 'effects')) : undefined)
    ?? assets.find(audio) ?? assets[0]
  const selected = selection.map(key => assets.find(item => item.id === key)).filter((x): x is Asset => !!x)
  const viewedTracks = selected.filter(audio).length ? selected.filter(audio) : audio(asset)
    ? asset.meta.group ? assets.filter(item => item.meta.group === asset.meta.group && audio(item)) : [asset] : []
  const tracks = edit.draft.tracks ?? {}
  const source = asset?.parents.map(parent => assets.find(item => item.id === parent)).find(audio)
  const bpm = edit.bpm
  const mark = edit.draft.downbeat ?? 0
  const [meterN, meterD] = edit.meter.split('/').map(Number)
  const beat = 60 / bpm * 4 / meterD
  const duration = Math.max(1, ...viewedTracks.map(item => (item.meta.seconds ?? 0) + ((tracks[item.id]?.offset ?? item.meta.project_offset ?? 0) / edit.rate)))
  const beatLines = useMemo(() => Array.from({ length: Math.min(2200, Math.max(0, Math.floor((duration - mark) / beat) + 1)) }, (_, i) => mark + beat * i), [duration, mark, beat])
  const trackSettings = (item: Asset) => tracks[item.id] ?? { gain: 0, pan: 0, offset: item.meta.project_offset ?? 0, mute: false, solo: false }
  const singleSettings = (key: string) => (edit.draft.settings?.[key] as Record<string, unknown> | undefined) ?? {}
  const defaultTool = templates.find(item => item.id === edit.draft.template)?.recipe[0]
  const tool = edit.draft.tool || defaultTool || (asset?.role === 'midi' ? 'midi' : 'qa')
  const settings = singleSettings(tool)
  const region = audio(asset) ? edit.draft.regions?.[asset.id] ?? { start: 0, end: asset.meta.samples! } : undefined
  const fxSource = tool === 'effects' && audio(asset) ? asset : undefined
  const liveId = fxSource && region ? `${fxSource.id}:${region.start}:${region.end}` : ''
  const auditionStart = audition?.id === liveId ? audition.start : region?.start
  const fxParams = fxSource && region && auditionStart !== undefined ? { ...effectParameters(settings), preview: true,
    start: auditionStart, end: Math.min(region.end, auditionStart + fxSource.meta.rate * 30),
  } : undefined
  const fxWindow = fxSource && fxParams ? selectionSeconds(fxSource, fxParams) : undefined
  const rackAt = Math.min(rackIndex, (fxParams?.chain.length ?? 0) - 1)
  const rackStep = fxParams?.chain[rackAt]
  const readyForLive = Boolean(caps?.live_effects && fxWindow && fxParams?.chain.length && fxParams.chain.every(step =>
    step.bypass || !Object.hasOwn(pluginModules, step.effect) || !!caps.effect_plugins?.[step.effect]))
  const liveStatus = player.liveActive ? (player.loading ? 'Live-Vorschau puffert …' : 'Echtzeit aktiv') : readyForLive ? 'Live-Vorschau bereit' : 'Live-Vorschau nicht verfügbar'
  const fxJobs = fxSource ? current.jobs.filter(job => job.tool === 'effects' && job.inputs[0] === fxSource.id && job.params.preview === true) : []
  const fxCurrent = fxParams && fxJobs.find(({ params }) => {
    const sameLength = params.start === fxParams.start && params.end === fxParams.end && (params.tail ?? 0) === fxParams.tail
    const previous = params.chain
    return sameLength && Array.isArray(previous) && previous.length === fxParams.chain.length && fxParams.chain.every((step, index) =>
      previous[index] && typeof previous[index] === 'object' && Object.keys(step).length === Object.keys(previous[index]).length &&
      Object.entries(step).every(([key, value]) => previous[index][key] === value))
  })
  const fxWet = fxCurrent?.state === 'completed' ? assets.find(item => item.job === fxCurrent.id && audio(item)) : undefined
  const fxBusy = fxCurrent && !terminal.has(fxCurrent.state)
  const fxId = fxSource && fxParams ? `${fxSource.id}:${fxParams.start}:${fxParams.end}:${fxWet?.id ?? ''}` : ''
  const fxSide = fxPlayback?.id === fxId ? fxPlayback.side : null
  const fxStart = fxWindow && fxSource ? fxWindow[0] + (tracks[fxSource.id]?.offset ?? fxSource.meta.project_offset ?? 0) / edit.rate : 0
  const fxDuration = fxWindow ? fxWindow[1] - fxWindow[0] : 0
  const waveClock = useMemo(() => fxSide ? {
    subscribe: player.position.subscribe,
    current: () => fxStart + Math.min(fxDuration, player.position.current()),
  } : player.position, [fxSide, fxStart, fxDuration, player.position])
  const regionGroup = asset ? `regions:${asset.id}:${tool === 'cut' ? 'cuts' : 'slices'}` : ''
  const slices = (asset && singleSettings(regionGroup).slices as Region[] | undefined) || []
  const analysis = audio(asset) ? assets.find(item => item.role === 'analysis' && item.parents.includes(asset.id) && typeof item.meta.report?.bpm === 'number') : undefined
  const keyReport = audio(asset) ? assets.find(item => item.role === 'analysis' && item.parents.includes(asset.id) && item.meta.report?.origin === 'librosa' && 'key' in item.meta.report) : undefined
  const keyGroup = `tonart:${asset?.id}`
  const sourceKey = tonalKey(singleSettings(keyGroup).source)
  const estimatedKey = tonalKey(keyReport ? keyReport.meta.report?.key : asset?.meta.key)
  const displayKey = sourceKey ?? estimatedKey
  const keyBusy = current.jobs.some(job => job.tool === 'detect' && job.inputs[0] === asset?.id && !terminal.has(job.state))
  const suggestions = audio(asset) ? assets.find(item => item.role === 'analysis' && item.parents.includes(asset.id) && Array.isArray(item.meta.report?.regions)) : undefined
  const cloudSpeech = audio(asset) ? assets.find(item => item.role === 'analysis' && item.parents.includes(asset.id) && Array.isArray(item.meta.report?.suggestions)) : undefined
  const speechProposals = (cloudSpeech?.meta.report?.suggestions as {start: number; end: number; kind: string; text?: string}[] | undefined)?.map(item => ({
    name: item.text || (item.kind === 'pause' ? 'Pause' : item.kind), start: Math.round(item.start * asset!.meta.rate!),
    end: Math.min(asset!.meta.samples!, Math.round(item.end * asset!.meta.rate!)),
  })).filter(item => item.end > item.start) ?? []
  const silence = audio(asset) ? assets.find(item => item.role === 'analysis' && item.parents.includes(asset.id) && Array.isArray(item.meta.report?.silence)) : undefined
  const detectCuts = (silence?.meta.report?.silence as [number, number][] | undefined)?.map(([start, end], index) => ({
    name: `Pause ${index + 1}`, start: Math.round(start * asset!.meta.rate!), end: Math.min(asset!.meta.samples!, Math.round(end * asset!.meta.rate!)),
  })).filter(item => item.end > item.start) ?? []
  const detected = tool === 'cut' ? (speechProposals.length ? speechProposals : detectCuts) : (suggestions?.meta.report?.regions as Region[] | undefined) ?? []
  const isNew = current.jobs.some(job => !terminal.has(job.state))
  const librarySearch = search.trim().toLowerCase()
  const filtered = assets.filter(item => (filter === 'all' || item.role === filter) &&
    (item.name.toLowerCase().includes(librarySearch) || resultName(item).toLowerCase().includes(librarySearch)))
  const midiView = asset?.role === 'midi' ? singleSettings(`midi:${asset.id}`).view as Midi | undefined : undefined
  const hasMidiNotes = midiHasNotes(midiView ?? asset?.meta.midi)
  const canPlay = audio(asset) || hasMidiNotes
  const project: Project = { ...current.project, ...edit, archived: Number(edit.archived) }
  const parentJob = current.jobs.find(job => job.id === asset?.job)
  const stalePreview = asset?.meta.preview_render && asset.meta.operation?.tool === tool &&
    Object.entries(settings).some(([key, value]) => JSON.stringify(value) !== JSON.stringify(asset.meta.operation?.parameters[key]))
  const [abortMessage, setAbortMessage] = useState('')
  const storage = useQuery({ queryKey: ['storage'], queryFn: () => api<{ preview_bytes: number; used_bytes: number; budget_bytes: number }>('/storage'), enabled: projectMenu })

  function update(next: Editable) {
    undoStack.current = [...undoStack.current.slice(-29), edit]
    redoStack.current = []
    saveRejected.current = false
    setEdit(next)
    setSaveState('Speichert …')
  }
  function undo(redo = false) {
    const from = redo ? redoStack : undoStack, to = redo ? undoStack : redoStack
    const value = from.current.pop()
    if (value) { to.current.push(edit); saveRejected.current = false; setEdit(value); setSaveState('Speichert …') }
  }
  function draft(next: Partial<Draft>) { update({ ...edit, draft: { ...edit.draft, ...next } }) }
  function config(key: string, value: unknown, group = tool) { draft({ settings: { ...edit.draft.settings, [group]: { ...singleSettings(group), [key]: value } } }) }
  function setRegion(value: Region) { if (asset) draft({ regions: { ...edit.draft.regions, [asset.id]: value } }) }

  async function persist(value: Editable) {
    await saving.current
    const text = JSON.stringify(value)
    if (saved.current === text) return
    saving.current = (async () => {
      try {
        const server = await api<Project>(`/projects/${id}`, 'PATCH', { ...value, revision: revision.current })
        revision.current = server.revision
        saved.current = text
        setSaveState('Gespeichert')
        void refresh()
        void query.invalidateQueries({ queryKey: ['projects'] })
      } catch (problem) {
        saveRejected.current = true
        setSaveState('Nicht gespeichert')
        throw problem
      }
    })()
    try { await saving.current }
    finally { saving.current = null }
  }
  useEffect(() => {
    if (JSON.stringify(edit) === saved.current || saving.current || saveRejected.current) return
    const timer = setTimeout(() => void persist(edit).catch(problem => setError((problem as Error).message)), 480)
    return () => clearTimeout(timer)
  }, [id, edit, current.project.revision, saveState])

  useEffect(() => {
    if (exportMenu) dialog.current?.showModal()
    else dialog.current?.close()
  }, [exportMenu])

  useEffect(() => {
    if (fxPlayback && fxPlayback.id !== fxId) { player.pause(); player.seek(0); setFxPlayback(null) }
  }, [fxPlayback, fxId])

  useEffect(() => {
    if (player.liveActive && (liveId !== liveClip.current || !readyForLive)) player.pause()
  }, [player.liveActive, liveId, readyForLive])

  useEffect(() => {
    if (fxParams?.chain.length) player.updateLive(fxParams.chain, loop)
  }, [fxParams?.chain, loop, player.liveActive])

  function pick(item: Asset) {
    if (asset?.id !== item.id) { player.pause(); player.seek(0); setSide('new'); setFxPlayback(null) }
    setActive(item.id)
    if (item.role === 'midi' && midiHasNotes(item.meta.midi) && tool !== 'midi') draft({ tool: 'midi' })
  }
  function choose(tool: string) {
    draft({ tool })
    setHideInspector(false)
    setPane('inspector')
  }
  function toggle(array: string[], value: string) { return array.includes(value) ? array.filter(item => item !== value) : [...array, value] }

  async function submit(tool: string, inputs: string[], params: Record<string, unknown>, count = 1) {
    if (submitting.current) return
    if (tool === 'effects' && params.preview && asset && asset.id === inputs[0]) setActive(asset.id)
    submitting.current = true
    setRunning(true)
    try {
      const signature = JSON.stringify([tool, inputs, params, count, edit])
      await persist(edit)
      const pending = pendingRun.current?.signature === signature ? pendingRun.current
        : { signature, id: crypto.randomUUID(), revision: revision.current }
      pendingRun.current = pending
      const request = { id: pending.id, tool, inputs, params, count, draft_revision: pending.revision }
      if (tool !== 'export') await api(`/projects/${id}/runs/validate`, 'POST', request)
      await api(`/projects/${id}/${tool === 'export' ? 'exports' : 'runs'}`, 'POST', request)
      pendingRun.current = null
      setQueue(true)
      setExportMenu(false)
      await refresh()
    } catch (problem) { setError((problem as Error).message) }
    finally { submitting.current = false; setRunning(false) }
  }
  async function importFiles(files: File[]) {
    if (!files.length || pending || edit.archived) return
    if (files.reduce((size, file) => size + file.size, 0) > 2 * 1024 ** 3) { setError('Pro Import sind bis zu 2 GiB möglich.'); return }
    setPending('Import wird vorbereitet …')
    try {
      let latest: Asset | undefined
      for (const entry of files) {
        try {
          latest = await upload<Asset>(`/projects/${id}/assets?filename=${encodeURIComponent(entry.name)}&role=${role.current}`, entry,
            percent => setPending(percent === 100 ? `${entry.name} wird geprüft …` : `${entry.name} wird importiert · ${percent ?? '…'}%`))
        } catch (problem) { setError(`${entry.name}: ${(problem as Error).message}`) }
      }
      await refresh()
      if (latest) pick(latest)
    } finally { setPending('') }
  }
  async function mutateAsset(item: Asset, params: object) {
    try { await api(`/projects/${id}/assets/${item.id}`, 'PATCH', params); await refresh() }
    catch (problem) { setError((problem as Error).message) }
  }
  function listen(specific?: Region, at?: number, which = side, loopEnabled = loop) {
    setFxPlayback(null)
    monitorTracks.current = []
    if (asset?.role === 'midi') {
      if (hasMidiNotes) void player.playMidi({ ...asset, meta: { ...asset.meta, midi: midiView ?? asset.meta.midi } }, at ?? player.cursor.current)
      return
    }
    if (!audio(asset)) return
    const item = asset
    const dry = specific || (source && which === 'base') ? [item] : viewedTracks
    const from = specific ? specific.start / item.meta.rate! : loopEnabled && region ? region.start / item.meta.rate! : 0
    const to = specific ? specific.end / item.meta.rate! : loopEnabled && region ? region.end / item.meta.rate! : dry.length === 1 ? item.meta.seconds! : duration
    const target = Math.max(from, Math.min(to - .0001, at ?? player.cursor.current))
    let playing = sourcesFor(dry, tracks, edit.rate)
    if (!specific && which === 'new' && !(matched && source)) monitorTracks.current = dry
    if (dry.length === 1 && (specific || source)) playing = [{ asset: item, gain: 1 }]
    if (source && which === 'base') {
      const inputRate = item.meta.source_rate ?? source.meta.rate!
      const resultRate = item.meta.rate!
      const stretch = item.meta.ratio || 1
      const sections = item.meta.edit_map?.map(part => ({
        start: part.result_start / resultRate, end: part.result_start / resultRate + (part.source_end - part.source_start) / inputRate, offset: part.source_start / inputRate,
      })) ?? (item.meta.source_end !== undefined && item.meta.source_start !== undefined && item.meta.operation?.tool === 'effects'
        ? [{ start: 0, end: (item.meta.source_end - item.meta.source_start) / inputRate, offset: item.meta.source_start / inputRate }]
        : undefined)
      playing = [{ asset: source, gain: 1, ratio: 1 / stretch, sourceOffset: (item.meta.source_start ?? 0) / inputRate, regions: sections }]
    }
    if (matched && source && playing.length) {
      const loudness = (entry: Asset) => entry.meta.lufs ?? assets.find(analysis => analysis.role === 'analysis' && analysis.parents.includes(entry.id) && typeof analysis.meta.report?.lufs === 'number')?.meta.report?.lufs as number | undefined
      const a = loudness(source), b = loudness(item)
      if (a != null && b != null) {
        const gain = 10 ** (Math.max(-20, Math.min(0, Math.min(a, b) - (which === 'base' ? a : b))) / 20)
        playing = playing.map(value => ({ ...value, gain: value.gain * gain }))
      }
    }
    if (target < to && playing.length) void player.play(playing as Source[], target, to, loopEnabled ? [from, to] : undefined)
  }
  function listenFx(next: FxSide, at = 0, repeat = loop, match = fxMatched) {
    if (!fxSource || !fxWindow || (next === 'wet' && !fxWet)) return
    const [from, to] = fxWindow
    const end = fxWet?.meta.seconds ?? to - from
    const levels = fxWet?.meta.comparison_lufs
    const gain = match && levels ? 10 ** (Math.max(-20, Math.min(...levels) - levels[next === 'dry' ? 0 : 1]) / 20) : 1
    const entry: Source = next === 'wet' && fxWet ? { asset: fxWet, gain } : { asset: fxSource, gain, regions: [{ start: 0, end: to - from, offset: from }] }
    const start = at < end - .001 ? at : 0
    monitorTracks.current = []
    setFxPlayback({ id: fxId, side: next })
    void player.play([entry], start, end, repeat ? [0, end] : undefined)
  }
  function startLive(at = player.cursor.current, listenSide = liveSide) {
    if (!readyForLive || !fxSource || !fxWindow || !fxParams || !region) return
    const [selectionStart, selectionEnd] = selectionSeconds(fxSource, region)
    const inSelection = at >= selectionStart && at < selectionEnd - .001
    const position = inSelection ? at : selectionStart
    const start = position >= fxWindow[0] && position < fxWindow[1] - .001 ? fxParams.start : Math.round(position * fxSource.meta.rate)
    const [from, to] = selectionSeconds(fxSource, { start, end: Math.min(region.end, start + fxSource.meta.rate * 30) })
    setAudition({ id: liveId, start })
    setError('')
    setFxPlayback(null)
    monitorTracks.current = []
    liveClip.current = liveId
    setLiveSide(listenSide)
    void player.playLive(fxSource, from, to, Math.max(from, position), fxParams.chain, loop, listenSide)
  }
  function liveAB(next: FxSide) {
    setLiveSide(next)
    player.selectLive(next)
  }
  function expandRack() {
    setRackExpanded(!rackExpanded)
    if (!rackExpanded) {
      setPane('')
      requestAnimationFrame(() => {
        rackPanel.current?.focus({ preventScroll: true })
        rackPanel.current?.scrollIntoView({ block: 'nearest' })
      })
    }
  }
  function changeRackStep(step: EffectStep) {
    if (fxParams) config('chain', fxParams.chain.map((entry, index) => index === rackAt ? step : entry))
  }
  const saveFxSelection = !running && !fxBusy && !edit.archived && fxSource && fxParams?.chain.length && caps?.tools.effects === 'ready'
    ? () => void submit('effects', [fxSource.id], fxParams) : undefined
  function togglePlayback() {
    if (player.playing) player.pause()
    else if (fxSide) listenFx(fxSide, player.cursor.current)
    else if (readyForLive) startLive()
    else listen()
  }
  function seek(target: number) {
    setFxPlayback(null); player.seek(target)
    if (player.liveActive) startLive(target)
    else if (player.playing) listen(undefined, target)
  }
  useEffect(() => { if (monitorTracks.current.length) player.setLevels(sourcesFor(monitorTracks.current, tracks, edit.rate)) }, [tracks, edit.rate])
  function alternate(which: 'base' | 'new') { setSide(which); if (player.playing) listen(undefined, player.cursor.current, which) }

  useEffect(() => {
    function key(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null
      if (target?.closest('input, textarea, select, button, [contenteditable], a, dialog')) return
      if (event.code === 'Space' && !event.repeat) { event.preventDefault(); togglePlayback() }
      if (event.key === 'Escape') { setProjectMenu(false); setPane(''); setExportMenu(false) }
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'z') { event.preventDefault(); undo(event.shiftKey) }
    }
    window.addEventListener('keydown', key)
    return () => window.removeEventListener('keydown', key)
  })
  const pairReady = !!source && audio(asset) && [source, asset].every(item => typeof item.meta.lufs === 'number' || assets.some(analysis => analysis.role === 'analysis' && analysis.parents.includes(item.id) && typeof analysis.meta.report?.lufs === 'number'))
  const navigation = () => {
    if (saving.current || saveState === 'Speichert …') { setError('Das Projekt speichert gerade.'); return }
    void query.invalidateQueries({ queryKey: ['projects'] }); back()
  }
  const template = templates.find(item => item.id === edit.draft.template)
  const recipe: NonNullable<Draft['recipe']> = edit.draft.recipe ?? (template?.recipe ?? []).map(tool => ({ tool, label: tools[tool][0], version: 1 }))
  const route = `/projects/${id}`
  function changeStep(index: number, details: Partial<NonNullable<Draft['recipe']>[number]>) {
    draft({ recipe: recipe.map((step, at) => at === index ? { ...step, ...details } : step) })
  }
  function moveStep(index: number, direction: number) {
    const entries = [...recipe]
    ;[entries[index], entries[index + direction]] = [entries[index + direction], entries[index]]
    draft({ recipe: entries })
  }
  async function runRecipe() {
    if (submitting.current || recipe.length < 2) return
    submitting.current = true
    setRunning(true)
    try {
      await persist(edit)
      const inputs = selected.length ? selected.map(item => item.id) : asset ? [asset.id] : []
      const steps = recipe.map(step => {
        const params = { ...singleSettings(step.tool) }
        if (step.tool === 'effects' && !params.chain) params.chain = [{ effect: 'Gain' }]
        if (step.tool === 'cut' && !params.cuts) params.cuts = slices
        if (step.tool === 'audiosr' && region && asset) { params.preview = true; params.start = region.start; params.end = Math.min(region.end, region.start + 15 * asset.meta.rate!) }
        const reference = step.tool === 'reference' ? assets.find(item => item.id === params.reference) ?? assets.find(item => item.role === 'reference' && item.id !== asset?.id) : undefined
        return { tool: step.tool, params, feed: step.feed || 'result', output: step.output || '', extra_inputs: reference ? [reference.id] : [] }
      })
      const signature = JSON.stringify([inputs, steps, edit])
      const pending = pendingRun.current?.signature === signature ? pendingRun.current
        : { signature, id: crypto.randomUUID(), revision: revision.current }
      pendingRun.current = pending
      await api(route + '/recipe-runs', 'POST', { id: pending.id, draft_revision: pending.revision, inputs, steps })
      pendingRun.current = null
      setQueue(true)
      await refresh()
    } catch (problem) { setError((problem as Error).message) }
    finally { submitting.current = false; setRunning(false) }
  }
  return <main className="workspace" style={{ '--library': `${libraryWidth}px`, '--inspector': `${inspectorWidth}px` } as React.CSSProperties}>
    <header className="project-bar">
      <div className="project-identity"><button className="brand-home" onClick={navigation} aria-label="Zur Projektübersicht"><BrandMark /></button>
        <div className="project-caption"><button className="project-name" aria-expanded={projectMenu} onClick={() => setProjectMenu(!projectMenu)} title={project.name}><span>{project.name}</span><ChevronDown size={15} aria-hidden="true" /></button><small className="save-label">{edit.archived ? 'Archiviert' : saveState}</small></div></div>
      <div className="project-metrics" aria-label="Projektparameter"><b title={edit.draft.tempo_origin === 'detected' ? 'Aus Audioanalyse übernommen' : edit.draft.tempo_origin === 'manual' ? 'Manuelles Projekttempo' : 'Projektvorgabe'}>{edit.bpm} <small>BPM</small></b><span>{edit.meter}</span><span>{edit.rate / 1000} kHz</span></div>
      <div className="project-actions"><button className="studio-manual" onClick={openHandbook} aria-label="Handbuch" title="Handbuch"><BookOpen size={16} aria-hidden="true" /><span>Handbuch</span></button><button disabled={!!pending || !!sharedPending || edit.archived} onClick={() => { role.current = 'original'; file.current?.click() }}><Import size={16} aria-hidden="true" /><span>Importieren</span></button><button className="primary" onClick={() => setExportMenu(true)}><ArrowDownToLine size={16} aria-hidden="true" /> Exportkorb <span className="counter">{cart.length}</span></button></div>
      <input hidden type="file" accept="audio/*,.flac,.aiff,.wav" multiple ref={file} onChange={event => { const files = Array.from(event.target.files ?? []); event.target.value = ''; void importFiles(files) }} />
    </header>
    {projectMenu && <section className="project-menu" aria-label="Projekteinstellungen">
      <div className="inline section-heading"><h2>Projekt</h2><button onClick={navigation}>Projekt wechseln</button></div>
      <label className="field"><span>Name</span><input maxLength={140} value={edit.name} onChange={event => update({ ...edit, name: event.target.value })} /></label>
      <div className="field-grid"><Num label="Tempo · BPM" value={edit.bpm} min={30} max={300} step={.01} onChange={bpm => update({ ...edit, bpm, draft: { ...edit.draft, tempo_origin: 'manual' } })} />
        <label className="field"><span>Taktart</span><select value={edit.meter} onChange={event => update({ ...edit, meter: event.target.value })}>{['2/4','3/4','4/4','5/4','6/8','7/8','9/8','12/8'].map(value => <option key={value}>{value}</option>)}</select></label>
        <label className="field"><span>Projekt-Sample-Rate</span><select value={edit.rate} onChange={event => update({ ...edit, rate: Number(event.target.value) })}><option value="48000">48 kHz</option><option value="44100">44,1 kHz</option></select></label>
        <label className="field"><span>Nutzung</span><select value={edit.purpose} onChange={event => update({ ...edit, purpose: event.target.value as Project['purpose'] })}><option value="private">Privates Experiment</option><option value="release">Veröffentlichung</option></select></label>
      </div>
      {storage.data && <details><summary>Lokaler Speicher · {(storage.data.used_bytes / 1024 ** 2).toFixed(1)} MiB</summary>
        <p className="hint">Hörkopien {(storage.data.preview_bytes / 1024 ** 2).toFixed(1)} MiB · Projektbudget {(storage.data.budget_bytes / 1024 ** 3).toFixed(0)} GiB</p>
        <button disabled={!storage.data.preview_bytes} onClick={async () => { try { await api('/storage/clear-previews','POST'); await storage.refetch() } catch (problem) { setError((problem as Error).message) } }}>Hörkopien bereinigen</button>
      </details>}
      <div className="inline"><button onClick={async () => { try { const copy = await api<Project>(route + '/duplicate', 'POST'); open(copy.id) } catch (problem) { setError((problem as Error).message) } }}>Duplizieren</button>
        <button onClick={() => update({ ...edit, archived: !edit.archived })}>{edit.archived ? 'Aktivieren' : 'Archivieren'}</button><button onClick={() => setProjectMenu(false)}>Schließen</button></div>
    </section>}
    <div className="compact-actions"><button aria-pressed={pane === 'library'} onClick={() => setPane(pane === 'library' ? '' : 'library')}><Layers3 size={16} aria-hidden="true" /> Bibliothek</button><button aria-pressed={pane === 'inspector'} onClick={() => setPane(pane === 'inspector' ? '' : 'inspector')}><SlidersHorizontal size={16} aria-hidden="true" /> Werkzeuge</button></div>
    <div className={`work-columns ${hideLibrary ? 'library-hidden' : ''} ${hideInspector ? 'inspector-hidden' : ''}`}>
      <aside className={`library panel ${pane === 'library' ? 'panel-shown' : ''}`}>
        <div className="panel-heading"><h2>Bibliothek</h2><button className="plain desktop-only" aria-label="Bibliothek einklappen" onClick={() => setHideLibrary(true)}>‹</button><button className="plain compact-only" aria-label="Bibliothek schließen" onClick={() => setPane('')}>×</button></div>
        <div className="library-filters"><input type="search" value={search} onChange={event => setSearch(event.target.value)} placeholder="Dateien suchen" aria-label="Dateien suchen" />
          <select aria-label="Asset-Typ filtern" value={filter} onChange={event => setFilter(event.target.value as Role | 'all')}><option value="all">Alle Materialien</option>{Object.entries(roleLabels).filter(([key]) => key !== 'export').map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></div>
        <div className="asset-list">
          {filtered.length ? filtered.map(item => <div className={`asset-row ${asset?.id === item.id ? 'active' : ''}`} data-role={item.role} key={item.id}>
            <input type="checkbox" aria-label={`${item.name} zur Mehrfachauswahl`} checked={selection.includes(item.id)} onChange={() => setSelection(toggle(selection, item.id))} />
            <button className="asset-name" title={item.name} aria-current={asset?.id === item.id ? 'true' : undefined} onClick={() => { pick(item); if (window.innerWidth < 900) setPane('') }}><span className="asset-icon" aria-hidden="true">{item.role === 'midi' ? <Disc3 size={16} /> : <AudioWaveform size={16} />}</span><span><strong>{resultName(item)}</strong><small>{roleLabels[item.role]}{item.meta.seconds ? ` · ${seconds(item.meta.seconds).slice(0, 5)}` : ''}</small></span></button>
          </div>) : <p className="hint">{assets.length ? 'Keine passenden Dateien.' : 'Importierte Dateien und Render erscheinen hier.'}</p>}
        </div>
        <div className="library-foot"><button disabled={!!pending || edit.archived} onClick={() => { role.current = 'reference'; file.current?.click() }}>+ Referenz importieren</button>
          <label className="field width-control"><span>Breite der Bibliothek</span><input type="range" min={240} max={280} value={libraryWidth} onChange={event => setLibraryWidth(Number(event.target.value))} /></label>
          {!!current.assets.filter(item => item.hidden).length && <details><summary>Ausgeblendete Materialien</summary>{current.assets.filter(item => item.hidden).map(item => <button key={item.id} onClick={() => void mutateAsset(item, { hidden: false })}>{item.name} wieder einblenden</button>)}</details>}
        </div>
      </aside>
      {hideLibrary && <button className="reopen desktop-only" onClick={() => setHideLibrary(false)}>Bibliothek</button>}
      <section className="timeline panel" onDragOver={event => { event.preventDefault() }} onDrop={event => { event.preventDefault(); role.current = 'original'; void importFiles(Array.from(event.dataTransfer.files)) }}>
        <div className="panel-heading"><h2>Arbeitsfläche</h2><div className="inline"><button className="plain" aria-label="Bearbeitung rückgängig" disabled={!undoStack.current.length} onClick={() => undo()}>↶</button><button className="plain" aria-label="Bearbeitung wiederholen" disabled={!redoStack.current.length} onClick={() => undo(true)}>↷</button></div></div>
        <details className="recipe" aria-label="Bearbeitungsfolge">
          <summary>{recipe.length ? `Bearbeitungsfolge · ${recipe.length} Schritte` : 'Bearbeitungsfolge'}</summary>
          <div className="recipe-steps">{recipe.map((step, index) => <button key={index} className={step.tool === tool ? 'current' : ''} onClick={() => choose(step.tool)}>{step.label}</button>)}</div>
          {recipe.map((step, index) => <div className="recipe-edit" key={index}>
            <div className="inline"><strong>{step.label}</strong>
              <button className="plain" aria-label={`${step.label} nach oben`} disabled={!index} onClick={() => moveStep(index, -1)}>↑</button>
              <button className="plain" aria-label={`${step.label} nach unten`} disabled={index === recipe.length - 1} onClick={() => moveStep(index, 1)}>↓</button>
              <button className="plain" aria-label={`${step.label} aus Folge entfernen`} onClick={() => draft({ recipe: recipe.filter((_, i) => i !== index) })}>×</button>
            </div>
            {index > 0 && step.tool !== 'generation' && <div className="field-grid">
              <label className="field"><span>Eingang</span><select value={step.feed || 'result'} onChange={event => changeStep(index, { feed: event.target.value as typeof step.feed })}><option value="result">Ergebnis des vorherigen Schritts</option><option value="input">Eingang des vorherigen Schritts</option><option value="initial">Erste Auswahl</option></select></label>
              {(step.feed || 'result') === 'result' && <label className="field"><span>Ausgabename bei mehreren Ergebnissen</span><input value={step.output || ''} maxLength={140} placeholder="z. B. drums.wav" onChange={event => changeStep(index, { output: event.target.value })} /></label>}
            </div>}
          </div>)}
          <div className="inline"><button disabled={recipe.length >= 8} onClick={() => draft({ recipe: [...recipe, { tool, label: tools[tool][0], version: 1 }] })}>Aktuelles Werkzeug hinzufügen</button>
            <button className="primary" disabled={running || edit.archived || recipe.length < 2} onClick={() => void runRecipe()}>Folge rendern</button></div>
          {recipe.some(step => ['separation','mastering','enhancement','transcription','generation','audiosr'].includes(step.tool)) && <p className="hint">Diese Folge enthält private Modal-Aufträge.</p>}
        </details>
        {!asset ? <div className="empty-stage"><div aria-hidden="true" className="empty-pulse"><AudioWaveform size={33} /></div><h3>Material ins Projekt holen</h3><p>Ziehe Audiodateien hierher oder importiere sie direkt.</p><button className="primary" disabled={edit.archived || !!pending} onClick={() => { role.current = 'original'; file.current?.click() }}>Dateien importieren</button>{defaultTool === 'generation' && <button onClick={() => choose('generation')}>Text zu Audio öffnen</button>}</div>
          : <><div className="asset-top"><div className="asset-title" data-role={asset.role}><div className="inline asset-tags"><span className="mode clip-tag">{roleLabels[asset.role]}</span>
            {audio(asset) && (displayKey || keyReport ? <button className="key-status" onClick={() => choose('stretch')} title={sourceKey ? 'Quelltonart manuell gesetzt' : estimatedKey ? 'Abgeleitete Quelltonart' : 'Tonart manuell wählen'}>
              {displayKey ? keyName(displayKey) : 'Tonart unklar'} <SlidersHorizontal size={13} aria-hidden="true" />
            </button> : <button className="key-status" disabled={running || keyBusy || !!edit.archived || caps?.tools.detect !== 'ready'} onClick={() => void submit('detect', [asset.id], { mode: 'key' })}>{keyBusy ? 'Tonart wird analysiert …' : 'Tonart erkennen'}</button>)}
          </div><h3 title={asset.name}>{resultName(asset)}</h3><small>{asset.meta.rate ? `${asset.meta.channels === 1 ? 'Mono' : 'Stereo'} · ${asset.meta.rate / 1000} kHz · ${seconds(asset.meta.seconds!)}` : asset.meta.engine || asset.suffix}</small></div>
            <div className="inline"><button aria-pressed={cart.includes(asset.id)} onClick={() => setCart(toggle(cart, asset.id))}>{cart.includes(asset.id) ? 'Im Exportkorb' : '+ Exportkorb'}</button>
              <details className="asset-menu"><summary>Asset-Aktionen</summary><form onSubmit={event => { event.preventDefault(); const value = new FormData(event.currentTarget).get('name'); void mutateAsset(asset, { name: value }) }}>
                <label className="field"><span>Asset-Name</span><input key={asset.id} name="name" defaultValue={asset.name} maxLength={140} required /></label><button>Umbenennen</button></form>
                <a className="button" href={assetUrl(asset, 'download')}>Datei herunterladen</a>
                {asset.role === 'take' && <button onClick={() => void mutateAsset(asset, { role: 'variant' })}>Als Material übernehmen</button>}
                {asset.role === 'original' && <button onClick={() => void mutateAsset(asset, { role: 'reference' })}>Als Referenz markieren</button>}
                <button onClick={() => void mutateAsset(asset, { hidden: true })}>Aus Bibliothek ausblenden</button>
                {asset.parents.length > 0 && <p className="hint">{current.assets.filter(item => item.parents.includes(asset.id)).length} direkte Weiterverwendungen · Quelle {source?.name || 'in Herkunft sichtbar'}</p>}
              </details></div>
          </div>
          {audio(asset) && region && <><div className="signal-frame"><div className="timeline-controls inline">
              <span className="signal-title"><AudioLines size={16} aria-hidden="true" />{viewedTracks.length} {viewedTracks.length === 1 ? 'Spur' : 'Spuren'}</span><div className="inline timeline-options"><label>Lineal <select value={bars ? 'bars' : 'time'} onChange={event => setBars(event.target.value === 'bars')}><option value="time">Zeit</option><option value="bars">Takte</option></select></label><label>Zoom <select value={zoom} onChange={event => setZoom(Number(event.target.value))}><option value="1">100 %</option><option value="2">200 %</option><option value="4">400 %</option><option value="8">800 %</option></select></label></div>
              {selected.length > 0 && <button onClick={() => { setCart([...new Set([...cart, ...selected.map(item => item.id)])]); setSelection([]) }}>Auswahl in Exportkorb</button>}
            </div><div className="wave-scroll"><div className="wave-grid" style={{ width: `${zoom * 100}%` }}>
              <TimelineRuler duration={duration} zoom={zoom} bars={bars} barLength={beat * meterN} downbeat={mark} />
              {viewedTracks.map(item => <div className={`lane ${item.id === asset.id ? 'lane-active' : ''}`} data-role={item.role} key={item.id}><div className="lane-label"><button className="plain" title={item.name} onClick={() => pick(item)}>{item.name}</button><small>{roleLabels[item.role]}</small><div>
                {(['solo', 'mute'] as const).map(key => <button className="plain" key={key} aria-label={`${item.name} ${key}`} aria-pressed={trackSettings(item)[key]} onClick={() => draft({ tracks: { ...tracks, [item.id]: { ...trackSettings(item), [key]: !trackSettings(item)[key] } } })}>{key === 'solo' ? 'S' : 'M'}</button>)}</div></div>
                <Wave asset={item} length={duration} position={waveClock} offset={trackSettings(item).offset / edit.rate}
                  region={item.id === asset.id ? region : undefined} markers={item.id === asset.id ? slices : undefined}
                  beats={beatLines} beatsPerBar={meterN} onRegion={item.id === asset.id ? setRegion : undefined} onSeek={seek} /></div>)}
            </div></div></div>
            {fxSource && fxParams && fxWindow && <>
              {caps?.live_effects && <section ref={rackPanel} tabIndex={-1} className="fx-compare rack-preview-panel" aria-label="Live-Effektvorschau">
                <header className="fx-compare-header"><div className="fx-compare-title"><AudioWaveform size={19} aria-hidden="true" /><div>
                  <h3>{rackExpanded && rackStep ? effectTitle(rackStep.effect) : 'Live-Effektvorschau'}</h3>
                  <p>{seconds(fxWindow[0])}–{seconds(fxWindow[1])}</p>
                </div></div>
                  <div className="inline"><button className="primary" disabled={!readyForLive} onClick={() => player.liveActive ? player.pause() : startLive()}>{player.liveActive ? 'Live pausieren' : 'Live hören'}</button>
                    <button type="button" aria-expanded={rackExpanded} onClick={expandRack}>{rackExpanded ? 'Display verkleinern' : 'Display vergrößern'}</button>
                  </div></header>
                {rackExpanded && <><FxScope large running={player.liveActive && !player.loading} read={player.readLive} />
                  {rackStep && <div className="rack-large-dials fx-module" data-effect={rackStep.effect}><EffectDials key={rackAt + rackStep.effect} step={rackStep} change={changeRackStep} /></div>}</>}
                <div className="rack-live-footer"><div className="ab" role="group" aria-label="Live-Hörvergleich">
                  <button disabled={!readyForLive} aria-pressed={liveSide === 'dry'} onClick={() => liveAB('dry')}>A · Quelle</button>
                  <button disabled={!readyForLive} aria-pressed={liveSide === 'wet'} onClick={() => liveAB('wet')}>B · Effekt</button>
                </div><small role="status">{liveStatus}</small></div>
              </section>}
              <details className="fx-saved" open={!caps?.live_effects || undefined}><summary>Gerenderte Vorschau und WAV speichern</summary>
              <FxCompare source={fxSource} wet={fxWet} window={fxWindow} clock={player.position} side={fxSide} playing={player.playing}
              state={fxBusy ? 'Rendert …' : fxCurrent?.state === 'failed' ? 'Render fehlgeschlagen' : fxJobs.length && !fxCurrent ? 'Auswahl oder Effekt geändert' : 'Vorschau fehlt'}
              render={saveFxSelection}
              listen={next => { if (next === fxSide && player.playing) player.pause(); else listenFx(next, fxSide ? player.cursor.current : 0) }}
              matched={fxMatched} setMatched={value => { setFxMatched(value); if (fxSide && player.playing) listenFx(fxSide, player.cursor.current, loop, value) }}
              inCart={!!fxWet && cart.includes(fxWet.id)} exportWet={() => fxWet && setCart(toggle(cart, fxWet.id))} /></details></>}
            <RegionEditor key={asset.id} project={project} asset={asset} region={region} set={setRegion} slices={slices}
              setSlices={value => config('slices', value, regionGroup)} addLabel={tool === 'cut' ? 'Schnitt' : 'Treffer'} detected={detected}
              onPlay={value => listen(value, selectionSeconds(asset, value)[0])} />
            <details className="grid-panel"><summary>Beat-Grid und erster Downbeat</summary><div className="field-grid">
              <Num label="BPM" value={bpm} min={30} max={300} step={.01} onChange={bpm => update({ ...edit, bpm, draft: { ...edit.draft, tempo_origin: 'manual' } })} />
              <Num label="Erster Downbeat · s" value={mark} min={0} max={duration} step={.001} onChange={downbeat => draft({ downbeat, tempo_origin: 'manual' })} />
            </div><div className="inline"><button disabled={bpm < 60} onClick={() => update({ ...edit, bpm: bpm / 2, draft: { ...edit.draft, tempo_origin: 'manual' } })}>Halbieren</button><button disabled={bpm > 150} onClick={() => update({ ...edit, bpm: bpm * 2, draft: { ...edit.draft, tempo_origin: 'manual' } })}>Verdoppeln</button>{analysis && <button onClick={() => update({ ...edit, bpm: Number(analysis.meta.report!.bpm), draft: { ...edit.draft, tempo_origin: 'detected' } })}>Erkanntes Tempo übernehmen</button>}</div><p className="hint">{meterN} Zählzeiten pro Takt · {edit.draft.tempo_origin === 'detected' ? 'Erkannt' : edit.draft.tempo_origin === 'manual' ? 'Manuell' : 'Projektvorgabe'}</p></details></>}
          {asset.role === 'midi' && ((midiView ?? asset.meta.midi)?.tracks?.length
            ? <Piano key={asset.id} asset={asset} view={midiView} change={view => config('view', view, `midi:${asset.id}`)} edit={() => choose('midi')} />
            : <TempoMap key={asset.id} asset={asset} />)}
          {asset.role === 'analysis' && <AnalysisResult key={asset.id} asset={asset} />}
          {audio(asset) && typeof asset.meta.lufs === 'number' && <section className="measure" aria-label="Messwerte">
            <h3>Messwerte</h3><ResultMetrics values={[
              ['Lautheit · LUFS', asset.meta.lufs], ['True Peak · dBTP', asset.meta.true_peak], ['Dynamik · LRA', asset.meta.lra],
              ['Pegel · dBFS', asset.meta.sample_peak], ['Tempo · BPM', asset.meta.bpm],
            ]} /></section>}
          {parentJob && <details className="grid-panel"><summary>Herkunft und Parameter{stalePreview ? ' · Vorschau mit älteren Parametern' : asset.meta.preview_render ? ' · Auswahlvorschau' : ''}</summary><p className="hint">{asset.meta.engine} · {source?.name || 'Projektquelle'}{asset.meta.seed !== undefined ? ` · Seed ${asset.meta.seed}` : ''}</p><pre>{JSON.stringify(parentJob.params, null, 2)}</pre></details>}
        </>}
      </section>
      {hideInspector && <button className="reopen desktop-only" onClick={() => setHideInspector(false)}>Werkzeuge</button>}
      <aside className={`inspector panel ${pane === 'inspector' ? 'panel-shown' : ''}`}>
        <div className="panel-heading"><h2>Inspektor</h2><button className="plain desktop-only" aria-label="Inspektor einklappen" onClick={() => setHideInspector(true)}>›</button><button className="plain compact-only" aria-label="Inspektor schließen" onClick={() => setPane('')}>×</button></div>
        <Inspector tool={tool} setTool={choose} settings={tool === 'midi' && asset ? { ...settings, view: midiView ?? asset.meta.midi } : settings}
          change={config} asset={asset} assets={assets} selected={selected} project={project} caps={caps}
          openSource={source ? () => { pick(source); setPane('') } : undefined}
          rack={{ selected: rackIndex, select: setRackIndex, running: player.liveActive && !player.loading, read: player.readLive,
            expanded: rackExpanded, expand: expandRack, status: liveStatus, playing: player.liveActive, render: saveFxSelection,
            playback: readyForLive ? () => player.liveActive ? player.pause() : startLive() : undefined }}
          sourceKey={sourceKey} estimatedKey={estimatedKey} setSourceKey={value => config('source', value ?? null, keyGroup)}
          region={region} setRegion={setRegion} slices={slices} setSlices={value => asset && config('slices', value, regionGroup)}
          setGrid={(bpm, downbeat) => update({ ...edit, bpm, draft: { ...edit.draft, downbeat } })}
          tracks={tracks} setTrack={(item, track) => draft({ tracks: { ...tracks, [item]: track } })} run={submit} busy={running} />
        <label className="field width-control"><span>Breite des Inspektors</span><input type="range" min={320} max={360} value={inspectorWidth} onChange={event => setInspectorWidth(Number(event.target.value))} /></label>
      </aside>
    </div>
    <footer className="bottom">
      <div className="transport" aria-label="Zentraler Transport">
        <div className="inline transport-buttons"><button className="play" data-playing={player.playing && !player.loading} aria-label={player.playing ? 'Pause' : 'Abspielen'} disabled={!player.playing && !canPlay} onClick={togglePlayback}>{player.playing ? <Pause size={17} fill="currentColor" /> : <Play size={17} fill="currentColor" />}</button>
          <button aria-label="Stopp" onClick={() => { player.pause(); player.seek(0) }}><Square size={14} fill="currentColor" aria-hidden="true" /></button><TransportTime clock={player.position} /></div>
        <OutputMeter playing={player.playing && !player.loading} read={player.readOutput} />
        <div className="inline transport-options"><button disabled={!audio(asset)} aria-pressed={loop} onClick={() => { setLoop(!loop); if (player.playing && !player.liveActive) { if (fxSide) listenFx(fxSide, player.cursor.current, !loop); else listen(undefined, player.cursor.current, side, !loop) } }}><Repeat2 size={16} aria-hidden="true" /> Loop</button>
          {player.liveActive ? <div className="ab"><button aria-pressed={liveSide === 'dry'} onClick={() => liveAB('dry')}>A · Quelle</button><button aria-pressed={liveSide === 'wet'} onClick={() => liveAB('wet')}>B · Effekt</button></div>
            : <div className="ab"><button aria-pressed={side === 'base'} disabled={!source || !audio(asset)} onClick={() => alternate('base')}>A · Quelle</button><button aria-pressed={side === 'new'} disabled={!source || !audio(asset)} onClick={() => alternate('new')}>B · Variante</button></div>}
          <button aria-pressed={!player.liveActive && matched} disabled={!pairReady || player.liveActive} title={pairReady ? undefined : 'Beide Versionen zuerst auf LUFS prüfen'} onClick={() => setMatched(!matched)}>Pegelabgleich</button>
          <div className="monitor"><Dial label="Abhörpegel" min={0} max={100} value={Math.round(player.volume * 100)}
            suffix="%" live onChange={value => player.setVolume(value / 100)} /></div>
        </div>
        {player.loading && <span className="hint" role="status">Audio wird gepuffert …</span>}
      </div>
      <section className="jobs"><button aria-expanded={queue} className="jobs-toggle" onClick={() => setQueue(!queue)}><span className={isNew ? 'job-light busy' : 'job-light'} /><strong>Aufgaben</strong> <span>{current.jobs.filter(job => !terminal.has(job.state)).length} aktiv · {current.jobs.filter(job => job.state === 'completed').length} fertig</span><span className="jobs-chevron" aria-hidden="true">{queue ? '⌄' : '⌃'}</span></button>
        {queue && <div className="job-list" aria-label="Aufgabenstatus">
          {!current.jobs.length && <p className="hint">Gestartete Render und Exporte erscheinen hier.</p>}
          {current.jobs.map(job => {
            const failed = job.state === 'partial' && job.error?.startsWith('Fehlende Ergebnisse: ') ? job.error.slice(20).trim().split(', ') : []
            const missing = job.tool === 'separation' ? failed.filter(item => item.endsWith('.wav')).map(item => item.slice(0,-4))
              : job.tool === 'transcription' ? failed.filter(item => ['melody','drums','beat','chords'].includes(item)) : []
            return <article className="job" key={job.id}>
            <div><strong>{job.tool === 'detect' && job.params.mode === 'key' ? 'Tonart erkennen' : tools[job.tool]?.[0] ?? 'Export'}</strong><small>{job.cancel_requested && !terminal.has(job.state) ? 'Abbruch angefordert' : stateLabels[job.state] || job.state} · {job.phase}{typeof job.params.seed === 'number' ? ` · Seed ${job.params.seed}` : ''}</small>{job.error && <p className="hint">{job.error}</p>}</div>
            <div className="job-actions">{job.progress !== null && !terminal.has(job.state) && <progress max={100} value={job.progress} aria-label="Fortschritt" />}
              {!terminal.has(job.state) && <button disabled={!!job.cancel_requested} onClick={async () => {
                try { await api(`${route}/jobs/${job.id}/cancel`, 'POST'); setAbortMessage('Abbruch angefordert.'); await refresh() }
                catch (problem) { setError((problem as Error).message) }
              }}>Abbrechen</button>}
              {(job.state === 'submission_unknown' || (job.remote_id && ['failed', 'output_unconfirmed'].includes(job.state))) && <button onClick={async () => {
                try { await api(`${route}/jobs/${job.id}/reconcile`, 'POST'); await refresh() }
                catch (problem) { setError((problem as Error).message) }
              }}>Cloud-Status prüfen</button>}
              {!!missing.length && <button disabled={running} onClick={() => void submit(job.tool, job.inputs, {
                ...job.params, [job.tool === 'separation' ? 'stems' : 'tasks']: missing,
                ...(missing.includes('instrumental') ? { coherent: false } : {}),
              })}>Fehlende Teile rendern</button>}
              {all.filter(item => item.job === job.id).map(item => item.role === 'export' ? <a className="button" key={item.id} href={assetUrl(item, 'download')}>Paket laden{item.meta.qa_warnings ? ` · ${item.meta.qa_warnings} QA-Hinweise` : ''}</a> : <button key={item.id} onClick={() => pick(item)}>{item.name}</button>)}
            </div>
          </article>})}
        </div>}
      </section>
    </footer>
    <dialog ref={dialog} className="export-dialog" onCancel={() => setExportMenu(false)} aria-labelledby="cart-title">
      <div className="inline section-heading"><h2 id="cart-title">Exportkorb</h2><button aria-label="Exportkorb schließen" onClick={() => setExportMenu(false)}>×</button></div>
      <div className="export-assets">{assets.map(item => <Check key={item.id} checked={cart.includes(item.id)} onChange={() => setCart(toggle(cart, item.id))}>{item.name} · {roleLabels[item.role]}{item.meta.bpm ? ` · ${item.meta.bpm} BPM` : ''}</Check>)}</div>
      <div className="field-grid"><label className="field"><span>Audioformat</span><select value={format} onChange={event => setFormat(event.target.value)}><option value="pcm24">WAV · PCM 24 Bit</option><option value="pcm16">WAV · PCM 16 Bit</option><option value="float32">WAV · Float 32</option><option value="mp3">MP3 · Hörkopie</option></select></label>
      <div><Check checked={align} onChange={setAlign}>Spuren ausrichten</Check><Check checked={strict} onChange={setStrict}>Bei QA-Abweichung stoppen</Check></div></div>
      <div className="inline"><button disabled={running || !assets.length || edit.archived} onClick={() => void submit('export', assets.map(item => item.id), { package: true, format: 'float32', align: false })}>Projektpaket sichern</button>
        <button className="primary" disabled={running || !cart.length || edit.archived} onClick={() => void submit('export', cart.filter(key => assets.some(item => item.id === key)), { format, align, strict })}>DAW-Paket erstellen</button></div>
    </dialog>
    {(error || pending || abortMessage) && <div className={`toast ${error ? 'error' : ''}`} role={error ? 'alert' : 'status'}>{error || pending || abortMessage}{(error || abortMessage) && <button aria-label="Meldung schließen" onClick={() => { setError(''); setAbortMessage('') }}>×</button>}</div>}
  </main>
}

createRoot(document.getElementById('root')!).render(<QueryClientProvider client={client}><App /></QueryClientProvider>)
