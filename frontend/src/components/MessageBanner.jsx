import { useState } from 'react'

const MODE_KO = { eco: '에코', standard: '표준', turbo: '터보' }

// §4.2 message policy: no failure framing, always offer a choice.
function content(f, plan) {
  const pCur = Math.round(f.p_complete * 100)
  switch (f.state) {
    case 'shortage_a': {
      // 부족A (§4.2): some zone subset still completes — steer to the plan, not to failure.
      const names = plan?.zones?.map((z) => z.name).join('·')
      const pS = plan ? Math.round(plan.p_complete * 100) : null
      return {
        cls: 'bad',
        icon: '🪫',
        head: '구역 선택 권장',
        body: names
          ? `지금 배터리로는 ${names}만 완결할 수 있어요 (확률 ${pS}%). 마치고 충전할까요?`
          : '지금 배터리로는 일부 구역만 완결할 수 있어요. 아래에서 구역과 경로를 확인하세요.',
        actions: [{ label: '충전 먼저', kind: 'ghost', act: 'toast' }],
      }
    }
    case 'sufficient':
      return {
        cls: 'ok',
        icon: '✅',
        head: '청소 가능',
        body: `${MODE_KO[f.mode]} 모드로 전체 청소를 마칠 수 있어요. 예상 ${Math.round(
          f.t_est_min,
        )}분 · 완료 확률 ${pCur}%`,
        actions: [{ label: '지금 시작', kind: 'primary', act: 'toast' }],
      }
    case 'caution': {
      const best = f.recommended_mode
      const pBest = best ? Math.round(f.per_mode[best].p_complete * 100) : pCur
      return {
        cls: 'warn',
        icon: '⚠️',
        head: '모드 변경 권장',
        body: best
          ? `현재 완료 확률 ${pCur}%. ${MODE_KO[best]} 전환 시 ${pBest}%까지 올라가요`
          : `현재 완료 확률 ${pCur}%. 데이터가 쌓이면 예보가 더 정확해져요`,
        actions: best
          ? [
              { label: `${MODE_KO[best]}로 전환`, kind: 'primary', act: 'switch', mode: best },
              { label: '그대로 진행', kind: 'ghost', act: 'dismiss' },
            ]
          : [{ label: '그대로 진행', kind: 'ghost', act: 'dismiss' }],
      }
    }
    default:
      // 부족B (§4.2): no zone subset completes → charge first.
      return {
        cls: 'bad',
        icon: '🔌',
        head: '충전 필요',
        body: `완결 가능한 구역이 없어요. 약 ${Math.round(
          f.charge_min,
        )}분 충전 후 전체 청소를 권장해요`,
        actions: [{ label: '충전 시작', kind: 'primary', act: 'toast' }],
      }
  }
}

export default function MessageBanner({ forecast, plan, onSwitchMode }) {
  const [dismissedFor, setDismissedFor] = useState(null)
  const [toast, setToast] = useState(null)
  if (!forecast) return null

  const c = content(forecast, plan)
  const key = `${forecast.state}:${forecast.recommended_mode ?? ''}`
  if (dismissedFor === key) return null

  const onAction = (a) => {
    if (a.act === 'switch') onSwitchMode(a.mode)
    else if (a.act === 'dismiss') setDismissedFor(key)
    else {
      setToast('실기기 연동은 이후 마일스톤에서 제공됩니다')
      setTimeout(() => setToast(null), 2200)
    }
  }

  return (
    <section className={`banner ${c.cls}`} role="status">
      <div className="banner-head">
        <span aria-hidden="true">{c.icon}</span> {c.head}
      </div>
      <p>{c.body}</p>
      <div className="banner-actions">
        {c.actions.map((a) => (
          <button key={a.label} className={`btn ${a.kind}`} onClick={() => onAction(a)}>
            {a.label}
          </button>
        ))}
      </div>
      {toast && <div className="toast">{toast}</div>}
    </section>
  )
}
