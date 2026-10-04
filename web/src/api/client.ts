export class ApiError extends Error {
  status: number
  detail: string

  constructor(status: number, detail: string) {
    super(`${status}: ${detail}`)
    this.status = status
    this.detail = detail
  }
}

type Params = Record<string, string | number | undefined>

export async function getJson<T>(path: string, params: Params = {}, signal?: AbortSignal): Promise<T> {
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
  return res.json() as Promise<T>
}
