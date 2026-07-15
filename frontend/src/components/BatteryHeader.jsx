export default function BatteryHeader({ battery, onChange }) {
  return (
    <header className="header">
      <div className="header-row">
        <h1>
          🔋⛅ 배터리 기상 예보 <span className="tag">M0</span>
        </h1>
        <span className="battery-pill">{battery}%</span>
      </div>
      <input
        type="range"
        min="0"
        max="100"
        step="1"
        value={battery}
        aria-label="현재 배터리 잔량"
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </header>
  )
}
