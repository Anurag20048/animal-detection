const API_BASE_URL = (window.ANIMAL_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
const STORAGE_KEY = "animal-detection-token";

function getAuthHeader() {
  const token = localStorage.getItem(STORAGE_KEY);
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function apiRequest(endpoint, options = {}) {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: { ...getAuthHeader(), ...(options.headers || {}) },
  });
  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`${response.status}: ${text || response.statusText}`);
  }
  return response.status === 204 ? null : response.json();
}

async function apiGet(endpoint) { return apiRequest(endpoint); }
async function apiPost(endpoint, body = {}) {
  return apiRequest(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}
async function apiUpload(endpoint, file, fieldName = "file") {
  const form = new FormData();
  form.append(fieldName, file);
  return apiRequest(endpoint, { method: "POST", body: form });
}
async function apiHealth() { return apiGet("/health"); }
