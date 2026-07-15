import { HATCH_BELOW, RAMP, pToColor } from '../heatmap/ramp.js'

// §5.2 trajectory heatmap + §7.3 visual rules: single-hue teal lightness ramp (light = low
// completion probability → dark = high), zone % text always shown, and p < 0.5 cells hatched —
// three independent codes so the ordering survives colour-vision deficiency and greyscale.
// The SVG scales to its container (viewBox in grid units); logic is unaffected by the 2× upsample.

const WALL = -1
const OBSTACLE = 2

function zoneCentroids(cells) {
  const acc = {}
  for (const c of cells) {
    const a = (acc[c.zone] ||= { sx: 0, sy: 0, n: 0 })
    a.sx += c.x + 0.5
    a.sy += c.y + 0.5
    a.n += 1
  }
  return acc
}

function Legend() {
  return (
    <div className="heatmap-legend" aria-hidden="true">
      <span className="legend-label">완료 확률</span>
      {RAMP.map((s) => (
        <span key={s.color} className="legend-swatch" style={{ background: s.color }} />
      ))}
      <span className="legend-ends">낮음 → 높음</span>
    </div>
  )
}

export default function HeatmapView({ heatmap, plan, showRoute }) {
  if (!heatmap) return <section className="card heatmap-card">지도 불러오는 중…</section>

  const { grid, cells, zones, dock, b_res: bRes } = heatmap
  const h = grid.length
  const w = grid[0].length
  const pByCell = new Map(cells.map((c) => [`${c.x},${c.y}`, c.p]))
  const zoneByCell = new Map(cells.map((c) => [`${c.x},${c.y}`, c.zone]))
  const centroids = zoneCentroids(cells)

  const planZones = showRoute && plan ? new Set(plan.zone_ids) : null
  const orderById = new Map((plan?.zones ?? []).map((z) => [z.zone_id, z.order]))

  return (
    <section className="card heatmap-card">
      <div className="heatmap-title">
        <span>청소 예보 지도</span>
        <span className="heatmap-sub">예비 {bRes}% 확보 · 셀당 완료 확률</span>
      </div>
      <svg
        className="heatmap-svg"
        viewBox={`0 0 ${w} ${h}`}
        role="img"
        aria-label="구역별 청소 완료 확률 지도"
      >
        <defs>
          <pattern
            id="hatch"
            width="0.5"
            height="0.5"
            patternUnits="userSpaceOnUse"
            patternTransform="rotate(45)"
          >
            <rect width="0.5" height="0.5" fill="transparent" />
            <line x1="0" y1="0" x2="0" y2="0.5" stroke="rgba(3,58,51,0.55)" strokeWidth="0.12" />
          </pattern>
        </defs>

        {grid.flatMap((row, y) =>
          row.map((code, x) => {
            if (code === WALL) return null
            const key = `${x},${y}`
            const p = pByCell.get(key)
            const dimmed = planZones && !planZones.has(zoneByCell.get(key))
            if (p === undefined) {
              // Non-cleanable interior cell (dock tile etc.) — neutral floor.
              return <rect key={key} x={x} y={y} width="1" height="1" fill="#eef2f4" />
            }
            return (
              <g key={key} opacity={dimmed ? 0.25 : 1}>
                <rect x={x} y={y} width="1" height="1" fill={pToColor(p)} />
                {p < HATCH_BELOW && <rect x={x} y={y} width="1" height="1" fill="url(#hatch)" />}
              </g>
            )
          }),
        )}

        {/* Obstacles: a small neutral marker (never colour-only) */}
        {grid.flatMap((row, y) =>
          row.map((code, x) =>
            code === OBSTACLE ? (
              <circle key={`o${x},${y}`} cx={x + 0.5} cy={y + 0.5} r="0.16" fill="#5b6470" />
            ) : null,
          ),
        )}

        {/* Dock */}
        <g>
          <rect
            x={dock[0] + 0.1}
            y={dock[1] + 0.1}
            width="0.8"
            height="0.8"
            rx="0.15"
            fill="#1c1f23"
          />
          <text
            x={dock[0] + 0.5}
            y={dock[1] + 0.72}
            textAnchor="middle"
            fontSize="0.55"
            fill="#fff"
          >
            ⌂
          </text>
        </g>

        {/* Zone % labels (always shown) + optional plan-route order badge */}
        {zones.map((z) => {
          const c = centroids[z.zone_id]
          if (!c) return null
          const cx = c.sx / c.n
          const cy = c.sy / c.n
          const order = orderById.get(z.zone_id)
          return (
            <g key={z.zone_id}>
              <text className="zone-name" x={cx} y={cy - 0.35} textAnchor="middle" fontSize="0.85">
                {z.name}
              </text>
              <text className="zone-pct" x={cx} y={cy + 0.75} textAnchor="middle" fontSize="0.95">
                {Math.round(z.p_complete * 100)}%
              </text>
              {showRoute && order && (
                <>
                  <circle cx={cx} cy={cy - 1.5} r="0.7" fill="#0d9488" />
                  <text
                    x={cx}
                    y={cy - 1.22}
                    textAnchor="middle"
                    fontSize="0.9"
                    fill="#fff"
                    fontWeight="700"
                  >
                    {order}
                  </text>
                </>
              )}
            </g>
          )
        })}
      </svg>
      <Legend />
    </section>
  )
}
