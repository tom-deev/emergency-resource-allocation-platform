const RAW_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export const API_BASE_URL = RAW_BASE_URL.replace(/\/+$/, "");

const TOKEN_STORAGE_KEY = "erap_auth_token";
const USER_STORAGE_KEY = "erap_auth_user";

export function getStoredToken() {
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function getStoredUser() {
  try {
    const raw = localStorage.getItem(USER_STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function saveSession(token, user) {
  localStorage.setItem(TOKEN_STORAGE_KEY, token);
  localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
}

export function clearSession() {
  localStorage.removeItem(TOKEN_STORAGE_KEY);
  localStorage.removeItem(USER_STORAGE_KEY);
}

export class ApiError extends Error {
  constructor(message, status, data = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

async function request(path, { method = "GET", body = null, auth = true } = {}) {
  const headers = {
    "Content-Type": "application/json",
  };

  if (auth) {
    const token = getStoredToken();
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
  }

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      body: body !== null ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(
      `Cannot reach backend API at ${API_BASE_URL}. Ensure the backend server is running.`,
      0
    );
  }

  const text = await response.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { raw: text };
    }
  }

  if (!response.ok) {
    const message =
      (data && (data.error || data.message)) ||
      `Request failed with HTTP ${response.status}`;
    throw new ApiError(message, response.status, data);
  }

  return data;
}

export const api = {
  health: () => request("/", { auth: false }),
  getDashboardSummary: () => request("/dashboard/summary"),

  // Auth
  register: (payload) =>
    request("/auth/register", { method: "POST", body: payload, auth: false }),
  login: (payload) =>
    request("/auth/login", { method: "POST", body: payload, auth: false }),
  verifyOtp: (payload) =>
    request("/auth/verify-otp", { method: "POST", body: payload, auth: false }),
  getMe: () => request("/auth/me"),

  // Incidents
  getIncidents: () => request("/incidents"),
  getArchivedIncidents: () => request("/incidents/archived"),
  getIncidentQueue: (params = {}) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value && value !== "ALL") qs.set(key, value);
    });
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return request(`/incidents/queue${suffix}`);
  },
  getIncident: (id) => request(`/incidents/${encodeURIComponent(id)}`),
  createIncident: (payload) =>
    request("/incidents", { method: "POST", body: payload }),
  cancelIncident: (id) =>
    request(`/incidents/${encodeURIComponent(id)}/status`, {
      method: "PUT",
      body: { status: "CANCELLED" },
    }),

  // Incident verification & manual coordination workflow
  startReview: (id) =>
    request(`/incidents/${encodeURIComponent(id)}/review`, { method: "POST" }),
  verifyIncident: (id, payload) =>
    request(`/incidents/${encodeURIComponent(id)}/verify`, {
      method: "POST",
      body: payload,
    }),
  getCandidates: (id, facilities = [], beds = null) => {
    const qs = new URLSearchParams();
    if (facilities.length > 0) qs.set("facilities", facilities.join(","));
    if (beds !== null && beds !== undefined && beds !== "") {
      qs.set("beds", String(beds));
    }
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return request(`/incidents/${encodeURIComponent(id)}/candidates${suffix}`);
  },
  assignAmbulance: (id, ambulanceId) =>
    request(`/incidents/${encodeURIComponent(id)}/assign-ambulance`, {
      method: "POST",
      body: { ambulanceId },
    }),
  requestHospital: (id, hospitalId, bedsRequested = null) =>
    request(`/incidents/${encodeURIComponent(id)}/request-hospital`, {
      method: "POST",
      body:
        bedsRequested !== null && bedsRequested !== undefined
          ? { hospitalId, bedsRequested: Number(bedsRequested) }
          : { hospitalId },
    }),
  cancelHospitalReservation: (id, reason = null) =>
    request(`/incidents/${encodeURIComponent(id)}/cancel-reservation`, {
      method: "POST",
      body: reason ? { reason } : {},
    }),
  recordHospitalDecision: (id, payload) =>
    request(`/incidents/${encodeURIComponent(id)}/hospital-decision`, {
      method: "POST",
      body: payload,
    }),
  markTransported: (id) =>
    request(`/incidents/${encodeURIComponent(id)}/transport`, {
      method: "POST",
    }),
  completeIncident: (id) =>
    request(`/incidents/${encodeURIComponent(id)}/complete`, {
      method: "POST",
    }),
  archiveIncident: (id) =>
    request(`/incidents/${encodeURIComponent(id)}/archive`, {
      method: "POST",
    }),

  // Ambulances
  getAmbulances: () => request("/ambulances"),
  createAmbulance: (payload) =>
    request("/ambulances", { method: "POST", body: payload }),
  updateAmbulance: (id, payload) =>
    request(`/ambulances/${encodeURIComponent(id)}`, {
      method: "PUT",
      body: payload,
    }),

  // Hospitals
  getHospitals: () => request("/hospitals"),
  createHospital: (payload) =>
    request("/hospitals", { method: "POST", body: payload }),
  updateHospital: (id, payload) =>
    request(`/hospitals/${encodeURIComponent(id)}`, {
      method: "PUT",
      body: payload,
    }),
};
