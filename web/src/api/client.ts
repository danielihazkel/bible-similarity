export class ApiError extends Error {
  status: number
  detail: string
  /** `stage_missing`: the analysis was not computed in this build (`stage` names it) */
  code?: string
  stage?: string

  constructor(status: number, detail: string, code?: string, stage?: string) {
    super(`${status}: ${detail}`)
    this.status = status
    this.detail = detail
    this.code = code
    this.stage = stage
  }
}

/** The stage behind this page did not run in this build (503 `stage_missing`). */
export function isStageMissing(error: unknown): error is ApiError {
  return error instanceof ApiError && error.code === 'stage_missing'
}

export type Params = Record<string, string | number | undefined>

export async function getJson<T>(path: string, params: Params = {}, signal?: AbortSignal): Promise<T> {
  return (await fetchJson<T>(path, params, signal)).body
}

/** A list endpoint that reports the size of the whole list in `X-Total-Count`. */
export async function getJsonWithTotal<T>(
  path: string,
  params: Params = {},
  signal?: AbortSignal,
): Promise<{ items: T[]; total: number }> {
  const { body, headers } = await fetchJson<T[]>(path, params, signal)
  const total = Number(headers.get('X-Total-Count'))
  return { items: body, total: Number.isFinite(total) && headers.has('X-Total-Count') ? total : body.length }
}

async function fetchJson<T>(path: string, params: Params, signal?: AbortSignal): Promise<{ body: T; headers: Headers }> {
  const qs = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) if (v !== undefined) qs.set(k, String(v))
  const url = `/api${path}${qs.size ? `?${qs}` : ''}`
  const res = await fetch(url, { signal })
  if (!res.ok) throw await apiError(res)
  return { body: (await res.json()) as T, headers: res.headers }
}

async function apiError(res: Response): Promise<ApiError> {
  let detail = res.statusText
  let code: string | undefined
  let stage: string | undefined
  try {
    const body = await res.json()
    const d = body.detail
    if (typeof d === 'string') detail = d
    else if (d && typeof d === 'object' && typeof d.message === 'string') {
      detail = d.message
      code = typeof d.code === 'string' ? d.code : undefined
      stage = typeof d.stage === 'string' ? d.stage : undefined
    } else detail = JSON.stringify(d)
  } catch {
    // not JSON: keep the status text
  }
  return new ApiError(res.status, detail, code, stage)
}

/** A write (the labels and the notebook are the API's only writable data): POST or PUT with a JSON body, or DELETE. */
export async function sendJson<T>(method: 'POST' | 'PUT' | 'DELETE', path: string, body?: unknown): Promise<T | null> {
  const res = await fetch(`/api${path}`, {
    method,
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!res.ok) throw await apiError(res)
  return res.status === 204 ? null : ((await res.json()) as T)
}

/** URL of an API path with query parameters (undefined values left out). */
export function apiUrl(path: string, params: Params = {}): string {
  const qs = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) if (v !== undefined) qs.set(k, String(v))
  return `/api${path}${qs.size ? `?${qs}` : ''}`
}
