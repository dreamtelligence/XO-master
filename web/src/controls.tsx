import { useEffect, useId, useRef, useState, type CSSProperties } from 'react'
import { silentOutput, type OutputReading } from './transport'

export function Dial({ label, value, min, max, step = 1, onChange, suffix, live = false }: {
  label: string; value: number; min: number; max: number; step?: number; onChange: (value: number) => void;
  suffix?: string; live?: boolean;
}) {
  const drag = useRef<{ x: number; y: number; start: number } | null>(null)
  const [preview, setPreview] = useState<number | null>(null)
  const [typed, setTyped] = useState<string | null>(null)
  const id = useId()
  const current = preview ?? value
  const scale = Math.max(0, Math.min(1, (current - min) / (max - min)))
  const precision = (String(step).split('.')[1] ?? '').length
  const [caption, unit] = label.split(' · ', 2)

  function dragValue(x: number, y: number) {
    const origin = drag.current!
    const change = (origin.y - y + (x - origin.x) * .6) / 140 * (max - min)
    const stepped = (origin.start + change - min) / step
    return Number(Math.min(max, Math.max(min, min + Math.round(stepped) * step)).toFixed(precision))
  }

  function commitTyped() {
    if (typed === null) return
    const next = Number(typed)
    if (typed.trim() && Number.isFinite(next)) {
      const clamped = Number(Math.max(min, Math.min(max, next)).toFixed(precision))
      if (clamped !== value) onChange(clamped)
    }
    setTyped(null)
  }

  return <div className="dial">
    <label className="dial-label" htmlFor={id}>{caption}</label>
    <div className="dial-body" style={{ '--sweep': `${scale * 270}deg`, '--rotation': `${scale * 270 - 135}deg` } as CSSProperties}>
      <span className="dial-cap" aria-hidden="true"><span /></span>
      <input id={id} className="dial-slider" type="range" aria-label={label} aria-valuetext={`${current}${unit ? ` ${unit}` : suffix ?? ''}`}
        min={min} max={max} step={step} value={current} onChange={event => onChange(event.currentTarget.valueAsNumber)}
        onPointerDown={event => {
          if (!event.isPrimary || event.button !== 0) return
          event.preventDefault()
          event.currentTarget.focus()
          event.currentTarget.setPointerCapture(event.pointerId)
          drag.current = { x: event.clientX, y: event.clientY, start: current }
        }}
        onPointerMove={event => {
          if (!event.isPrimary || !drag.current) return
          const next = dragValue(event.clientX, event.clientY)
          setPreview(next)
          if (live && next !== value) onChange(next)
        }}
        onPointerUp={event => {
          if (!event.isPrimary || !drag.current) return
          const next = dragValue(event.clientX, event.clientY)
          drag.current = null
          setPreview(null)
          if (next !== value) onChange(next)
        }}
        onLostPointerCapture={() => { drag.current = null; setPreview(null) }} />
    </div>
    <div className="dial-readout">
      <input type="number" inputMode="decimal" aria-label={`${label} numerisch`} value={typed ?? current} min={min} max={max} step={step}
        onChange={event => setTyped(event.currentTarget.value)} onBlur={commitTyped}
        onKeyDown={event => { if (event.key === 'Enter') event.currentTarget.blur(); if (event.key === 'Escape') setTyped(null) }} />
      {(unit || suffix) && <span aria-hidden="true">{unit || suffix}</span>}
    </div>
  </div>
}

export function OutputMeter({ playing, read }: { playing: boolean; read: () => OutputReading }) {
  const [reading, setReading] = useState(silentOutput)
  const sample = useRef(read)
  sample.current = read
  useEffect(() => {
    if (!playing) return
    const timer = window.setInterval(() => setReading(sample.current()), 65)
    return () => { clearInterval(timer); setReading(silentOutput) }
  }, [playing])
  const { peaks, spectrum } = playing ? reading : silentOutput
  return <div className="output-display"><div className="output-meter" role="group" aria-label="Ausgangspegel in dBFS">
    <span className="meter-label">OUT</span>
    <div className="meter-rows">{(['L', 'R'] as const).map((channel, index) => {
      const peak = peaks[index]
      return <div className="meter-row" key={channel}><span aria-hidden="true">{channel}</span>
        <meter min={-48} max={0} value={peak} aria-label={`Ausgangspegel ${channel}`} />
        <span aria-hidden="true" className={peak === 0 ? 'clip' : ''}>{peak <= -48 ? '–' : peak.toFixed(0)}</span>
      </div>
    })}</div>
  </div>
    <div className="spectrum" title="Frequenzspektrum der Mono-Summe, von tief nach hoch" role="img" aria-label="Live-Frequenzspektrum der Mono-Summe">
      <div className="spectrum-bands" aria-hidden="true">{spectrum.map((value, i) => <span key={i} style={{ '--level': value } as CSSProperties} />)}</div>
      <div className="spectrum-labels" aria-hidden="true"><span>Tief</span><span>Hoch</span></div>
    </div>
  </div>
}
