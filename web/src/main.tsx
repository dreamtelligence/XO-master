import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useMemo, useRef, useState } from 'react'
import { api, assetUrl, audio, terminal, upload, type Asset, type Capabilities, type Draft, type Midi, type Project, type Region, type Role, type Workspace } from './api'
import { Piano, RegionEditor, TransportTime, Wave } from './editor'
import { Check, Inspector, Num, templates, tools } from './tools'
import { seconds, selectionSeconds, sourcesFor, useTransport, type Source } from './transport'
import './studio.css'

const client = new QueryClient({ defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } } })
const roleLabels: Record<Role, string> = { original: 'Original', reference: 'Referenz', stem: 'Stem', variant: 'Variante', loop: 'Loop', oneshot: 'One-Shot', midi: 'MIDI', take: 'Take', analysis: 'Analyse', export: 'Paket' }
const stateLabels: Record<string, string> = { queued: 'Wartet', blocked: 'Wartet auf Eingang', running: 'Läuft', finalizing: 'Prüft', completed: 'Fertig', failed: 'Fehler', partial: 'Teilweise fertig', cancelled: 'Abgebrochen', offline: 'Verbindung unterbrochen', submission_unknown: 'Start unbestätigt', output_unconfirmed: 'Ausgabe unbestätigt' }
const contextKey = 'xo-workspace-project'
const copyright = 'Dreamtelligence'

function Brand() { return <div className="brand"><span className="brand-mark" aria-hidden="true">∿</span><span>{copyright}<small>Artist Workspace</small></span></div> }

function App() {
  const [project, setProject] = useState(() => localStorage.getItem(contextKey) || '')
  const [error, setError] = useState('')
  const [pending, setPending] = useState('')
  const openFile = useRef<HTMLInputElement>(null)
  const inputPackage = useRef<HTMLInputElement>(null)
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
    {project ? <ProjectView key={project} id={project} back={() => open('')} open={open} caps={caps.data} sharedPending={pending} />
      : <main className="welcome" onDragOver={event => { event.preventDefault() }} onDrop={event => { event.preventDefault(); const files = Array.from(event.dataTransfer.files); if (files.length) void create(undefined, files) }}>
      <header className="welcome-header"><Brand /><span className="session-mark"><span /> Privater Arbeitsbereich</span></header>
      <section className="welcome-main"><div className="welcome-hero">
        <div className="welcome-copy"><h1>Dein Audio.<br />Dein Arbeitsbereich.</h1><p>Importiere Material, höre Varianten im Vergleich und bereite Spuren, Samples und MIDI für deine DAW vor.</p>
          <div className="inline"><button className="primary import-main" disabled={!!pending} onClick={() => openFile.current?.click()}><span aria-hidden="true">↥</span> Dateien importieren</button><button disabled={!!pending} onClick={() => void create()}>Leeres Projekt</button></div>
          <input hidden ref={openFile} type="file" accept="audio/*,.flac,.aiff,.wav" multiple onChange={event => { const files = Array.from(event.target.files ?? []); if (files.length) void create(undefined, files); event.target.value = '' }} />
        </div><div className="hero-visual" aria-hidden="true">
          <div className="visual-grid" /><div className="visual-crossline" />
          <div className="hero-wave">{Array.from({ length: 85 }, (_, i) => <span key={i} style={{ height: `${Math.max(4, Math.abs(Math.sin(i * .69) * Math.cos(i * .105)) * 114 * Math.sin((i + 1) / 86 * Math.PI))}px` }} />)}</div>
          <div className="hero-wave secondary">{Array.from({ length: 85 }, (_, i) => <span key={i} style={{ height: `${Math.max(4, Math.abs(Math.sin(i * .31) * Math.cos(i * .058)) * 46)}px` }} />)}</div>
          <div className="hero-ticks"><span>00:00</span><span>00:04</span><span>00:08</span><span>00:12</span></div>
        </div>
      </div>
      <section className="start-templates"><h2>Mit Vorlage starten</h2><div className="template-grid">{templates.map(item =>
        <button key={item.id} className="template" disabled={!!pending} onClick={() => void create(item.id)}><span className={`template-icon ${item.id}`} aria-hidden="true">{item.icon}</span><span><strong>{item.title}</strong><small>{item.detail}</small></span><span className="arrow" aria-hidden="true">↗</span></button>)}</div></section>
      <section className="recent"><div className="inline section-heading"><h2>Lokale Projekte</h2><button disabled={!!pending} onClick={() => inputPackage.current?.click()}>Projektpaket öffnen</button></div>
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
  </>
}

function ProjectView({ id, back, open, caps, sharedPending }: { id: string; back: () => void; open: (id: string) => void; caps?: Capabilities; sharedPending: string }) {
  const query = useQueryClient()
  const data = useQuery({ queryKey: ['workspace', id], queryFn: () => api<Workspace>(`/projects/${id}`),
    refetchInterval: q => q.state.data?.jobs.some(job => !terminal.has(job.state)) ? 1000 : false })
  if (!data.data) return <main className="welcome"><Brand /><p className={data.error ? 'notice' : 'hint'}>{data.error?.message || 'Projekt wird geladen …'}</p><button onClick={back}>Zu den Projekten</button></main>
  return <WorkspaceView current={data.data} id={id} back={back} open={open} caps={caps} sharedPending={sharedPending} refresh={() => query.invalidateQueries({ queryKey: ['workspace', id] })} />
}

type Editable = Pick<Project, 'name' | 'rate' | 'meter' | 'purpose' | 'bpm'> & { draft: Draft; archived: boolean }

function WorkspaceView({ current, id, back, open, caps, sharedPending, refresh }: { current: Workspace; id: string; back: () => void; open: (id: string) => void; caps?: Capabilities; sharedPending: string; refresh: () => Promise<void> }) {
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
  const [pane, setPane] = useState<'library' | 'inspector' | ''>('library')
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
  const [zoom, setZoom] = useState(1)
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
  const asset = assets.find(item => item.id === active) ?? assets.find(audio) ?? assets[0]
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
  const regionGroup = asset ? `regions:${asset.id}:${tool === 'cut' ? 'cuts' : 'slices'}` : ''
  const slices = (asset && singleSettings(regionGroup).slices as Region[] | undefined) || []
  const analysis = audio(asset) ? assets.find(item => item.role === 'analysis' && item.parents.includes(asset.id) && typeof item.meta.report?.bpm === 'number') : undefined
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
  const filtered = assets.filter(item => (filter === 'all' || item.role === filter) && item.name.toLowerCase().includes(search.toLowerCase()))
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

  function pick(item: Asset) {
    if (asset?.id !== item.id) { player.pause(); player.seek(0); setSide('new') }
    setActive(item.id)
    if (item.role === 'midi') draft({ tool: 'midi' })
  }
  function choose(tool: string) {
    draft({ tool })
    setHideInspector(false)
    setPane('inspector')
  }
  function toggle(array: string[], value: string) { return array.includes(value) ? array.filter(item => item !== value) : [...array, value] }

  async function submit(tool: string, inputs: string[], params: Record<string, unknown>, count = 1) {
    if (submitting.current) return
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
    monitorTracks.current = []
    if (asset?.role === 'midi') { void player.playMidi({ ...asset, meta: { ...asset.meta, midi: (singleSettings(`midi:${asset.id}`).view as Midi | undefined) ?? asset.meta.midi } }, at ?? player.cursor.current); return }
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
      }))
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
  function seek(target: number) { player.seek(target); if (player.playing) listen(undefined, target) }
  useEffect(() => { if (monitorTracks.current.length) player.setLevels(sourcesFor(monitorTracks.current, tracks, edit.rate)) }, [tracks, edit.rate])
  function alternate(which: 'base' | 'new') { setSide(which); if (player.playing) listen(undefined, player.cursor.current, which) }

  useEffect(() => {
    function key(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null
      if (target?.closest('input, textarea, select, button, [contenteditable], a, dialog')) return
      if (event.code === 'Space' && !event.repeat) { event.preventDefault(); if (player.playing) player.pause(); else listen() }
      if (event.key === 'Escape') { setProjectMenu(false); setPane(''); setExportMenu(false) }
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'z') { event.preventDefault(); undo(event.shiftKey) }
    }
    window.addEventListener('keydown', key)
    return () => window.removeEventListener('keydown', key)
  })
  const measured = asset?.meta.report ?? asset?.meta ?? {}
  const pairReady = !!source && [source, asset].every(item => !!item && (typeof item.meta.lufs === 'number' || assets.some(analysis => analysis.role === 'analysis' && analysis.parents.includes(item.id) && typeof analysis.meta.report?.lufs === 'number')))
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
      <div className="project-identity"><button className="brand-home" onClick={navigation} aria-label="Zur Projektübersicht"><span className="brand-mark" aria-hidden="true">∿</span></button>
        <div><button className="project-name" aria-expanded={projectMenu} onClick={() => setProjectMenu(!projectMenu)}>{project.name} <span aria-hidden="true">⌄</span></button><small className="save-label">{edit.archived ? 'Archiviert' : saveState}</small></div></div>
      <div className="project-metrics"><b>{edit.bpm} <small>BPM</small></b><span>{edit.meter}</span><span>{edit.rate / 1000} kHz</span></div>
      <div className="project-actions"><button disabled={!!pending || !!sharedPending || edit.archived} onClick={() => { role.current = 'original'; file.current?.click() }}>↥ <span>Importieren</span></button><button className="primary" onClick={() => setExportMenu(true)}>Exportkorb <span className="counter">{cart.length}</span></button></div>
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
    <div className="compact-actions"><button aria-pressed={pane === 'library'} onClick={() => setPane(pane === 'library' ? '' : 'library')}>Bibliothek</button><button aria-pressed={pane === 'inspector'} onClick={() => setPane(pane === 'inspector' ? '' : 'inspector')}>Werkzeuge</button></div>
    <div className={`work-columns ${hideLibrary ? 'library-hidden' : ''} ${hideInspector ? 'inspector-hidden' : ''}`}>
      <aside className={`library panel ${pane === 'library' ? 'panel-shown' : ''}`}>
        <div className="panel-heading"><h2>Bibliothek</h2><button className="plain desktop-only" aria-label="Bibliothek einklappen" onClick={() => setHideLibrary(true)}>‹</button><button className="plain compact-only" aria-label="Bibliothek schließen" onClick={() => setPane('')}>×</button></div>
        <div className="library-filters"><input type="search" value={search} onChange={event => setSearch(event.target.value)} placeholder="Dateien suchen" aria-label="Dateien suchen" />
          <select aria-label="Asset-Typ filtern" value={filter} onChange={event => setFilter(event.target.value as Role | 'all')}><option value="all">Alle Materialien</option>{Object.entries(roleLabels).filter(([key]) => key !== 'export').map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></div>
        <div className="asset-list">
          {filtered.length ? filtered.map(item => <div className={`asset-row ${asset?.id === item.id ? 'active' : ''}`} key={item.id}>
            <input type="checkbox" aria-label={`${item.name} zur Mehrfachauswahl`} checked={selection.includes(item.id)} onChange={() => setSelection(toggle(selection, item.id))} />
            <button className="asset-name" aria-current={asset?.id === item.id ? 'true' : undefined} onClick={() => { pick(item); if (window.innerWidth < 900) setPane('') }}><span className={`asset-icon ${item.role}`} aria-hidden="true">{item.role === 'midi' ? '♬' : item.role === 'analysis' ? '≋' : '∿'}</span><span><strong>{item.name}</strong><small>{roleLabels[item.role]}{item.meta.seconds ? ` · ${seconds(item.meta.seconds).slice(0, 5)}` : ''}</small></span></button>
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
        {!asset ? <div className="empty-stage"><div aria-hidden="true" className="empty-pulse">∿</div><h3>Material ins Projekt holen</h3><p>Ziehe Audiodateien hierher oder importiere sie direkt.</p><button className="primary" disabled={edit.archived || !!pending} onClick={() => { role.current = 'original'; file.current?.click() }}>Dateien importieren</button>{defaultTool === 'generation' && <button onClick={() => choose('generation')}>Text zu Audio öffnen</button>}</div>
          : <><div className="asset-top"><div className="asset-title"><span className="mode">{roleLabels[asset.role]}</span><h3>{asset.name}</h3><small>{asset.meta.rate ? `${asset.meta.channels === 1 ? 'Mono' : 'Stereo'} · ${asset.meta.rate / 1000} kHz · ${seconds(asset.meta.seconds!)}` : asset.meta.engine || asset.suffix}</small></div>
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
          {audio(asset) && region && <><div className="timeline-controls inline">
              <span>{viewedTracks.length} {viewedTracks.length === 1 ? 'Spur' : 'Spuren'}</span><label>Zoom <select value={zoom} onChange={event => setZoom(Number(event.target.value))}><option value="1">100 %</option><option value="2">200 %</option><option value="4">400 %</option><option value="8">800 %</option></select></label>
              {selected.length > 0 && <button onClick={() => { setCart([...new Set([...cart, ...selected.map(item => item.id)])]); setSelection([]) }}>Auswahl in Exportkorb</button>}
            </div><div className="wave-scroll"><div className="wave-grid" style={{ width: `${zoom * 100}%` }}>
              <div className="timeline-label"><span />{Array.from({ length: 5 }, (_, index) => <span key={index}>{seconds(duration * index / 4).slice(0, duration < 10 ? 8 : 5)}</span>)}</div>
              {viewedTracks.map(item => <div className="lane" key={item.id}><div className="lane-label"><button className="plain" title={item.name} onClick={() => pick(item)}>{item.name}</button><div>
                {(['solo', 'mute'] as const).map(key => <button className="plain" key={key} aria-label={`${item.name} ${key}`} aria-pressed={trackSettings(item)[key]} onClick={() => draft({ tracks: { ...tracks, [item.id]: { ...trackSettings(item), [key]: !trackSettings(item)[key] } } })}>{key === 'solo' ? 'S' : 'M'}</button>)}</div></div>
                <Wave asset={item} length={duration} position={player.position} offset={trackSettings(item).offset / edit.rate}
                  region={item.id === asset.id ? region : undefined} markers={item.id === asset.id ? slices : undefined}
                  beats={beatLines} onRegion={item.id === asset.id ? setRegion : undefined} onSeek={seek} /></div>)}
            </div></div>
            <RegionEditor key={asset.id} project={project} asset={asset} region={region} set={setRegion} slices={slices}
              setSlices={value => config('slices', value, regionGroup)} addLabel={tool === 'cut' ? 'Schnitt' : 'Treffer'} detected={detected}
              onPlay={value => listen(value, selectionSeconds(asset, value)[0])} />
            <details className="grid-panel"><summary>Beat-Grid und erster Downbeat</summary><div className="field-grid">
              <Num label="BPM" value={bpm} min={30} max={300} step={.01} onChange={bpm => update({ ...edit, bpm, draft: { ...edit.draft, tempo_origin: 'manual' } })} />
              <Num label="Erster Downbeat · s" value={mark} min={0} max={duration} step={.001} onChange={downbeat => draft({ downbeat, tempo_origin: 'manual' })} />
            </div><div className="inline"><button disabled={bpm < 60} onClick={() => update({ ...edit, bpm: bpm / 2, draft: { ...edit.draft, tempo_origin: 'manual' } })}>Halbieren</button><button disabled={bpm > 150} onClick={() => update({ ...edit, bpm: bpm * 2, draft: { ...edit.draft, tempo_origin: 'manual' } })}>Verdoppeln</button>{analysis && <button onClick={() => update({ ...edit, bpm: Number(analysis.meta.report!.bpm), draft: { ...edit.draft, tempo_origin: 'detected' } })}>Erkanntes Tempo übernehmen</button>}</div><p className="hint">{meterN} Zählzeiten pro Takt · {edit.draft.tempo_origin === 'detected' ? 'Erkannt' : edit.draft.tempo_origin === 'manual' ? 'Manuell' : 'Projektvorgabe'}</p></details></>}
          {asset.role === 'midi' && <Piano key={asset.id} asset={asset} view={singleSettings(`midi:${asset.id}`).view as Midi | undefined}
            change={view => config('view', view, `midi:${asset.id}`)} edit={() => choose('midi')} />}
          {(asset.role === 'analysis' || typeof measured.lufs === 'number') && <div className="measure">
            <h3>Messwerte</h3><div className="measure-grid">{([['lufs','LUFS'],['true_peak','dBTP'],['lra','LRA'],['sample_peak','dBFS'],['bpm','BPM']] as const).map(([key, label]) => <div key={key}><strong>{typeof measured[key] === 'number' ? Number(measured[key]).toFixed(2) : '–'}</strong><small>{label}</small></div>)}</div>
            {asset.role === 'analysis' && asset.meta.report && <details><summary>Analyseprotokoll</summary><pre>{JSON.stringify(asset.meta.report, null, 2)}</pre></details>}</div>}
          {parentJob && <details className="grid-panel"><summary>Herkunft und Parameter{stalePreview ? ' · Vorschau mit älteren Parametern' : asset.meta.preview_render ? ' · Auswahlvorschau' : ''}</summary><p className="hint">{asset.meta.engine} · {source?.name || 'Projektquelle'}{asset.meta.seed !== undefined ? ` · Seed ${asset.meta.seed}` : ''}</p><pre>{JSON.stringify(parentJob.params, null, 2)}</pre></details>}
        </>}
      </section>
      {hideInspector && <button className="reopen desktop-only" onClick={() => setHideInspector(false)}>Werkzeuge</button>}
      <aside className={`inspector panel ${pane === 'inspector' ? 'panel-shown' : ''}`}>
        <div className="panel-heading"><h2>Inspektor</h2><button className="plain desktop-only" aria-label="Inspektor einklappen" onClick={() => setHideInspector(true)}>›</button><button className="plain compact-only" aria-label="Inspektor schließen" onClick={() => setPane('')}>×</button></div>
        <Inspector tool={tool} setTool={choose} settings={tool === 'midi' && asset ? { ...settings, view: singleSettings(`midi:${asset.id}`).view ?? asset.meta.midi } : settings}
          change={config} asset={asset} assets={assets} selected={selected} project={project} caps={caps}
          region={region} setRegion={setRegion} slices={slices} setSlices={value => asset && config('slices', value, regionGroup)}
          setGrid={(bpm, downbeat) => update({ ...edit, bpm, draft: { ...edit.draft, downbeat } })}
          tracks={tracks} setTrack={(item, track) => draft({ tracks: { ...tracks, [item]: track } })} run={submit} busy={running} />
        <label className="field width-control"><span>Breite des Inspektors</span><input type="range" min={320} max={360} value={inspectorWidth} onChange={event => setInspectorWidth(Number(event.target.value))} /></label>
      </aside>
    </div>
    <footer className="bottom">
      <div className="transport" aria-label="Zentraler Transport">
        <div className="inline transport-buttons"><button className="play" aria-label={player.playing ? 'Pause' : 'Abspielen'} disabled={!audio(asset) && asset?.role !== 'midi'} onClick={() => player.playing ? player.pause() : listen()}>{player.playing ? 'Ⅱ' : '▶'}</button>
          <button aria-label="Stopp" onClick={() => { player.pause(); player.seek(0) }}>■</button><TransportTime clock={player.position} /></div>
        <div className="inline transport-options"><button disabled={!audio(asset)} aria-pressed={loop} onClick={() => { setLoop(!loop); if (player.playing) listen(undefined, player.cursor.current, side, !loop) }}>Loop</button>
          <div className="ab"><button aria-pressed={side === 'base'} disabled={!source} onClick={() => alternate('base')}>A · Quelle</button><button aria-pressed={side === 'new'} disabled={!source} onClick={() => alternate('new')}>B · Variante</button></div>
          <button aria-pressed={matched} disabled={!pairReady} title={pairReady ? undefined : 'Beide Versionen zuerst auf LUFS prüfen'} onClick={() => setMatched(!matched)}>Pegelabgleich</button>
          <label className="monitor">Abhörpegel <input type="range" min="0" max="1" step=".01" value={player.volume} onChange={event => player.setVolume(Number(event.target.value))} /></label>
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
            <div><strong>{tools[job.tool]?.[0] ?? 'Export'}</strong><small>{job.cancel_requested && !terminal.has(job.state) ? 'Abbruch angefordert' : stateLabels[job.state] || job.state} · {job.phase}{typeof job.params.seed === 'number' ? ` · Seed ${job.params.seed}` : ''}</small>{job.error && <p className="hint">{job.error}</p>}</div>
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
