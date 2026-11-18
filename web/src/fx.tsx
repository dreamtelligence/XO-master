import { useEffect, useRef, useSyncExternalStore, type CSSProperties } from 'react'
import { ArrowDownToLine, AudioWaveform, Pause, Play } from 'lucide-react'
import type { Asset } from './api'
import { seconds, type PositionClock } from './transport'

export type FxSide = 'dry' | 'wet'

export function FxScope({ running, read, large = false }: { running: boolean; read: () => number[][] | undefined; large?: boolean }) {
  const canvas = useRef<HTMLCanvasElement>(null)
  const readLatest = useRef(read)
  readLatest.current = read
  useEffect(() => {
    const element = canvas.current!
    const ctx = element.getContext('2d')
    if (!ctx) return
    let frame = 0
    function draw() {
      const width = element.clientWidth, height = element.clientHeight, ratio = Math.min(devicePixelRatio, 2)
      const w = Math.round(width * ratio), h = Math.round(height * ratio)
      if (element.width !== w || element.height !== h) { element.width = w; element.height = h }
      const view = ctx!
      view.setTransform(ratio, 0, 0, ratio, 0, 0)
      view.clearRect(0, 0, width, height)
      const bottom = height - 18, left = 9, right = Math.max(left, width - 13)
      view.font = '9px ui-monospace, monospace'
      view.textAlign = 'center'
      view.strokeStyle = '#685c763d'
      view.fillStyle = '#bdb0d0'
      const hz = large ? [50, 100, 250, 1000, 4000, 10000] : [100, 1000, 10000]
      for (const frequency of hz) {
        const x = left + Math.log(frequency / 35) / Math.log(18000 / 35) * (right - left)
        view.beginPath(); view.moveTo(x, 6); view.lineTo(x, bottom); view.stroke()
        view.fillText(frequency >= 1000 ? `${frequency / 1000}k` : String(frequency), x, height - 5)
      }
      view.beginPath(); view.moveTo(left, bottom); view.lineTo(right, bottom); view.stroke()
      if (running) {
        readLatest.current()?.forEach((band, side) => {
          view.beginPath()
          band.forEach((value, i) => {
            const x = left + (right - left) * i / (band.length - 1)
            const y = bottom - (bottom - 8) * value
            if (i === 0) view.moveTo(x, y); else view.lineTo(x, y)
          })
          view.strokeStyle = side ? '#f3a8d3' : '#bba4f1'
          view.lineWidth = side ? 2 : 1.5
          view.stroke()
        })
        frame = requestAnimationFrame(draw)
      }
    }
    const observer = new ResizeObserver(() => { if (!running) draw() })
    observer.observe(element)
    draw()
    return () => { cancelAnimationFrame(frame); observer.disconnect() }
  }, [running, large])
  return <div className={`rack-display${large ? ' rack-display-large' : ''}`}>
    <div className="rack-legend"><span>Quelle</span><span>Effekt</span><small>Hz</small></div>
    <canvas ref={canvas} role="img" aria-label="Frequenzspektrum von Quelle und Effekt" />
  </div>
}

function AuditionCursor({ clock, length }: { clock: PositionClock; length: number }) {
  const cursor = useSyncExternalStore(clock.subscribe, clock.current)
  return <span className="fx-cursor" aria-hidden="true" style={{ left: `${Math.min(1, cursor / length) * 100}%` }} />
}

export function FxCompare({ source, wet, window, clock, side, playing, state, render, listen, matched, setMatched, inCart, exportWet }: {
  source: Asset; wet?: Asset; window: [number, number]; clock: PositionClock; side: FxSide | null; playing: boolean;
  state: string; render?: () => void; listen: (side: FxSide) => void; matched: boolean; setMatched: (value: boolean) => void;
  inCart: boolean; exportWet: () => void;
}) {
  const [from, to] = window
  const clipLength = to - from
  const length = wet?.meta.seconds ?? clipLength
  const tail = Math.max(0, length - clipLength)

  return <section className="fx-compare" aria-label="Effekt-Hörvergleich">
    <header className="fx-compare-header">
      <div className="fx-compare-title"><AudioWaveform size={19} aria-hidden="true" /><div><h3>Effekt-Hörvergleich</h3>
        <p>{seconds(from)}–{seconds(to)}{tail > .005 ? ` · +${tail.toLocaleString('de-DE', { maximumFractionDigits: 2 })} s Ausklang` : ''}</p></div></div>
      <button className="primary" disabled={!render} onClick={render}>{state === 'Rendert …' ? state : 'Ausschnitt rendern'}</button>
    </header>
    <div className="fx-signals" style={{ '--dry-end': `${clipLength / length * 100}%` } as CSSProperties}>
      {(['dry', 'wet'] as const).map((key, index) => {
        const asset = index ? wet : source
        const peaks = asset?.meta.peaks ?? []
        const bars = Array.from({ length: 84 }, (_, bin) => {
          const time = length * bin / 84
          if (!asset || (!index && time >= clipLength)) return 0
          const offset = index ? time : time + from
          const scale = peaks.length / asset.meta.seconds!
          const a = Math.floor(offset * scale)
          const b = Math.max(a + 1, Math.min(peaks.length, Math.ceil((offset + length / 84) * scale)))
          return Math.max(0, ...peaks.slice(a, b))
        })
        return <div className="fx-signal" data-channel={key} key={key}>
          <button type="button" disabled={!asset} aria-pressed={side === key} aria-label={`${index ? 'B Effektsignal' : 'A Trocken'} ${side === key && playing ? 'pausieren' : 'hören'}`} onClick={() => listen(key)}>
            {side === key && playing ? <Pause size={13} aria-hidden="true" /> : <Play size={13} aria-hidden="true" />}<span><strong>{index ? 'B' : 'A'}</strong> {index ? 'Effekt' : 'Trocken'}</span>
          </button>
          <div className="fx-signal-display" role="img" aria-label={index ? 'Wellenform der Effektvorschau' : 'Wellenform des trockenen Ausschnitts'}>
            {asset ? <div className="fx-bins" aria-hidden="true">{bars.map((peak, bin) => <i key={bin} style={{ '--peak': Math.sqrt(peak) } as CSSProperties} />)}</div> : <span className="fx-signal-empty">{state}</span>}
            {tail > .005 && <span className="fx-tail" aria-hidden="true" />}
            {side && <AuditionCursor clock={clock} length={length} />}
          </div>
        </div>
      })}
    </div>
    <footer className="fx-compare-footer">
      <label className="check"><input type="checkbox" checked={Boolean(wet?.meta.comparison_lufs && matched)} disabled={!wet?.meta.comparison_lufs} onChange={event => setMatched(event.target.checked)} />Pegelabgleich</label>
      {wet && <button type="button" className="plain" aria-pressed={inCart} onClick={exportWet}><ArrowDownToLine size={14} aria-hidden="true" />{inCart ? 'Im Exportkorb' : 'Vorschau in Exportkorb'}</button>}
    </footer>
  </section>
}
