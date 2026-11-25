import { useState } from "react";
import { api } from "../api/client";

const INITIAL_FORM = {
  name: "",
  latitude: "18.5230",
  longitude: "73.8500",
  totalBeds: "100",
  availableBeds: "25",
  facilities: "EMERGENCY, ICU, TRAUMA_CENTER",
  status: "ACTIVE",
};

export default function HospitalsView({ user, hospitals, onRefresh }) {
  const isOperator = user.role === "RESOURCE_OPERATOR";

  const [form, setForm] = useState(INITIAL_FORM);
  const [bedEdits, setBedEdits] = useState({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function handleCreate(e) {
    e.preventDefault();
    setError("");
    setSuccess("");
    setBusy(true);

    try {
      const facList = form.facilities
        .split(",")
        .map((s) => s.trim().toUpperCase())
        .filter(Boolean);

      const created = await api.createHospital({
        name: form.name.trim(),
        latitude: Number(form.latitude),
        longitude: Number(form.longitude),
        totalBeds: Number(form.totalBeds),
        availableBeds: Number(form.availableBeds),
        facilities: facList,
        status: form.status,
      });

      setForm(INITIAL_FORM);
      setSuccess(`Hospital ${created.name} registered.`);
      await onRefresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleUpdateBeds(hospital) {
    setError("");
    setSuccess("");
    setBusy(true);
    try {
      const newBeds = Number(
        bedEdits[hospital.hospitalId] ?? hospital.availableBeds
      );
      await api.updateHospital(hospital.hospitalId, { availableBeds: newBeds });
      setSuccess(`Updated available beds for ${hospital.name} to ${newBeds}.`);
      await onRefresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleStatusToggle(hospital) {
    setError("");
    setSuccess("");
    setBusy(true);
    try {
      const next = hospital.status === "ACTIVE" ? "INACTIVE" : "ACTIVE";
      await api.updateHospital(hospital.hospitalId, { status: next });
      setSuccess(`Hospital ${hospital.name} set to ${next}.`);
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
            <h3>Register Hospital</h3>
          </div>
          <form onSubmit={handleCreate} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
            <div className="form-grid">
              <div className="field">
                <label>Hospital Name</label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="City General Hospital"
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
                <label>Total Beds</label>
                <input
                  type="number"
                  min="0"
                  value={form.totalBeds}
                  onChange={(e) =>
                    setForm({ ...form, totalBeds: e.target.value })
                  }
                  required
                />
              </div>
              <div className="field">
                <label>Available Beds</label>
                <input
                  type="number"
                  min="0"
                  value={form.availableBeds}
                  onChange={(e) =>
                    setForm({ ...form, availableBeds: e.target.value })
                  }
                  required
                />
              </div>
              <div className="field">
                <label>Facilities (comma-separated)</label>
                <input
                  type="text"
                  value={form.facilities}
                  onChange={(e) =>
                    setForm({ ...form, facilities: e.target.value })
                  }
                />
              </div>
            </div>
            <div>
              <button type="submit" className="btn btn-primary" disabled={busy}>
                {busy ? "Saving..." : "Register Hospital"}
              </button>
            </div>
          </form>
        </div>
      ) : (
        <div className="alert alert-info">
          Viewing hospitals in read-only mode. Sign in as a{" "}
          <strong>RESOURCE_OPERATOR</strong> to register or update hospital capacity.
        </div>
      )}

      <div className="card">
        <div className="card-header">
          <h3>Registered Hospitals ({hospitals.length})</h3>
        </div>
        {hospitals.length === 0 ? (
          <div className="empty-state">No hospitals registered yet.</div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Hospital</th>
                  <th>Status</th>
                  <th>Location</th>
                  <th>Beds (Avail / Total)</th>
                  <th>Facilities</th>
                  {isOperator && <th>Actions</th>}
                </tr>
              </thead>
              <tbody>
                {hospitals.map((h) => (
                  <tr key={h.hospitalId}>
                    <td>
                      <strong>{h.name}</strong>
                      <div style={{ fontSize: "11px", color: "#64748b" }}>
                        {h.hospitalId}
                      </div>
                    </td>
                    <td>
                      <span
                        className={`badge badge-${(h.status || "").toLowerCase()}`}
                      >
                        {h.status}
                      </span>
                    </td>
                    <td>
                      {h.latitude}, {h.longitude}
                    </td>
                    <td>
                      <strong>{h.availableBeds}</strong> / {h.totalBeds}
                    </td>
                    <td>
                      <div className="tag-list">
                        {(h.facilities || []).map((f) => (
                          <span key={f} className="tag">
                            {f}
                          </span>
                        ))}
                      </div>
                    </td>
                    {isOperator && (
                      <td>
                        <div className="btn-row">
                          <input
                            type="number"
                            min="0"
                            max={h.totalBeds}
                            value={bedEdits[h.hospitalId] ?? h.availableBeds}
                            onChange={(e) =>
                              setBedEdits({
                                ...bedEdits,
                                [h.hospitalId]: e.target.value,
                              })
                            }
                            style={{
                              width: "70px",
                              padding: "5px 6px",
                              border: "1px solid #cbd5e1",
                              borderRadius: "6px",
                              fontSize: "12px",
                            }}
                          />
                          <button
                            type="button"
                            className="btn btn-primary btn-sm"
                            disabled={busy}
                            onClick={() => handleUpdateBeds(h)}
                          >
                            Save Beds
                          </button>
                          <button
                            type="button"
                            className="btn btn-secondary btn-sm"
                            disabled={busy}
                            onClick={() => handleStatusToggle(h)}
                          >
                            {h.status === "ACTIVE" ? "Deactivate" : "Activate"}
                          </button>
                        </div>
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
