const MODES = [
  { id: 'eco', label: '에코', hint: '저소음·저전력' },
  { id: 'standard', label: '표준', hint: '일상 청소' },
  { id: 'turbo', label: '터보', hint: '강력 흡입' },
]

export default function ModeSelector({ mode, forecast, onChange }) {
  return (
    <section className="mode-selector" role="radiogroup" aria-label="청소 모드">
      {MODES.map((m) => {
        const pm = forecast?.per_mode?.[m.id]
        return (
          <button
            key={m.id}
            role="radio"
            aria-checked={mode === m.id}
            className={`mode-btn ${mode === m.id ? 'active' : ''}`}
            onClick={() => onChange(m.id)}
          >
            <span className="mode-label">{m.label}</span>
            <span className="mode-hint">{m.hint}</span>
            {pm && (
              <span className="mode-p">
                {Math.round(pm.t_est_min)}분 · {Math.round(pm.p_complete * 100)}%
              </span>
            )}
          </button>
        )
      })}
    </section>
  )
}
