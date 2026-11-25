import { useState } from "react";
import { api } from "../api/client";

const INITIAL_FORM = {
  registrationNumber: "",
  latitude: "18.5204",
  longitude: "73.8567",
  status: "AVAILABLE",
  equipment: "OXYGEN, FIRST_AID",
};

export default function AmbulancesView({ user, ambulances, onRefresh }) {
  const isOperator = user.role === "RESOURCE_OPERATOR";

  const [form, setForm] = useState(INITIAL_FORM);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function handleCreate(e) {
    e.preventDefault();
    setError("");
    setSuccess("");
    setBusy(true);

    try {
      const equipList = form.equipment
        .split(",")
        .map((s) => s.trim().toUpperCase())
        .filter(Boolean);

      const created = await api.createAmbulance({
        registrationNumber: form.registrationNumber.trim().toUpperCase(),
        latitude: Number(form.latitude),
        longitude: Number(form.longitude),
        status: form.status,
        equipment: equipList,
      });

      setForm(INITIAL_FORM);
      setSuccess(`Ambulance ${created.registrationNumber} registered.`);
      await onRefresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleStatusChange(ambulanceId, status) {
    setError("");
    setSuccess("");
    setBusy(true);
    try {
      await api.updateAmbulance(ambulanceId, { status });
      setSuccess(`Ambulance ${ambulanceId} updated to ${status}.`);
      await onRefresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      {isOperator ? (
        <div className="card">
          <div className="card-header">
            <h3>Register Ambulance</h3>
          </div>
          <form onSubmit={handleCreate} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
            <div className="form-grid">
              <div className="field">
                <label>Vehicle Registration Number</label>
                <input
                  type="text"
                  value={form.registrationNumber}
                  onChange={(e) =>
                    setForm({ ...form, registrationNumber: e.target.value })
                  }
                  placeholder="MH12EM1004"
                  required
                />
              </div>
              <div className="field">
                <label>Latitude</label>
                <input
                  type="number"
                  step="any"
                  value={form.latitude}
                  onChange={(e) => setForm({ ...form, latitude: e.target.value })}
                  required
                />
              </div>
              <div className="field">
                <label>Longitude</label>
                <input
                  type="number"
                  step="any"
                  value={form.longitude}
                  onChange={(e) =>
                    setForm({ ...form, longitude: e.target.value })
                  }
                  required
                />
              </div>
              <div className="field">
                <label>Status</label>
                <select
                  value={form.status}
                  onChange={(e) => setForm({ ...form, status: e.target.value })}
                >
                  <option value="AVAILABLE">AVAILABLE</option>
                  <option value="BUSY">BUSY</option>
                  <option value="OFFLINE">OFFLINE</option>
                </select>
              </div>
              <div className="field">
                <label>Equipment (comma-separated)</label>
                <input
                  type="text"
                  value={form.equipment}
                  onChange={(e) =>
                    setForm({ ...form, equipment: e.target.value })
                  }
                />
              </div>
            </div>
            <div>
              <button type="submit" className="btn btn-primary" disabled={busy}>
                {busy ? "Saving..." : "Register Ambulance"}
              </button>
            </div>
          </form>
        </div>
      ) : (
        <div className="alert alert-info">
          Viewing ambulance fleet in read-only mode. Sign in as a{" "}
          <strong>RESOURCE_OPERATOR</strong> to register or update ambulances.
        </div>
      )}

      <div className="card">
        <div className="card-header">
          <h3>Ambulance Fleet ({ambulances.length})</h3>
        </div>
        {ambulances.length === 0 ? (
          <div className="empty-state">No ambulances registered yet.</div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Vehicle</th>
                  <th>Status</th>
                  <th>Location</th>
                  <th>Equipment</th>
                  <th>Assigned Incident</th>
                  {isOperator && <th>Update Status</th>}
                </tr>
              </thead>
              <tbody>
                {ambulances.map((amb) => (
                  <tr key={amb.ambulanceId}>
                    <td>
                      <strong>{amb.registrationNumber}</strong>
                      <div style={{ fontSize: "11px", color: "#64748b" }}>
                        {amb.ambulanceId}
                      </div>
                    </td>
                    <td>
                      <span
                        className={`badge badge-${(amb.status || "").toLowerCase()}`}
                      >
                        {amb.status}
                      </span>
                    </td>
                    <td>
                      {amb.latitude}, {amb.longitude}
                    </td>
                    <td>
                      <div className="tag-list">
                        {(amb.equipment || []).map((eq) => (
                          <span key={eq} className="tag">
                            {eq}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td>{amb.assignedIncidentId || "—"}</td>
                    {isOperator && (
                      <td>
                        <select
                          value={amb.status}
                          disabled={busy}
                          onChange={(e) =>
                            handleStatusChange(amb.ambulanceId, e.target.value)
                          }
                          style={{
                            padding: "5px 8px",
                            border: "1px solid #cbd5e1",
                            borderRadius: "6px",
                            fontSize: "12px",
                          }}
                        >
                          <option value="AVAILABLE">AVAILABLE</option>
                          <option value="BUSY">BUSY</option>
                          <option value="OFFLINE">OFFLINE</option>
                        </select>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
