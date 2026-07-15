// REST client for the §6 endpoints. Same-origin by default; VITE_API_BASE overrides.
const BASE = import.meta.env.VITE_API_BASE ?? ''

async function request(path, params) {
  const qs = params ? `?${new URLSearchParams(params)}` : ''
  const res = await fetch(`${BASE}${path}${qs}`)
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(body?.error?.message ?? `HTTP ${res.status}`)
  }
  return res.json()
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

export function getSessions() {
  return request('/api/sessions')
}
