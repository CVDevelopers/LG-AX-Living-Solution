// Carryover-plan storage (§4.2 이월 UX). Per §12.1 the store is a client adapter: on profile W
// (public Vercel URL) next_plan is per-visitor state, so keeping it in localStorage is the
// correct design — a shared server row would mix visitors' plans. The same adapter works on
// profile L. The server also exposes /api/next-plan for single-user local use; this default keeps
// the deployed demo self-contained and write-free against the read-only seed DB.

const KEY = 'bwf.next_plan'

function read() {
  try {
    return JSON.parse(localStorage.getItem(KEY) || 'null')
  } catch {
    return null
  }
}

export const nextPlanStore = {
  /** The pending (un-consumed) carryover plan, or null. */
  getPending() {
    const p = read()
    return p && !p.consumed ? p : null
  },

  /** Defer the un-selected zones for next visit. */
  defer({ zoneIds, zoneNames, mode, reason }) {
    const plan = {
      zone_ids: zoneIds,
      zone_names: zoneNames ?? [],
      mode,
      reason: reason ?? null,
      created_at: new Date().toISOString(),
      consumed: false,
    }
    localStorage.setItem(KEY, JSON.stringify(plan))
    return plan
  },

  /** Mark the pending plan consumed (offered and acted on / dismissed). */
  consume() {
    const p = read()
    if (p) localStorage.setItem(KEY, JSON.stringify({ ...p, consumed: true }))
  },

  clear() {
    localStorage.removeItem(KEY)
  },
}
