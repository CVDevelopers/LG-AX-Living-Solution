import { useState } from 'react'

function IntervalBar({ f }) {
  // One shared scale for [T_lo, T_hi] and the T_req band — same distribution, two views.
  const max = Math.max(f.t_hi_min, f.t_req_hi, 1) * 1.15
  const pct = (v) => `${Math.min(100, (v / max) * 100)}%`
  return (
    <div className="interval-bar" aria-label="예상 시간 구간과 필요 시간">
      <div
        className="interval-range"
        style={{ left: pct(f.t_lo_min), width: pct(f.t_hi_min - f.t_lo_min) }}
      />
      <div
        className="treq-band"
        style={{ left: pct(f.t_req_lo), width: pct(f.t_req_hi - f.t_req_lo) }}
      />
      <div
        className="treq-tick"
        style={{ left: pct(f.t_req_min) }}
        title={`필요 ${f.t_req_min}분`}
      />
      <div className="est-tick" style={{ left: pct(f.t_est_min) }} />
    </div>
  )
}

export default function ForecastCard({ forecast, optimistic }) {
  const [showBasis, setShowBasis] = useState(false)
  if (!forecast) return <section className="card">예보 불러오는 중…</section>

  const f = forecast
  const tEst = optimistic ? optimistic.t_est_min : f.t_est_min
  const pDone = optimistic ? optimistic.p_complete : f.p_complete
  const basis = f.basis

  return (
    <section
      className={`card forecast ${optimistic ? 'optimistic' : ''}`}
      onClick={() => setShowBasis((v) => !v)}
      title="탭하면 산출 근거를 표시합니다"
    >
      <div className="forecast-main">
        <div>
          <div className="t-est">
            {Math.round(tEst)}
            <span className="unit">분</span>
          </div>
          <div className="t-range">
            {Math.round(f.t_lo_min)}–{Math.round(f.t_hi_min)}분 · 필요 {Math.round(f.t_req_min)}분
          </div>
        </div>
        <div className="p-complete">
          <div className="p-value">{Math.round(pDone * 100)}%</div>
          <div className="p-label">완료 확률</div>
        </div>
      </div>
      <IntervalBar f={f} />
      {basis.low_data && <span className="badge-lowdata">초기 추정</span>}
      {showBasis && (
        <div className="basis" onClick={(e) => e.stopPropagation()}>
          세그먼트 {basis.segments_used}개 · 드리프트 ×{basis.drift} · 프라이어{' '}
          {Math.round(basis.prior_weight * 100)}%
          <br />
          n_eff {basis.n_eff} · 기저율 {basis.base_rate}%/분 · {basis.interval_method} (B=
          {basis.B})
        </div>
      )}
    </section>
  )
}
