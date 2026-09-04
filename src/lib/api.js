/**
 * API client for the Personal Knowledge OS backend.
 *
 * Talks to the FastAPI app started with `uvicorn app.main:app --reload`.
 * Every function here maps 1:1 to a real backend route — see
 * app/api/router.py / app/api/routes/*.py in the backend. Nothing here
 * is invented; if a feature isn't listed below, the backend doesn't
 * expose it yet.
 *
 * Base URL comes from VITE_API_URL (see .env), defaulting to the
 * backend's default local address.
 */

const BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

/**
 * Thin wrapper around fetch that:
 *  - prefixes BASE_URL
 *  - JSON-encodes plain object bodies (leaves FormData alone)
 *  - throws an Error with a readable message on non-2xx responses or
 *    network failures (e.g. backend not running), so callers can just
 *    try/catch and show err.message.
 */
async function request(path, options = {}) {
  const isFormData = options.body instanceof FormData;

  const init = {
    ...options,
    headers: isFormData
      ? options.headers
      : { "Content-Type": "application/json", ...(options.headers || {}) },
  };

  let response;
  try {
    response = await fetch(`${BASE_URL}${path}`, init);
  } catch (err) {
    throw new Error(
      `Could not reach the backend at ${BASE_URL}. Is it running (uvicorn app.main:app --reload)?`
    );
  }

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const data = await response.json();
      if (data && data.detail) detail = data.detail;
    } catch {
      // response wasn't JSON — fall back to statusText
    }
    throw new Error(detail || `Request failed with status ${response.status}`);
  }

  if (response.status === 204) return null;

  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) return null;
  return response.json();
}

/** GET /api/health -> {status: "ok"} */
export function getHealth() {
  return request("/api/health");
}

/** GET /api/documents -> DocumentOut[] */
export function listDocuments() {
  return request("/api/documents");
}

/** GET /api/documents/{id} -> DocumentOut */
export function getDocument(id) {
  return request(`/api/documents/${id}`);
}

/** POST /api/documents (multipart) -> DocumentOut. Accepts a File/Blob. */
export function uploadDocument(file) {
  const formData = new FormData();
  formData.append("file", file);
  return request("/api/documents", { method: "POST", body: formData });
}

/** DELETE /api/documents/{id} -> 204 */
export function deleteDocument(id) {
  return request(`/api/documents/${id}`, { method: "DELETE" });
}

/** POST /api/search {query, top_k?} -> {query, results: [...]} */
export function search(query, topK = 5) {
  return request("/api/search", {
    method: "POST",
    body: JSON.stringify({ query, top_k: topK }),
  });
}

/** POST /api/chat {message, conversation_id?} -> {answer, sources, conversation_id} */
export function sendChatMessage(message, conversationId) {
  return request("/api/chat", {
    method: "POST",
    body: JSON.stringify({ message, conversation_id: conversationId ?? null }),
  });
}

/** POST /api/study/quiz {query, count?} -> {topic, questions, sources, count} */
export function generateQuiz(query, count) {
  return request("/api/study/quiz", {
    method: "POST",
    body: JSON.stringify({ query, count: count ?? null }),
  });
}

/** POST /api/study/flashcards {query, count?} -> {topic, cards, sources, count} */
export function generateFlashcards(query, count) {
  return request("/api/study/flashcards", {
    method: "POST",
    body: JSON.stringify({ query, count: count ?? null }),
  });
}

/** GET /api/settings -> {is_configured, source, provider?, model?, api_key_hint?} */
export function getSettings() {
  return request("/api/settings");
}

/** PUT /api/settings {provider, api_key, model?} -> SettingsResponse */
export function updateSettings(provider, apiKey, model) {
  return request("/api/settings", {
    method: "PUT",
    body: JSON.stringify({ provider, api_key: apiKey, model: model || null }),
  });
}

/** DELETE /api/settings -> {ok: true} */
export function deleteSettings() {
  return request("/api/settings", { method: "DELETE" });
}
