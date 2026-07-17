// REST client for the §6 endpoints. Same-origin by default; VITE_API_BASE overrides.
const BASE = import.meta.env.VITE_API_BASE ?? ''

async function unwrap(res) {
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(body?.error?.message ?? `HTTP ${res.status}`)
  }
  return res.json()
}

async function request(path, params) {
  const qs = params ? `?${new URLSearchParams(params)}` : ''
  return unwrap(await fetch(`${BASE}${path}${qs}`))
}

async function post(path, body) {
  return unwrap(
    await fetch(`${BASE}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  )
}

/**
 * @param {{battery: number, mode: string, zones?: number[], prevState?: string|null}} args
 * @returns {Promise<object>} §6 /api/predict payload (t_est/t_lo/t_hi, t_req*, p_complete,
 *   state, recommended_mode, charge_min, per_mode, basis)
 */
export function getPredict({ battery, mode, zones, prevState }) {
  const params = { battery: String(battery), mode }
  if (zones?.length) params.zones = zones.join(',')
  if (prevState) params.prev_state = prevState
  return request('/api/predict', params)
}

/**
 * §5.2 trajectory heatmap: per-cell completion probability + per-zone rollup.
 * @param {{battery: number, mode: string}} args
 * @returns {Promise<object>} {grid, dock, cell_size_m, b_res, cells:[{x,y,zone,p}], zones:[...]}
 */
export function getHeatmap({ battery, mode }) {
  return request('/api/heatmap', { battery: String(battery), mode })
}

/**
 * §5.1 subset planner (부족A): the max-value zone set that still completes at ≥ 0.90.
 * @param {{battery: number, zones?: number[]}} args
 * @returns {Promise<object>} {feasible, plan|null, b_res}
 */
export function getPlan({ battery, zones }) {
  return post('/api/plan', { battery, zones: zones ?? null })
}

export function getSessions() {
  return request('/api/sessions')
}

/**
 * §9.5 session report: structured facts + §3.6 factor decomposition + §9.6 template narration.
 * @param {string} sessionId
 * @returns {Promise<object>} {facts, factors:[{feature,label,direction,contribution_min}], narration}
 */
export function getReport(sessionId) {
  return request(`/api/report/${encodeURIComponent(sessionId)}`)
}
