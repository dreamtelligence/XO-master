import { api, type Asset, type EffectStep } from './api'

type Side = 'dry' | 'wet'
type Session = { url: string; ticket: string; rate: number; frames: number; codec?: "pcm" | "adpcm" }
type Scheduled = { when: number; from: number; length: number }
type Block = { from: number; length: number; audio: AudioBuffer[] }
const ADPCM_STEPS = [7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 19, 21, 23, 25, 28, 31, 34, 37, 41, 45, 50, 55, 60,
  66, 73, 80, 88, 97, 107, 118, 130, 143, 157, 173, 190, 209, 230, 253, 279, 307, 337, 371, 408, 449, 494,
  544, 598, 658, 724, 796, 876, 963, 1060, 1166, 1282, 1411, 1552, 1707, 1878, 2066, 2272, 2499, 2749,
  3024, 3327, 3660, 4026, 4428, 4871, 5358, 5894, 6484, 7132, 7845, 8630, 9493, 10442, 11487, 12635,
  13899, 15289, 16818, 18500, 20350, 22385, 24623, 27086, 29794, 32767]
const ADPCM_INDEX = [-1, -1, -1, -1, 2, 4, 6, 8]

function decodeAdpcm(packet: DataView, base: number, data: Float32Array) {
  let sample = packet.getInt16(base, true)
  let index = packet.getUint8(base + 2)
  for (let i = 0; i < data.length; i++) {
    const code = (packet.getUint8(base + 3 + (i >> 1)) >> (i % 2 ? 0 : 4)) & 15
    const step = ADPCM_STEPS[index]
    const difference = (step >> 3) + (code & 4 ? step : 0) + (code & 2 ? step >> 1 : 0) + (code & 1 ? step >> 2 : 0)
    sample = Math.max(-32768, Math.min(32767, sample + (code & 8 ? -difference : difference)))
    index = Math.max(0, Math.min(88, index + ADPCM_INDEX[code & 7]))
    data[i] = sample / 32768
  }
}

export class LiveFx {
  private socket?: WebSocket
  private timer?: number
  private pending = 0
  private nextAt = 0
  private target = 0.3
  private readySeconds = 0
  private readonly ready: Block[] = []
  private ended = false
  private stopped = false
  private lastChain?: string
  private readonly scheduled: Scheduled[] = []
  private readonly sources = new Set<AudioBufferSourceNode>()
  private readonly paths: { analyser: AnalyserNode; gain: GainNode; values: Uint8Array<ArrayBuffer> }[]
  private session?: Session
  private start = 0
  private cursor = 0

  constructor(private context: AudioContext, bus: AudioNode, private chain: EffectStep[], private loop: boolean, side: Side,
    private events: { playing: () => void; buffering: () => void; end: () => void; error: (message: string) => void }) {
    this.paths = [0, 1].map(() => {
      const analyser = context.createAnalyser(), gain = context.createGain()
      analyser.fftSize = 2048
      analyser.smoothingTimeConstant = 0.76
      analyser.connect(gain).connect(bus)
      return { analyser, gain, values: new Uint8Array(analyser.frequencyBinCount) }
    })
    this.paths[0].gain.gain.value = side === 'dry' ? 1 : 0
    this.paths[1].gain.gain.value = side === 'wet' ? 1 : 0
  }

  async open(asset: Asset, from: number, to: number, position: number) {
    const rate = asset.meta.rate!
    const start = Math.round(from * rate), end = Math.round(to * rate)
    this.start = from
    this.cursor = position
    const hosted = window.location.protocol === "https:"
    // Hosted packet arrivals can pause for over two seconds even on a warm connection.
    this.target = hosted ? 2.65 : 0.3
    const session = await api<Session>(`/projects/${asset.project}/assets/${asset.id}/fx-live`, 'POST', {
      start, end, codec: hosted ? "adpcm" : "pcm", position: Math.max(start, Math.min(end - 1, Math.round(position * rate))), chain: this.chain,
    })
    if (this.stopped) return
    this.session = session
    const socket = this.socket = new WebSocket(session.url, ['xo-fx', session.ticket])
    socket.binaryType = 'arraybuffer'
    const startup = window.setTimeout(() => this.fail('Die Live-Vorschau konnte nicht gestartet werden.'), 20000)
    socket.onmessage = (event) => {
      if (this.stopped) return
      if (typeof event.data === 'string') {
        const status = JSON.parse(event.data)
        if (status.ready) {
          clearTimeout(startup)
          this.timer = window.setInterval(() => this.pump(), 12)
          this.pump()
        } else if (status.end) {
          this.ended = true
          this.schedule()
        }
      } else this.receive(event.data)
    }
    socket.onclose = () => {
      clearTimeout(startup)
      if (!this.ended && !this.stopped) this.fail('Die Live-Vorschau wurde unterbrochen. Starte sie erneut oder rendere die Auswahl.')
    }
  }

  private pump() {
    if (this.stopped || !this.session) return
    const now = this.context.currentTime
    if (this.ended) {
      if (this.nextAt <= now) { this.stop(); this.events.end() }
      return
    }
    if (this.socket?.readyState !== WebSocket.OPEN) return
    this.schedule()
    const duration = this.session.frames / this.session.rate
    const batch = this.session.codec === "adpcm" ? 3 : 1
    const chain = JSON.stringify(this.chain)
    while (Math.max(0, this.nextAt - now) + this.readySeconds + this.pending * duration < this.target) {
      this.socket.send(JSON.stringify({ loop: this.loop, ...(batch > 1 ? { blocks: batch } : {}),
        ...(chain === this.lastChain ? {} : { chain: this.chain }) }))
      this.lastChain = chain
      this.pending += batch
    }
  }

  private receive(packet: ArrayBuffer) {
    const frame = new DataView(packet)
    const rate = this.session!.rate
    const compressed = this.session!.codec === "adpcm"
    let offset = 0
    while (offset + 8 <= packet.byteLength) {
      const from = this.start + frame.getUint32(offset, true) / rate
      const count = frame.getUint32(offset + 4, true)
      offset += 8
      const stride = compressed ? 3 + Math.ceil(count / 2) : count * 2
      if (!this.pending || !count || count > this.session!.frames || offset + stride * 4 > packet.byteLength ||
        (compressed && [0, 1, 2, 3].some(channel => frame.getUint8(offset + channel * stride + 2) > 88))) {
        this.fail('Ein Audioblock war unvollständig.')
        return
      }
      this.pending--
      const audio = this.paths.map((_, side) => {
        const buffer = this.context.createBuffer(2, count, rate)
        for (let channel = 0; channel < 2; channel++) {
          const data = buffer.getChannelData(channel)
          const base = offset + (side * 2 + channel) * stride
          if (compressed) decodeAdpcm(frame, base, data)
          else for (let i = 0; i < count; i++) data[i] = frame.getInt16(base + i * 2, true) / 32768
        }
        return buffer
      })
      offset += stride * 4
      const length = count / rate
      this.ready.push({ from, length, audio })
      this.readySeconds += length
    }
    if (!offset || offset !== packet.byteLength) {
      this.fail('Ein Audioblock war unvollständig.')
      return
    }
    this.schedule()
    this.pump()
  }

  private schedule() {
    const now = this.context.currentTime
    if (this.nextAt && this.nextAt <= now && !this.ended) {
      this.nextAt = 0
      this.target = Math.min(4, this.target * 1.6)
      this.events.buffering()
    }
    const starting = !this.nextAt
    if (!this.ready.length || (starting && !this.ended && this.readySeconds + 0.001 < this.target)) return
    let when = Math.max(now + (starting || this.ended ? 0.025 : 0), this.nextAt)
    for (const { from, length, audio } of this.ready) {
      this.paths.forEach(({ analyser }, side) => {
        const source = this.context.createBufferSource()
        source.buffer = audio[side]
        source.connect(analyser)
        source.onended = () => { source.disconnect(); this.sources.delete(source) }
        this.sources.add(source)
        source.start(when)
      })
      this.scheduled.push({ when, from, length })
      when += length
    }
    this.ready.length = 0
    this.readySeconds = 0
    this.nextAt = when
    if (starting) this.events.playing()
  }

  get position() {
    const now = this.context.currentTime
    while (this.scheduled.length > 1 && this.scheduled[1].when <= now) this.scheduled.shift()
    const block = this.scheduled[0]
    if (block) this.cursor = block.from + Math.max(0, Math.min(block.length, now - block.when))
    return this.cursor
  }

  update(chain: EffectStep[], loop: boolean) { this.chain = chain; this.loop = loop }

  select(side: Side) {
    const now = this.context.currentTime
    this.paths.forEach(({ gain }, i) => gain.gain.setTargetAtTime(Number(side === (i ? 'wet' : 'dry')), now, 0.007))
  }

  readSpectrum() {
    return this.paths.map(({ analyser, values }) => {
      analyser.getByteFrequencyData(values)
      return Array.from({ length: 72 }, (_, i) => {
        const freq = 35 * (18000 / 35) ** (i / 71)
        return values[Math.min(values.length - 1, Math.round(freq * analyser.fftSize / this.context.sampleRate))] / 255
      })
    })
  }

  private fail(message: string) { this.stop(); this.events.error(message) }

  stop() {
    this.stopped = true
    clearInterval(this.timer)
    this.socket?.close()
    for (const source of this.sources) { source.onended = null; source.stop(); source.disconnect() }
    this.sources.clear()
    for (const { analyser, gain } of this.paths) { analyser.disconnect(); gain.disconnect() }
  }
}
