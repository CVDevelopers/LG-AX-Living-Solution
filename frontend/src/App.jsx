import { useCallback, useEffect, useRef, useState } from 'react'
import { getPredict } from './api/client.js'
import BatteryHeader from './components/BatteryHeader.jsx'
import ForecastCard from './components/ForecastCard.jsx'
import MessageBanner from './components/MessageBanner.jsx'
import ModeSelector from './components/ModeSelector.jsx'

const DEBOUNCE_MS = 250

export default function App() {
  const [battery, setBattery] = useState(34)
  const [mode, setMode] = useState('standard')
  const [forecast, setForecast] = useState(null)
  const [optimistic, setOptimistic] = useState(null) // per_mode cache shown ≤300 ms (§7.2)
  const [error, setError] = useState(null)
  const prevState = useRef(null)
  const timer = useRef(null)

  const refresh = useCallback((batteryPct, m) => {
    clearTimeout(timer.current)
    timer.current = setTimeout(async () => {
      try {
        const data = await getPredict({
          battery: batteryPct,
          mode: m,
          prevState: prevState.current,
        })
        prevState.current = data.state // hysteresis feedback (§4.1)
        setForecast(data)
        setOptimistic(null)
        setError(null)
      } catch (err) {
        setError(err.message)
      }
    }, DEBOUNCE_MS)
  }, [])

  useEffect(() => {
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

  return (
    <div className="app">
      <BatteryHeader battery={battery} onChange={setBattery} />
      {error && <div className="error-box">서버에 연결할 수 없어요 — {error}</div>}
      <ForecastCard forecast={forecast} optimistic={optimistic} />
      <MessageBanner forecast={forecast} onSwitchMode={changeMode} />
      <ModeSelector mode={mode} forecast={forecast} onChange={changeMode} />
      <footer className="footnote">
        예보·구간·완료 확률은 동일한 결합 부트스트랩 분포에서 산출됩니다 (engine:{' '}
        {forecast?.engine ?? '…'})
      </footer>
    </div>
  )
}
