/**
 * Timing instrumentation for latency analysis.
 *
 * Usage:
 *   import { logTiming, generateRequestId, timingState } from '@/utils/timing'
 *
 *   // At request start
 *   const requestId = generateRequestId()
 *   timingState.setRequestId(requestId)
 *   logTiming('T0', 'request_sent')
 *
 *   // During processing
 *   logTiming('T10', 'response_received')
 *   logTiming('T11', 'audio_playback_start')
 *
 * Events are logged to console AND posted to /api/timing/log for aggregation.
 */

const TIMING_API_BASE = '/api/timing'

// Current request context
class TimingState {
  private requestId: string = 'unknown'
  private t0Timestamp: number = 0
  private s0Timestamp: number = 0

  setRequestId(id: string) {
    this.requestId = id
  }

  getRequestId(): string {
    return this.requestId
  }

  setT0(ts: number) {
    this.t0Timestamp = ts
  }

  getT0(): number {
    return this.t0Timestamp
  }

  setS0(ts: number) {
    this.s0Timestamp = ts
  }

  getS0(): number {
    return this.s0Timestamp
  }

  reset() {
    this.requestId = 'unknown'
    this.t0Timestamp = 0
    this.s0Timestamp = 0
  }
}

export const timingState = new TimingState()

/**
 * Generate a short unique request ID for timing correlation.
 */
export function generateRequestId(): string {
  return crypto.randomUUID().slice(0, 8)
}

/**
 * Post timing event to backend (fire-and-forget).
 */
function postTimingEvent(
  requestId: string,
  point: string,
  ts: number,
  label: string,
  extra?: Record<string, string | number | boolean>
): void {
  // Fire-and-forget POST - don't await, don't block
  fetch(`${TIMING_API_BASE}/log`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      request_id: requestId,
      point,
      ts,
      label,
      extra: extra || null,
    }),
  }).catch(() => {
    // Silently ignore failures - timing shouldn't break the app
  })
}

/**
 * Log a timing point with consistent format.
 *
 * @param point - Timing point identifier (T0, T10, T11, S0, S1, S5)
 * @param label - Human-readable label
 * @param extra - Additional key-value pairs
 * @returns The timestamp that was logged
 */
export function logTiming(
  point: string,
  label: string,
  extra: Record<string, string | number | boolean> = {}
): number {
  const ts = Date.now() / 1000 // Match backend format (Unix timestamp)
  const requestId = timingState.getRequestId()

  // Console log for local debugging
  const extraStr = Object.entries(extra)
    .map(([k, v]) => `${k}=${v}`)
    .join(' ')

  console.log(
    `[TIMING] request_id=${requestId} point=${point} ts=${ts.toFixed(3)} label="${label}"` +
      (extraStr ? ` ${extraStr}` : '')
  )

  // Post to backend for aggregation
  postTimingEvent(requestId, point, ts, label, Object.keys(extra).length > 0 ? extra : undefined)

  return ts
}

/**
 * Log a timing point with delta from a start timestamp.
 */
export function logTimingDelta(
  point: string,
  label: string,
  startTs: number,
  extra: Record<string, string | number | boolean> = {}
): number {
  const ts = Date.now() / 1000
  const deltaMs = (ts - startTs) * 1000

  return logTiming(point, label, { ...extra, delta_ms: deltaMs.toFixed(1) })
}

/**
 * Calculate and log total latency from T0.
 */
export function logTotalLatency(point: string, label: string): number {
  const t0 = timingState.getT0()
  if (t0 === 0) {
    return logTiming(point, label)
  }
  return logTimingDelta(point, label, t0, { total: true })
}
