"use client";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000/api";

// Auth now lives in httpOnly cookies the browser sends automatically — nothing
// for JS to read or store, which is the point (an XSS bug can't steal the session).
let loggedInCache = null; // null = unknown, true/false = last check's answer

export async function isLoggedIn() {
  if (loggedInCache !== null) return loggedInCache;
  try {
    const res = await fetch(`${API_BASE}/auth/me/`, { credentials: "include" });
    loggedInCache = res.ok;
  } catch {
    loggedInCache = false;
  }
  return loggedInCache;
}
function setLoggedIn(v) { loggedInCache = v; }

async function refreshAccessToken() {
  const res = await fetch(`${API_BASE}/auth/token/refresh/`, { method: "POST", credentials: "include" });
  if (!res.ok) throw new Error("refresh-failed");
}

/** Core request helper. Pass a relative path like "/content/posts/".
 *  Pass { workspace: id } to scope the request to one avatar — added as a query
 *  param for GET/DELETE, merged into the JSON body otherwise. */
export async function api(path, { method = "GET", body, isForm = false, retry = true, workspace } = {}) {
  const headers = {};
  if (!isForm) headers["Content-Type"] = "application/json";

  let finalPath = path;
  let finalBody = body;
  if (workspace) {
    if (method === "GET" || method === "DELETE") {
      finalPath += (path.includes("?") ? "&" : "?") + `workspace=${workspace}`;
    } else if (!isForm) {
      finalBody = { ...(body || {}), workspace };
    }
  }

  const res = await fetch(`${API_BASE}${finalPath}`, {
    method, headers, credentials: "include",
    body: finalBody ? (isForm ? finalBody : JSON.stringify(finalBody)) : undefined,
  });

  if (res.status === 401 && retry) {
    try {
      await refreshAccessToken();
      return api(path, { method, body, isForm, retry: false, workspace });
    } catch {
      setLoggedIn(false);
      if (typeof window !== "undefined") window.location.href = "/login";
      throw new Error("Session expired");
    }
  }

  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    let code;
    try { const data = await res.json(); detail = data.detail || JSON.stringify(data); code = data.code; } catch {}
    const err = new Error(detail);
    err.status = res.status; err.code = code;
    throw err;
  }
  if (res.status === 204) return null;
  return res.json();
}

export async function login(email, password) {
  const res = await fetch(`${API_BASE}/auth/login/`, {
    method: "POST", credentials: "include", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) { let d = "Invalid email or password"; try { d = (await res.json()).detail || d; } catch {} throw new Error(d); }
  setLoggedIn(true);
  return res.json();
}

export async function register(email, password, fullName, turnstileToken) {
  const res = await fetch(`${API_BASE}/auth/register/`, {
    method: "POST", credentials: "include", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, full_name: fullName, turnstile_token: turnstileToken }),
  });
  if (!res.ok) {
    let detail = "Could not create account";
    try { const data = await res.json(); detail = Object.values(data)[0]?.[0] || Object.values(data)[0] || detail; } catch {}
    throw new Error(detail);
  }
  setLoggedIn(true);
  return res.json();
}

export async function logout() {
  try { await fetch(`${API_BASE}/auth/logout/`, { method: "POST", credentials: "include" }); } catch {}
  setLoggedIn(false);
}
