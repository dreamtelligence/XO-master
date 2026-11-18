import { useEffect, useMemo, useRef, useState } from 'react'
import { assetUrl, type Asset, type Region, type Track } from './api'

export type PositionClock = { subscribe: (listener: () => void) => () => void; current: () => number }

const WINDOW = 8
export type Source = { asset: Asset; gain: number; pan?: number; offset?: number; ratio?: number; sourceOffset?: number; regions?: { start: number; end: number; offset: number }[] }
const seconds = (n: number) => {
  const mm = Math.floor(n / 60), ss = Math.floor(n % 60), ms = Math.floor(n * 1000) % 1000
  return `${String(mm).padStart(2, '0')}:${String(ss).padStart(2, '0')}.${String(ms).padStart(3, '0')}`
}
export { seconds }

export function useTransport(onError: (message: string) => void) {
  const context = useRef<AudioContext | null>(null)
  const master = useRef<GainNode | null>(null)
  const nodes = useRef<AudioNode[]>([])
  const levels = useRef(new Map<string, {gain: number; pan: number}>())
  const mixer = useRef(new Set<{id: string; gain: GainNode; pan: StereoPannerNode}>())
  const controller = useRef<AbortController | null>(null)
  const ticket = useRef(0)
  const next = useRef<number | undefined>(undefined)
  const clock = useRef({ position: 0, started: 0, until: 0 })
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
  const [volume, setVolume] = useState(0.8)

  function seekLocal(value: number) {
    cursor.current = Math.max(0, value)
    for (const listener of listeners.current) listener()
  }

  function reset() {
    ticket.current += 1
    controller.current?.abort()
    clearTimeout(next.current)
    for (const node of nodes.current) { try { (node as AudioScheduledSourceNode).stop?.() } catch { /* already ended */ } node.disconnect() }
    nodes.current = []
    mixer.current.clear()
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

  function pause() {
    const now = context.current?.currentTime ?? 0
    const state = clock.current
    if (playing && !loading) seekLocal(Math.min(state.until, state.position + Math.max(0, now - state.started)))
    reset()
    setPlaying(false)
    setLoading(false)
  }

  async function play(sources: Source[], start: number, end: number, repeat?: [number, number]) {
    reset()
    if (!sources.length || start >= end) return
    setLevels(sources)
    const generation = ticket.current
    try {
      const ctx = context.current ??= new AudioContext()
      const bus = master.current ??= ctx.createGain()
      if (!master.current || !ctx) return
      bus.connect(ctx.destination)
      bus.gain.value = volume
      await ctx.resume()
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
            const response = await fetch(assetUrl(source.asset, `window?from=${from}&seconds=${duration}`), { signal: abort.signal })
            if (!response.ok) throw new Error('Die Audioauswahl konnte nicht vorgepuffert werden.')
            return { source, start, buffer: await ctx.decodeAudioData(await response.arrayBuffer()) }
          })
        }))
        if (generation !== ticket.current) return
        const anchor = Math.max(ctx.currentTime + 0.025, scheduled ?? 0)
        for (const { source, start: begin, buffer } of buffers) {
          const sound = ctx.createBufferSource(), fadeGain = ctx.createGain(), gain = ctx.createGain(), pan = ctx.createStereoPanner()
          const channel = {id: source.asset.id, gain, pan}
          const level = levels.current.get(channel.id)
          gain.gain.value = level?.gain ?? source.gain
          sound.buffer = buffer
          sound.playbackRate.value = source.ratio ?? 1
          pan.pan.value = level?.pan ?? source.pan ?? 0
          sound.connect(fadeGain).connect(gain).connect(pan).connect(bus)
          const when = anchor + begin - at
          const duration = buffer.duration / sound.playbackRate.value
          const fade = Math.min(0.008, duration / 4)
          fadeGain.gain.setValueAtTime(0, when)
          fadeGain.gain.linearRampToValueAtTime(1, when + fade)
          fadeGain.gain.setValueAtTime(1, when + duration - fade)
          fadeGain.gain.linearRampToValueAtTime(0, when + duration)
          sound.start(when)
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
        clock.current = { position: at, started: anchor, until: at + span }
        setLoading(false)
        const remaining = limit - at - span
        if (remaining > 0.001 || repeat) {
          next.current = window.setTimeout(() => void loadWindow(remaining > 0.001 ? at + span : repeat![0], limit, until).catch(failed),
            Math.max(0, (until - ctx.currentTime - 0.35) * 1000))
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
    const bus = master.current ??= ctx.createGain()
    bus.connect(ctx.destination)
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
    clock.current = { position: start, started: when, until: end }
    setPlaying(true)
    next.current = window.setTimeout(() => { reset(); setPlaying(false) }, 15050)
  }

  useEffect(() => {
    if (!playing || loading) return
    let frame = 0
    const tick = () => {
      const now = context.current?.currentTime ?? 0, state = clock.current
      if (now >= state.started) seekLocal(Math.min(state.until, state.position + now - state.started))
      frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [playing, loading])

  useEffect(() => () => { reset(); void context.current?.close() }, [])
  useEffect(() => { if (master.current && context.current) master.current.gain.setTargetAtTime(volume, context.current.currentTime, 0.015) }, [volume])

  return { playing, loading, position, cursor, play, playMidi, pause, seek: seekLocal, volume, setVolume, setLevels }
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
