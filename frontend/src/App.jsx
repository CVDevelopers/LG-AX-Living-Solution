import { useCallback, useEffect, useRef, useState } from 'react'
import { getHeatmap, getPlan, getPredict } from './api/client.js'
import { nextPlanStore } from './api/storage.js'
import BatteryHeader from './components/BatteryHeader.jsx'
import ForecastCard from './components/ForecastCard.jsx'
import HeatmapView from './components/HeatmapView.jsx'
import MessageBanner from './components/MessageBanner.jsx'
import ModeSelector from './components/ModeSelector.jsx'
import PlanOverlay from './components/PlanOverlay.jsx'
import ReportView from './views/ReportView.jsx'

const DEBOUNCE_MS = 250

export default function App() {
  const [battery, setBattery] = useState(55) // opens on a rich heatmap gradient; slide to 18 % → 부족A
  const [mode, setMode] = useState('standard')
  const [tab, setTab] = useState('forecast') // 예보 | 보고서 (§7.1)
  const [forecast, setForecast] = useState(null)
  const [heatmap, setHeatmap] = useState(null)
  const [plan, setPlan] = useState(null)
  const [showRoute, setShowRoute] = useState(false)
  const [deferred, setDeferred] = useState(false)
  const [optimistic, setOptimistic] = useState(null) // per_mode cache shown ≤300 ms (§7.2)
  const [error, setError] = useState(null)
  const [carryover, setCarryover] = useState(null) // pending next_plan (§4.2 이월)
  const [toast, setToast] = useState(null)
  const prevState = useRef(null)
  const timer = useRef(null)

  useEffect(() => {
    setCarryover(nextPlanStore.getPending())
  }, [])

  const refresh = useCallback((batteryPct, m) => {
    clearTimeout(timer.current)
    timer.current = setTimeout(async () => {
      try {
        const [data, hm] = await Promise.all([
          getPredict({ battery: batteryPct, mode: m, prevState: prevState.current }),
          getHeatmap({ battery: batteryPct, mode: m }).catch(() => null),
        ])
        prevState.current = data.state // hysteresis feedback (§4.1)
        setForecast(data)
        setHeatmap(hm)
        setOptimistic(null)
        setError(null)
        // Plan is only needed for 부족A; keep it in lockstep with the shared distribution (§5.1).
        if (data.state === 'shortage_a') {
          const body = await getPlan({ battery: batteryPct }).catch(() => null)
          setPlan(body?.feasible ? body.plan : null)
        } else {
          setPlan(null)
          setShowRoute(false)
        }
      } catch (err) {
        setError(err.message)
      }
    }, DEBOUNCE_MS)
  }, [])

  useEffect(() => {
    setShowRoute(false)
    setDeferred(false)
    refresh(battery, mode)
    return () => clearTimeout(timer.current)
  }, [battery, mode, refresh])

  // Optimistic mode switch: paint cached per_mode numbers immediately, confirm via refetch.
  const changeMode = (next) => {
    if (forecast?.per_mode?.[next]) {
      setOptimistic({ mode: next, ...forecast.per_mode[next] })
    }
    setMode(next)
  }

  const flash = (msg) => {
    setToast(msg)
    setTimeout(() => setToast(null), 2200)
  }

  const deferLeftover = (zoneIds, zoneNames) => {
    nextPlanStore.defer({ zoneIds, zoneNames, mode: plan?.mode ?? mode, reason: 'shortage_a' })
    setDeferred(true)
    flash(`${zoneNames.join('·')}를 다음에 예약했어요`)
  }

  const acceptCarryover = () => {
    nextPlanStore.consume()
    if (carryover?.mode) changeMode(carryover.mode)
    flash(`지난번 미룬 ${(carryover?.zone_names ?? []).join('·') || '구역'}부터 안내할게요`)
    setCarryover(null)
  }

  const dismissCarryover = () => {
    nextPlanStore.consume()
    setCarryover(null)
  }

  return (
    <div className="app">
      <BatteryHeader battery={battery} onChange={setBattery} />

      <nav className="tabs" role="tablist">
        <button
          className={`tab ${tab === 'forecast' ? 'active' : ''}`}
          role="tab"
          aria-selected={tab === 'forecast'}
          onClick={() => setTab('forecast')}
        >
          예보
        </button>
        <button
          className={`tab ${tab === 'report' ? 'active' : ''}`}
          role="tab"
          aria-selected={tab === 'report'}
          onClick={() => setTab('report')}
        >
          보고서
        </button>
      </nav>

      {error && <div className="error-box">서버에 연결할 수 없어요 — {error}</div>}

      {tab === 'report' && <ReportView />}

      {tab === 'forecast' && carryover && (
        <section className="banner carryover" role="status">
          <p>
            지난번 미룬 <strong>{(carryover.zone_names ?? []).join('·') || '구역'}</strong>부터
            시작할까요?
          </p>
          <div className="banner-actions">
            <button className="btn primary" onClick={acceptCarryover}>
              예약 구역부터
            </button>
            <button className="btn ghost" onClick={dismissCarryover}>
              아니요
            </button>
          </div>
        </section>
      )}

      {tab === 'forecast' && (
        <>
          <ForecastCard forecast={forecast} optimistic={optimistic} />
          <HeatmapView heatmap={heatmap} plan={plan} showRoute={showRoute} />
          <MessageBanner forecast={forecast} plan={plan} onSwitchMode={changeMode} />
          {forecast?.state === 'shortage_a' && (
            <PlanOverlay
              plan={plan}
              allZones={heatmap?.zones}
              showRoute={showRoute}
              deferred={deferred}
              onCleanSubset={() => {
                setShowRoute(true)
                flash('완결 가능한 구역의 청소 경로를 표시했어요')
              }}
              onDefer={deferLeftover}
            />
          )}
          <ModeSelector mode={mode} forecast={forecast} onChange={changeMode} />
        </>
      )}

      <footer className="footnote">
        예보·히트맵·구역 완결 확률은 동일한 결합 부트스트랩 분포에서 산출됩니다 (engine:{' '}
        {forecast?.engine ?? '…'})
      </footer>
      {toast && <div className="toast app-toast">{toast}</div>}
    </div>
  )
}
