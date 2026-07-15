const MODE_KO = { eco: '에코', standard: '표준', turbo: '터보' }

// 부족A plan card (§4.2, §5.1): the max-value zone subset that still completes, with the route
// trigger ([○○만 청소] → numbered overlay on the heatmap) and the carryover affordance
// ([다음에 예약] → next_plan). No number here is invented — all come from /api/plan (§5.1).
export default function PlanOverlay({
  plan,
  allZones,
  showRoute,
  onCleanSubset,
  onDefer,
  deferred,
}) {
  if (!plan) return null

  const chosen = plan.zones.map((z) => z.name)
  const chosenIds = new Set(plan.zone_ids)
  const leftover = (allZones ?? []).filter((z) => !chosenIds.has(z.zone_id))
  const pct = Math.round(plan.p_complete * 100)

  return (
    <section className="card plan-overlay">
      <div className="plan-head">
        지금 배터리로 완결 가능한 구역 · <strong>{chosen.join('·')}</strong>
      </div>
      <p className="plan-summary">
        {MODE_KO[plan.mode]} 모드 · 예상 {Math.round(plan.t_req_min)}분 · 완료 확률{' '}
        <strong>{pct}%</strong> · 청소 후 잔여 {Math.round(plan.remaining_pct)}%
      </p>

      <div className="plan-actions">
        <button className={`btn ${showRoute ? 'ghost' : 'primary'}`} onClick={onCleanSubset}>
          {showRoute ? '경로 표시됨' : `${chosen.join('·')}만 청소`}
        </button>
      </div>

      {leftover.length > 0 && (
        <div className="plan-leftover">
          <span className="leftover-label">미선택 구역</span>
          {leftover.map((z) => (
            <span key={z.zone_id} className="zone-chip">
              {z.name}
            </span>
          ))}
          <button
            className="btn ghost small"
            disabled={deferred}
            onClick={() =>
              onDefer(
                leftover.map((z) => z.zone_id),
                leftover.map((z) => z.name),
              )
            }
          >
            {deferred ? '예약됨 ✓' : '다음에 예약'}
          </button>
        </div>
      )}
    </section>
  )
}
