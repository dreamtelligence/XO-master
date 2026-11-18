import { useEffect, useMemo, useRef, useState } from 'react'
import { assetUrl, type Asset, type EffectStep, type Region, type Track } from './api'
import { LiveFx } from './live-fx'

export type PositionClock = { subscribe: (listener: () => void) => () => void; current: () => number }
export type OutputReading = { peaks: [number, number]; spectrum: number[] }
export const silentOutput: OutputReading = { peaks: [-48, -48], spectrum: Array<number>(22).fill(0) }

const WINDOW = 8
const PREFETCH = 5
const OPUS = typeof Audio !== "undefined" && Boolean(new Audio().canPlayType('audio/ogg; codecs="opus"'))
type ClockWindow = { position: number; started: number; until: number }
const LISTEN_CACHE_BYTES = 32 * 1024 * 1024
export type Source = { asset: Asset; gain: number; pan?: number; offset?: number; ratio?: number; sourceOffset?: number; regions?: { start: number; end: number; offset: number }[] }
const seconds = (n: number) => {
  const mm = Math.floor(n / 60), ss = Math.floor(n % 60), ms = Math.floor(n * 1000) % 1000
  return `${String(mm).padStart(2, '0')}:${String(ss).padStart(2, '0')}.${String(ms).padStart(3, '0')}`
}
export { seconds }

export function useTransport(onError: (message: string) => void) {
  const context = useRef<AudioContext | null>(null)
  const master = useRef<GainNode | null>(null)
  const analysers = useRef<AnalyserNode[]>([])
  const spectrum = useRef<{ node: AnalyserNode; data: Uint8Array<ArrayBuffer>; edges: number[] } | null>(null)
  const meterBuffer = useRef(new Float32Array(512))
  const nodes = useRef<AudioNode[]>([])
  const levels = useRef(new Map<string, {gain: number; pan: number}>())
  const mixer = useRef(new Set<{id: string; gain: GainNode; pan: StereoPannerNode}>())
  const controller = useRef<AbortController | null>(null)
  const live = useRef<LiveFx | null>(null)
  const listenCache = useRef(new Map<string, AudioBuffer>())
  const ticket = useRef(0)
  const next = useRef<number | undefined>(undefined)
  const clock = useRef<ClockWindow[]>([])
  const cursor = useRef(0)
  const listeners = useRef(new Set<() => void>())
  const position = useMemo<PositionClock>(() => ({
    subscribe(listener) {
      listeners.current.add(listener)
      return () => { listeners.current.delete(listener) }
    },
    current: () => cursor.current,
  }), [])
  const [playing, setPlaying] = useState(false)
  const [loading, setLoading] = useState(false)
  const [liveActive, setLiveActive] = useState(false)
  const [volume, setVolume] = useState(0.8)

  function outputBus(ctx: AudioContext) {
    if (master.current) return master.current
    const bus = ctx.createGain()
    bus.channelCount = 2
    bus.channelCountMode = 'explicit'
    const splitter = ctx.createChannelSplitter(2)
    bus.connect(ctx.destination)
    bus.connect(splitter)
    analysers.current = [0, 1].map(channel => {
      const analyser = ctx.createAnalyser()
      analyser.fftSize = meterBuffer.current.length
      splitter.connect(analyser, channel)
      return analyser
    })
    const frequency = ctx.createAnalyser()
    frequency.fftSize = 4096
    frequency.maxDecibels = -16
    const binWidth = ctx.sampleRate / frequency.fftSize
    const top = Math.min(18000, ctx.sampleRate / 2)
    const edges = Array.from({ length: silentOutput.spectrum.length + 1 }, (_, i) =>
      Math.round(35 * (top / 35) ** (i / silentOutput.spectrum.length) / binWidth))
    spectrum.current = { node: frequency, data: new Uint8Array(frequency.frequencyBinCount), edges }
    bus.connect(frequency)
    master.current = bus
    return bus
  }

  function readOutput(): OutputReading {
    const peak = (analyser?: AnalyserNode) => {
      if (!analyser) return -48
      analyser.getFloatTimeDomainData(meterBuffer.current)
      let maximum = 0
      for (const value of meterBuffer.current) maximum = Math.max(maximum, Math.abs(value))
      return Math.max(-48, Math.min(0, 20 * Math.log10(maximum)))
    }
    const monitor = spectrum.current
    if (!monitor) return silentOutput
    monitor.node.getByteFrequencyData(monitor.data)
    const bands = silentOutput.spectrum.map((_, i) => {
      const start = monitor.edges[i], end = Math.max(start + 1, monitor.edges[i + 1])
      let highest = 0
      for (let bin = start; bin < end; bin++) highest = Math.max(highest, monitor.data[bin])
      return highest / 255
    })
    return { peaks: [peak(analysers.current[0]), peak(analysers.current[1])], spectrum: bands }
  }

  function seekLocal(value: number) {
    cursor.current = Math.max(0, value)
    for (const listener of listeners.current) listener()
  }

  function reset() {
    ticket.current += 1
    live.current?.stop()
    live.current = null
    setLiveActive(false)
    controller.current?.abort()
    clearTimeout(next.current)
    for (const node of nodes.current) { try { (node as AudioScheduledSourceNode).stop?.() } catch { /* already ended */ } node.disconnect() }
    nodes.current = []
    mixer.current.clear()
    clock.current = []
  }

  function setLevels(sources: Source[]) {
    levels.current = new Map(sources.map(source => [source.asset.id, {gain: source.gain, pan: source.pan ?? 0}]))
    const now = context.current?.currentTime ?? 0
    for (const channel of mixer.current) {
      const value = levels.current.get(channel.id)
      if (value) {
        channel.gain.gain.setTargetAtTime(value.gain, now, .01)
        channel.pan.pan.setTargetAtTime(value.pan, now, .01)
      }
    }
  }

  function currentWindow(now: number) {
    while (clock.current.length > 1 && clock.current[1].started <= now) clock.current.shift()
    return clock.current[0]
  }

  function pause() {
    const now = context.current?.currentTime ?? 0
    const state = currentWindow(now)
    if (live.current) seekLocal(live.current.position)
    else if (state) seekLocal(Math.min(state.until, state.position + Math.max(0, now - state.started)))
    reset()
    setPlaying(false)
    setLoading(false)
  }

  async function playLive(asset: Asset, from: number, to: number, at: number, chain: EffectStep[], repeat: boolean, side: 'dry' | 'wet') {
    reset()
    const generation = ticket.current
    setLiveActive(true)
    setPlaying(true)
    setLoading(true)
    seekLocal(at)
    function finish(message?: string) {
      if (generation !== ticket.current) return
      if (live.current) seekLocal(live.current.position)
      reset(); setPlaying(false); setLoading(false)
      if (message) onError(message)
    }
    try {
      const ctx = context.current ??= new AudioContext()
      const bus = outputBus(ctx)
      bus.gain.value = volume
      await ctx.resume()
      if (generation !== ticket.current) return
      const session = live.current = new LiveFx(ctx, bus, chain, repeat, side, {
        playing: () => { if (generation === ticket.current) setLoading(false) },
        buffering: () => { if (generation === ticket.current) setLoading(true) },
        end: () => finish(), error: finish,
      })
      await session.open(asset, from, to, at)
    } catch (error) { finish(error instanceof Error ? error.message : String(error)) }
  }

  async function audioWindow(ctx: AudioContext, url: string, signal: AbortSignal) {
    const cache = listenCache.current
    const existing = cache.get(url)
    if (existing) {
      cache.delete(url)
      cache.set(url, existing)
      return existing
    }
    const response = await fetch(url, { signal })
    if (!response.ok) throw new Error('Die Audioauswahl konnte nicht vorgepuffert werden.')
    const buffer = await ctx.decodeAudioData(await response.arrayBuffer())
    if (!signal.aborted) {
      cache.set(url, buffer)
      let bytes = 0
      const size = (entry: AudioBuffer) => entry.length * entry.numberOfChannels * Float32Array.BYTES_PER_ELEMENT
      for (const entry of cache.values()) bytes += size(entry)
      for (const [key, entry] of cache) {
        if (bytes <= LISTEN_CACHE_BYTES) break
        cache.delete(key)
        bytes -= size(entry)
      }
    }
    return buffer
  }

  async function play(sources: Source[], start: number, end: number, repeat?: [number, number]) {
    reset()
    if (!sources.length || start >= end) return
    setLevels(sources)
    const generation = ticket.current
    try {
      const ctx = context.current ??= new AudioContext()
      const bus = outputBus(ctx)
      bus.gain.value = volume
      await ctx.resume()
      if (generation !== ticket.current) return
      setPlaying(true)
      async function loadWindow(at: number, limit: number, scheduled?: number) {
        if (generation !== ticket.current) return
        const span = Math.min(WINDOW, limit - at)
        if (span <= 0.001) { if (repeat) return loadWindow(repeat[0], repeat[1]); pause(); return }
        setLoading(scheduled === undefined)
        const abort = controller.current = new AbortController()
        const buffers = await Promise.all(sources.slice(0, 12).flatMap(source => {
          const rate = source.asset.meta.rate
          if (!rate) return []
          const ratio = source.ratio ?? 1
          const sections = source.regions ?? [{ start: source.offset ?? 0, end: (source.offset ?? 0) + ((source.asset.meta.seconds ?? 0) - (source.sourceOffset ?? 0)) / ratio, offset: source.sourceOffset ?? 0 }]
          return sections.filter(section => section.end > at && section.start < at + span).map(async section => {
            const start = Math.max(at, section.start)
            const from = section.offset + (start - section.start) * ratio
            const duration = (Math.min(section.end, at + span) - start) * ratio
            const url = assetUrl(source.asset, `window?from=${from}&seconds=${duration}`)
            const buffer = await (OPUS
              ? audioWindow(ctx, url + '&format=opus', abort.signal).catch(error => {
                if (abort.signal.aborted) throw error
                return audioWindow(ctx, url, abort.signal)
              })
              : audioWindow(ctx, url, abort.signal))
            return { source, start, buffer, duration }
          })
        }))
        if (generation !== ticket.current) return
        const anchor = Math.max(ctx.currentTime + 0.025, scheduled ?? 0)
        for (const { source, start: begin, buffer, duration: requested } of buffers) {
          const sound = ctx.createBufferSource(), fadeGain = ctx.createGain(), gain = ctx.createGain(), pan = ctx.createStereoPanner()
          const channel = {id: source.asset.id, gain, pan}
          const level = levels.current.get(channel.id)
          gain.gain.value = level?.gain ?? source.gain
          sound.buffer = buffer
          sound.playbackRate.value = source.ratio ?? 1
          pan.pan.value = level?.pan ?? source.pan ?? 0
          sound.connect(fadeGain).connect(gain).connect(pan).connect(bus)
          const when = anchor + begin - at
          const available = Math.min(buffer.duration, requested)
          const duration = available / sound.playbackRate.value
          const fade = Math.min(0.008, duration / 4)
          fadeGain.gain.setValueAtTime(0, when)
          fadeGain.gain.linearRampToValueAtTime(1, when + fade)
          fadeGain.gain.setValueAtTime(1, when + duration - fade)
          fadeGain.gain.linearRampToValueAtTime(0, when + duration)
          sound.start(when, 0, available)
          mixer.current.add(channel)
          const audioNodes = [sound, fadeGain, gain, pan]
          nodes.current.push(...audioNodes)
          sound.onended = () => {
            mixer.current.delete(channel)
            audioNodes.forEach(node => node.disconnect())
            nodes.current = nodes.current.filter(node => !audioNodes.some(candidate => candidate === node))
          }
        }
        const until = anchor + span
        currentWindow(ctx.currentTime)
        clock.current.push({ position: at, started: anchor, until: at + span })
        setLoading(false)
        const remaining = limit - at - span
        if (remaining > 0.001 || repeat) {
          next.current = window.setTimeout(() => void loadWindow(remaining > 0.001 ? at + span : repeat![0], limit, until).catch(failed),
            Math.max(0, (until - ctx.currentTime - Math.min(PREFETCH, span * 0.8)) * 1000))
        } else {
          next.current = window.setTimeout(() => {
            if (generation === ticket.current) { seekLocal(limit); reset(); setPlaying(false); setLoading(false) }
          }, Math.max(0, (until - ctx.currentTime) * 1000))
        }
      }
      function failed(error: unknown) {
        if (generation !== ticket.current) return
        reset(); setPlaying(false); setLoading(false)
        onError(error instanceof Error ? error.message : String(error))
      }
      await loadWindow(start, end).catch(failed)
    } catch (error) {
      if (generation === ticket.current) {
        setPlaying(false); setLoading(false)
        onError(error instanceof Error ? error.message : String(error))
      }
    }
  }

  async function playMidi(asset: Asset, start: number) {
    reset()
    const ctx = context.current ??= new AudioContext()
    const bus = outputBus(ctx)
    bus.gain.value = volume
    await ctx.resume()
    const when = ctx.currentTime + 0.035
    const end = start + 15
    for (const track of asset.meta.midi?.tracks ?? []) {
      for (const [a, b, pitch, velocity] of track.notes.filter(([a, b]) => a < end && b > start).slice(0, 700)) {
        const oscillator = ctx.createOscillator(), gain = ctx.createGain()
        oscillator.type = track.drums ? 'triangle' : 'sine'
        oscillator.frequency.value = 440 * 2 ** ((pitch - 69) / 12)
        oscillator.connect(gain).connect(bus)
        const on = when + Math.max(0, a - start), off = Math.min(when + b - start, when + 15, track.drums ? on + 0.08 : Infinity)
        gain.gain.setValueAtTime(0, on)
        gain.gain.linearRampToValueAtTime(velocity / 127 * 0.08, Math.min(on + 0.008, off))
        gain.gain.setTargetAtTime(0, Math.max(on, off - 0.01), 0.007)
        oscillator.start(on); oscillator.stop(off + 0.03)
        nodes.current.push(oscillator, gain)
      }
    }
    clock.current = [{ position: start, started: when, until: end }]
    setPlaying(true)
    next.current = window.setTimeout(() => { reset(); setPlaying(false) }, 15050)
  }

  useEffect(() => {
    if (!playing) return
    let frame = 0
    const tick = () => {
      const now = context.current?.currentTime ?? 0, state = currentWindow(now)
      if (live.current) seekLocal(live.current.position)
      else if (state && now >= state.started) seekLocal(Math.min(state.until, state.position + now - state.started))
      frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [playing])

  useEffect(() => () => { reset(); void context.current?.close() }, [])
  useEffect(() => { if (master.current && context.current) master.current.gain.setTargetAtTime(volume, context.current.currentTime, 0.015) }, [volume])

  return { playing, loading, liveActive, position, cursor, play, playLive, playMidi, pause, seek: seekLocal, volume, setVolume, setLevels, readOutput,
    updateLive: (chain: EffectStep[], loop: boolean) => live.current?.update(chain, loop),
    selectLive: (side: 'dry' | 'wet') => live.current?.select(side), readLive: () => live.current?.readSpectrum(),
  }
}

export function sourcesFor(assets: Asset[], tracks: Record<string, Track>, rate: number): Source[] {
  const solo = assets.some(asset => tracks[asset.id]?.solo)
  return assets.map(asset => ({
    asset, gain: tracks[asset.id]?.mute || (solo && !tracks[asset.id]?.solo) ? 0 : 10 ** ((tracks[asset.id]?.gain ?? 0) / 20), pan: tracks[asset.id]?.pan ?? 0,
    offset: (tracks[asset.id]?.offset ?? asset.meta.project_offset ?? 0) / rate,
  }))
}

export function selectionSeconds(asset: Asset, region: Region): [number, number] {
  return [region.start / asset.meta.rate!, region.end / asset.meta.rate!]
}
