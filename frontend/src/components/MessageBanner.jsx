import { useState } from 'react'

const MODE_KO = { eco: '에코', standard: '표준', turbo: '터보' }

// §4.2 message policy: no failure framing, always offer a choice.
function content(f) {
  const pCur = Math.round(f.p_complete * 100)
  switch (f.state) {
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
      // M0에서는 부족A(구역 선택)가 M1 플래너와 함께 도착 — 부족B 메시지로 안내 (§13).
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

export default function MessageBanner({ forecast, onSwitchMode }) {
  const [dismissedFor, setDismissedFor] = useState(null)
  const [toast, setToast] = useState(null)
  if (!forecast) return null

  const c = content(forecast)
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
