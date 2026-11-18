export type Role = 'original' | 'reference' | 'stem' | 'variant' | 'loop' | 'oneshot' | 'midi' | 'take' | 'analysis' | 'export'
export type Region = { start: number; end: number; name?: string; fade_in?: number; fade_out?: number; snap_zero?: boolean }
export type Note = [start: number, end: number, pitch: number, velocity: number]
export type Midi = { tracks: { name: string; program: number; drums: boolean; notes: Note[]; bends: [number, number][]; controls?: [number, number, number][] }[]; tempo: number[][]; signatures: number[][] }
export const midiHasNotes = (midi?: Midi) => midi?.tracks?.some(track => track.notes?.length > 0) ?? false
export type Track = { gain: number; pan: number; offset: number; mute: boolean; solo: boolean; start?: number; end?: number }
export type EffectStep = { effect: string; bypass?: boolean } & Record<string, number | string | boolean | undefined>
export type Draft = { template?: string; template_version?: number; downbeat?: number; tempo_origin?: string; tool?: string; regions?: Record<string, Region>; tracks?: Record<string, Track>; settings?: Record<string, unknown>; recipe?: {tool: string; label: string; version: number; feed?: "result" | "input" | "initial"; output?: string}[] }
export type Project = { id: string; name: string; rate: number; bpm: number; meter: string; purpose: 'private' | 'release'; revision: number; archived: number; draft: Draft }
export type TonalKey = { tonic: number; mode: 'major' | 'minor' }
export const pitchNames = ['C', 'C♯', 'D', 'E♭', 'E', 'F', 'F♯', 'G', 'A♭', 'A', 'B♭', 'H']
export const keyName = ({ tonic, mode }: TonalKey) => `${pitchNames[tonic]}-${mode === 'major' ? 'Dur' : 'Moll'}`
export function tonalKey(value: unknown): TonalKey | undefined {
  if (typeof value !== 'object' || !value) return
  const { tonic, mode } = value as Partial<TonalKey>
  if (typeof tonic === 'number' && Number.isInteger(tonic) && tonic >= 0 && tonic < 12 && (mode === 'major' || mode === 'minor')) return { tonic, mode }
}
export type Metadata = {
  seconds?: number; rate?: number; channels?: number; bits?: number; samples?: number; peaks?: number[]; codec?: string;
  sample_peak?: number; clipped_samples?: number; nonfinite_samples?: number; lufs?: number; true_peak?: number; lra?: number;
  group?: string; stem?: string; seed?: number; engine?: string; midi?: Midi; report?: Record<string, unknown>; bpm?: number; key?: TonalKey;
  preview_render?: boolean; project_offset?: number; source_start?: number; source_end?: number; source_rate?: number; ratio?: number;
  comparison_lufs?: [number, number];
  edit_map?: {source_start: number; source_end: number; result_start: number}[]; target_lufs?: number; target_true_peak?: number;
  qa_warnings?: number; operation?: { tool: string; parameters: Record<string, unknown> }; source_asset?: string; meter?: string; experiment?: boolean
}
export type Asset = { id: string; project: string; name: string; role: Role; hash: string; suffix: string; meta: Metadata; parents: string[]; hidden: number; job?: string }
export type Job = { id: string; tool: string; inputs: string[]; params: Record<string, unknown>; state: string; phase: string; progress: number | null; error?: string; remote_id?: string; cancel_requested: number; created: number }
export type Workspace = { project: Project; assets: Asset[]; jobs: Job[] }
export type Capabilities = { tools: Record<string, string>; online?: boolean; effect_plugins?: Record<string, string>; live_effects?: boolean; generation_seconds: number; upload_bytes: number; used_bytes: number; storage_bytes: number; legacy: boolean }
export const audio = (asset?: Asset): asset is Asset & { meta: Metadata & { rate: number; samples: number; seconds: number } } => Boolean(asset?.meta?.rate && asset?.meta.samples)
export const assetUrl = (asset: Asset, mode: string) => `/api/projects/${asset.project}/assets/${asset.id}/${mode}`
export const terminal = new Set(['completed', 'partial', 'failed', 'cancelled', 'submission_unknown', 'output_unconfirmed'])
let session: Promise<string> | undefined

async function csrf() {
  session ??= fetch('/api/session').then(async response => {
    if (!response.ok) throw new Error('Lokale Sitzung konnte nicht geöffnet werden.')
    return (await response.json()).session as string
  }).catch(error => { session = undefined; throw error })
  return session
}
export async function api<T>(path: string, method = 'GET', data?: unknown): Promise<T> {
  const headers: Record<string, string> = {}
  if (method !== 'GET') headers['X-Workspace-Session'] = await csrf()
  if (data !== undefined) headers['Content-Type'] = 'application/json'
  const response = await fetch('/api' + path, { method, headers, body: method === 'GET' ? undefined : JSON.stringify(data ?? {}) })
  const body = await response.json()
  if (!response.ok) {
    if (body.code === 'session') session = undefined
    throw new Error(body.detail || 'Die Anfrage ist fehlgeschlagen.')
  }
  return body as T
}

export async function upload<T>(path: string, file: File, onProgress: (percent: number | null) => void) {
  const token = await csrf()
  return new Promise<T>((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', '/api' + path)
    xhr.setRequestHeader('X-Workspace-Session', token)
    xhr.setRequestHeader('Content-Type', 'application/octet-stream')
    xhr.upload.onprogress = event => onProgress(event.lengthComputable ? Math.round(event.loaded / event.total * 100) : null)
    xhr.onload = () => {
      try {
        const body = JSON.parse(xhr.responseText)
        if (xhr.status >= 200 && xhr.status < 300) resolve(body)
        else reject(new Error(body.detail || 'Import fehlgeschlagen.'))
      } catch { reject(new Error('Der Server hat den Import nicht bestätigt.')) }
    }
    xhr.onerror = () => reject(new Error('Verbindung beim Import unterbrochen.'))
    xhr.send(file)
  })
}
