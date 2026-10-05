export class ApiError extends Error {
  status: number
  detail: string

  constructor(status: number, detail: string) {
    super(`${status}: ${detail}`)
    this.status = status
    this.detail = detail
  }
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
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch {
      // not JSON: keep the status text
    }
    throw new ApiError(res.status, detail)
  }
  return { body: (await res.json()) as T, headers: res.headers }
}

/** URL of an API path with query parameters (undefined values left out). */
export function apiUrl(path: string, params: Params = {}): string {
  const qs = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) if (v !== undefined) qs.set(k, String(v))
  return `/api${path}${qs.size ? `?${qs}` : ''}`
}
