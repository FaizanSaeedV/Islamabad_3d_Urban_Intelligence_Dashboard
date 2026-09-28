/**
 * Backend API client. Thin fetch wrapper with query building, timeouts,
 * and typed errors so UI modules can degrade gracefully.
 */
import { CONFIG } from "../config.js";

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/**
 * GET a backend endpoint. `params` object becomes the query string
 * (null/undefined values are skipped).
 */
export async function apiGet(path, params = {}, timeoutMs = 60000) {
  const url = new URL(path, CONFIG.API_BASE_URL);
  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined) url.searchParams.set(key, value);
  }
  let response;
  try {
    response = await fetch(url, {
      headers: { Accept: "application/json" },
      signal: AbortSignal.timeout(timeoutMs),
    });
  } catch (err) {
    throw new ApiError(`Backend unreachable (${err.name})`, 0);
  }
  if (!response.ok) {
    let detail = response.statusText;
    try {
      detail = (await response.json()).detail ?? detail;
    } catch { /* non-JSON error body */ }
    throw new ApiError(`${detail}`, response.status);
  }
  return response.json();
}
