// Typed fetch wrapper for src/web_api — types mirror src/web_api/schemas.py (data-model.md).

export interface GenerateRequest {
  location: string
  calendar_length_days: number
  max_cost?: number | null
  event_types?: string[]
  genres?: string[]
  start_after?: string | null
  start_before?: string | null
  model?: string | null
}

export interface EventSummary {
  name: string
  date: string
  start_time: string
  venue: string
  cost: string
  event_type: string
  genre: string | null
  source_url: string
}

export interface CalendarResponse {
  output_path: string
  generated_at: string
  events: EventSummary[]
  event_count: number
}

export interface SourceResponse {
  name: string
  url: string
  added_at: string
}

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

// The Vite dev server's origin differs from the backend's, so requests go
// straight to the backend (allowed via CORS — src/web_api/app.py). In
// production the backend serves the built frontend itself, so requests are
// same-origin and a relative base works (research.md #6).
const API_BASE = import.meta.env.DEV ? 'http://127.0.0.1:8000' : ''

interface FastApiValidationError {
  msg: string
}

function extractErrorMessage(body: unknown, fallback: string): string {
  if (body && typeof body === 'object' && 'detail' in body) {
    const detail = (body as { detail: unknown }).detail
    if (typeof detail === 'string') {
      return detail
    }
    if (Array.isArray(detail)) {
      return detail
        .map((entry) => (entry as FastApiValidationError)?.msg)
        .filter((msg): msg is string => typeof msg === 'string')
        .join('; ')
    }
  }
  return fallback
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })

  if (!response.ok) {
    const body: unknown = await response.json().catch(() => undefined)
    throw new ApiError(
      response.status,
      extractErrorMessage(body, `Request failed with status ${response.status}`),
    )
  }

  return (await response.json()) as T
}

export function generateCalendar(req: GenerateRequest): Promise<CalendarResponse> {
  return request<CalendarResponse>('/api/calendar', {
    method: 'POST',
    body: JSON.stringify(req),
  })
}

export function listSources(): Promise<SourceResponse[]> {
  return request<SourceResponse[]>('/api/sources')
}

export function addSource(name: string, url: string): Promise<SourceResponse> {
  return request<SourceResponse>('/api/sources', {
    method: 'POST',
    body: JSON.stringify({ name, url }),
  })
}

export function removeSource(url: string): Promise<SourceResponse> {
  return request<SourceResponse>(`/api/sources?url=${encodeURIComponent(url)}`, {
    method: 'DELETE',
  })
}
