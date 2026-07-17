import { useEffect, useState } from 'react'
import { getReport, getSessions } from '../api/client.js'

const MODE_KR = { eco: '절약', standard: '표준', turbo: '강력' }

function label(session) {
  const md = session.started_at?.slice(5, 10).replace('-', '/') ?? ''
  const done = session.completed ? '완료' : '중단'
  return `${md} · ${MODE_KR[session.mode] ?? session.mode} · ${Math.round(session.cleaned_area_m2)}㎡ · ${done}`
}

// Direction is carried in text ("빨리"/"느리게"), not colour, so the reading survives CVD (§7.3).
function FactorBar({ factor, max }) {
  const width = Math.min(100, (Math.abs(factor.contribution_min) / (max || 1)) * 100)
  const sign = factor.contribution_min >= 0 ? '+' : '−'
  const dir = factor.direction === 'faster' ? '빨리' : '느리게'
  return (
    <div className="factor-row">
      <span className="factor-label">{factor.label}</span>
      <div className="factor-track">
        <div className="factor-fill" style={{ width: `${width}%` }} />
      </div>
      <span className="factor-val">
        {sign}
        {Math.abs(factor.contribution_min).toFixed(1)}분 {dir}
      </span>
    </div>
  )
}

export default function ReportView() {
  const [sessions, setSessions] = useState([])
  const [selected, setSelected] = useState('')
  const [report, setReport] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    getSessions()
      .then((s) => {
        setSessions(s)
        if (s.length) setSelected(s[0].session_id)
      })
      .catch((e) => setError(e.message))
  }, [])

  useEffect(() => {
    if (!selected) return
    setReport(null)
    getReport(selected)
      .then(setReport)
      .catch((e) => setError(e.message))
  }, [selected])

  if (error) return <div className="error-box">보고서를 불러올 수 없어요 — {error}</div>
  if (!sessions.length) return <section className="card">세션 기록이 없어요.</section>

  const f = report?.facts
  const maxContribution = report
    ? Math.max(...report.factors.map((x) => Math.abs(x.contribution_min)), 0.1)
    : 1

  return (
    <>
      <select
        className="report-select"
        value={selected}
        onChange={(e) => setSelected(e.target.value)}
        aria-label="세션 선택"
      >
        {sessions.map((s) => (
          <option key={s.session_id} value={s.session_id}>
            {label(s)}
          </option>
        ))}
      </select>

      {!report && <section className="card">보고서 불러오는 중…</section>}

      {report && (
        <>
          <section className="card narration">
            <p>{report.narration.text}</p>
            {!report.narration.guardrail_ok && (
              <span className="badge-lowdata">수치 검증 실패</span>
            )}
          </section>

          <section className="card">
            <div className="fact-chips">
              <span className="chip">{MODE_KR[f.mode] ?? f.mode} 모드</span>
              <span className="chip">{Math.round(f.duration_min)}분</span>
              <span className="chip">{f.cleaned_area_m2}㎡</span>
              <span className="chip">{f.charged ? '충전 후 재개' : `배터리 ${f.dsoc}%`}</span>
              <span className="chip">{f.completed ? '전체 완료' : '중단'}</span>
              {f.high_obstacle && <span className="chip warn">장애물 많음</span>}
              {f.mode_changes > 0 && <span className="chip">모드 변경</span>}
            </div>
          </section>

          <section className="card">
            <div className="factor-title">소모 요인 분해 (§3.6)</div>
            {report.factors.map((factor) => (
              <FactorBar key={factor.feature} factor={factor} max={maxContribution} />
            ))}
          </section>
        </>
      )}
    </>
  )
}
