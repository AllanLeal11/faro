// Thin fetch wrapper. The backend base URL is a public build-time value
// (VITE_* is visible in the browser — never put secrets here).

const BASE: string =
  (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") ??
  "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

interface Options {
  method?: string;
  body?: unknown;
  token?: string | null;
}

export async function api<T>(path: string, opts: Options = {}): Promise<T> {
  const headers: Record<string, string> = {};
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";
  if (opts.token) headers["Authorization"] = `Bearer ${opts.token}`;

  let resp: Response;
  try {
    resp = await fetch(`${BASE}${path}`, {
      method: opts.method ?? "GET",
      headers,
      body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
    });
  } catch {
    throw new ApiError(0, "network");
  }

  if (resp.status === 204) return undefined as T;

  let data: unknown = null;
  const text = await resp.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = null;
    }
  }

  if (!resp.ok) {
    const detail =
      (data as { detail?: string } | null)?.detail ?? `error_${resp.status}`;
    throw new ApiError(resp.status, detail);
  }
  return data as T;
}

export const apiBase = BASE;
