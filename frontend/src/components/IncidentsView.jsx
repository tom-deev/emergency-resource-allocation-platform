import { useState } from "react";
import { api } from "../api/client";
import {
  derivePriority,
  formatElapsedFromIso,
  formatIstDateTime,
} from "../utils/time";
import LocationPickerMap from "./maps/LocationPickerMap";
import IncidentLocationMap from "./maps/IncidentLocationMap";

const INITIAL_FORM = {
  type: "ROAD_ACCIDENT",
  description: "",
  latitude: "18.5204",
  longitude: "73.8567",
  severity: "HIGH",
  peopleAffected: "1",
  requiredEquipment: "OXYGEN, TRAUMA_KIT",
};

export default function IncidentsView({
  user,
  incidents,
  onRefresh,
  onSelectForCoordination,
}) {
  const isDispatcher = user.role === "DISPATCHER";
  const isOperator = user.role === "RESOURCE_OPERATOR";

  const [form, setForm] = useState(INITIAL_FORM);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [severityFilter, setSeverityFilter] = useState("ALL");
  const [selectedId, setSelectedId] = useState(null);
  const [remarks, setRemarks] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const selectedIncident = incidents.find((i) => i.incidentId === selectedId);

  const filtered = incidents.filter((inc) => {
    const q = search.trim().toLowerCase();
    const matchesSearch =
      !q ||
      (inc.incidentId || "").toLowerCase().includes(q) ||
      (inc.type || "").toLowerCase().includes(q) ||
      (inc.description || "").toLowerCase().includes(q);
    const matchesStatus =
      statusFilter === "ALL" || inc.status === statusFilter;
    const matchesSeverity =
      severityFilter === "ALL" || inc.severity === severityFilter;
    return matchesSearch && matchesStatus && matchesSeverity;
  });

  async function handleCreate(e) {
    e.preventDefault();
    setError("");
    setSuccess("");
    setBusy(true);

    try {
      const equipmentList = form.requiredEquipment
        .split(",")
        .map((s) => s.trim().toUpperCase())
        .filter(Boolean);

      const created = await api.createIncident({
        type: form.type.trim(),
        description: form.description.trim(),
        latitude: Number(form.latitude),
        longitude: Number(form.longitude),
        severity: form.severity,
        peopleAffected: Number(form.peopleAffected),
        requiredResources: ["AMBULANCE"],
        requiredEquipment: equipmentList,
      });

      setForm(INITIAL_FORM);
      setSelectedId(created.incidentId);
      setSuccess(`Incident ${created.incidentId} created (status: CREATED).`);
      await onRefresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function runAction(fn, okMessage) {
    setError("");
    setSuccess("");
    setBusy(true);
    try {
      await fn();
      setSuccess(okMessage);
      setRemarks("");
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

      {isDispatcher && (
        <div className="card">
          <div className="card-header">
            <h3>Report New Emergency Incident</h3>
          </div>
          <form onSubmit={handleCreate} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
            <div className="form-grid">
              <div className="field">
                <label>Emergency Type</label>
                <select
                  value={form.type}
                  onChange={(e) => setForm({ ...form, type: e.target.value })}
                >
                  <option value="ROAD_ACCIDENT">ROAD_ACCIDENT</option>
                  <option value="MEDICAL">MEDICAL</option>
                  <option value="FIRE">FIRE</option>
                  <option value="CARDIAC">CARDIAC</option>
                  <option value="TRAUMA">TRAUMA</option>
                </select>
              </div>
              <div className="field">
                <label>Severity</label>
                <select
                  value={form.severity}
                  onChange={(e) => setForm({ ...form, severity: e.target.value })}
                >
                  <option value="CRITICAL">CRITICAL</option>
                  <option value="HIGH">HIGH</option>
                  <option value="MEDIUM">MEDIUM</option>
                  <option value="LOW">LOW</option>
                </select>
              </div>
              <div className="field">
                <label>People Affected</label>
                <input
                  type="number"
                  min="0"
                  value={form.peopleAffected}
                  onChange={(e) =>
                    setForm({ ...form, peopleAffected: e.target.value })
                  }
                  required
                />
              </div>
              <div className="field">
                <label>Latitude (-90 to 90)</label>
                <input
                  type="number"
                  step="any"
                  value={form.latitude}
                  onChange={(e) => setForm({ ...form, latitude: e.target.value })}
                  required
                />
              </div>
              <div className="field">
                <label>Longitude (-180 to 180)</label>
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
                <label>Required Equipment (comma-separated)</label>
                <input
                  type="text"
                  value={form.requiredEquipment}
                  onChange={(e) =>
                    setForm({ ...form, requiredEquipment: e.target.value })
                  }
                  placeholder="OXYGEN, DEFIBRILLATOR"
                />
              </div>
            </div>

            <LocationPickerMap
              latitude={form.latitude}
              longitude={form.longitude}
              onChange={(lat, lng) =>
                setForm((prev) => ({
                  ...prev,
                  latitude: String(lat),
                  longitude: String(lng),
                }))
              }
            />

            <div className="field">
              <label>Description</label>
              <textarea
                rows={2}
                value={form.description}
                onChange={(e) =>
                  setForm({ ...form, description: e.target.value })
                }
                placeholder="Describe location landmarks, injuries, and immediate needs..."
                required
              />
            </div>

            <div>
              <button type="submit" className="btn btn-primary" disabled={busy}>
                {busy ? "Submitting..." : "Create Incident"}
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="card">
        <div className="card-header">
          <h3>
            {isDispatcher ? "My Reported Incidents" : "All Incidents"} (
            {filtered.length})
          </h3>
        </div>

        <div className="filters-bar">
          <input
            type="text"
            placeholder="Search ID, type, description..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ minWidth: "240px" }}
          />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="ALL">All Statuses</option>
            <option value="CREATED">CREATED</option>
            <option value="UNDER_REVIEW">UNDER_REVIEW</option>
            <option value="VERIFIED">VERIFIED</option>
            <option value="REJECTED">REJECTED</option>
            <option value="AMBULANCE_ASSIGNED">AMBULANCE_ASSIGNED</option>
            <option value="HOSPITAL_REQUESTED">HOSPITAL_REQUESTED</option>
            <option value="HOSPITAL_ACCEPTED">HOSPITAL_ACCEPTED</option>
            <option value="HOSPITAL_REJECTED">HOSPITAL_REJECTED</option>
            <option value="PATIENT_TRANSPORTED">PATIENT_TRANSPORTED</option>
            <option value="COMPLETED">COMPLETED</option>
            <option value="CANCELLED">CANCELLED</option>
          </select>
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
          >
            <option value="ALL">All Severities</option>
            <option value="CRITICAL">CRITICAL</option>
            <option value="HIGH">HIGH</option>
            <option value="MEDIUM">MEDIUM</option>
            <option value="LOW">LOW</option>
          </select>
        </div>

        {filtered.length === 0 ? (
          <div className="empty-state">No matching incidents found.</div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Type &amp; Description</th>
                  <th>Severity</th>
                  <th>Status</th>
                  <th>Location</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((inc) => (
                  <tr key={inc.incidentId}>
                    <td>
                      <code>{inc.incidentId.slice(0, 12)}</code>
                    </td>
                    <td>
                      <strong>{inc.type}</strong>
                      <div style={{ fontSize: "12px", color: "#64748b" }}>
                        {inc.description}
                      </div>
                    </td>
                    <td>
                      <span
                        className={`badge badge-${(inc.severity || "").toLowerCase()}`}
                      >
                        {inc.severity}
                      </span>
                    </td>
                    <td>
                      <span
                        className={`badge badge-${(inc.status || "").toLowerCase()}`}
                      >
                        {inc.status}
                      </span>
                      {inc.isArchived && (
                        <span
                          className="badge badge-low"
                          style={{ marginLeft: "6px" }}
                        >
                          ARCHIVED
                        </span>
                      )}
                    </td>
                    <td>
                      {inc.latitude}, {inc.longitude}
                    </td>
                    <td>
                      <div className="btn-row">
                        <button
                          type="button"
                          className="btn btn-secondary btn-sm"
                          onClick={() => setSelectedId(inc.incidentId)}
                        >
                          {isOperator ? "Inspect / Review" : "View Details"}
                        </button>
                        {isOperator &&
                          ![
                            "CREATED",
                            "UNDER_REVIEW",
                            "REJECTED",
                            "CANCELLED",
                          ].includes(inc.status) && (
                            <button
                              type="button"
                              className="btn btn-primary btn-sm"
                              onClick={() =>
                                onSelectForCoordination(inc.incidentId)
                              }
                            >
                              Coordinate
                            </button>
                          )}
                        {isOperator &&
                          inc.status === "COMPLETED" &&
                          !inc.isArchived && (
                            <button
                              type="button"
                              className="btn btn-secondary btn-sm"
                              disabled={busy}
                              onClick={() => {
                                if (
                                  window.confirm(
                                    `Archive completed incident ${inc.incidentId.slice(0, 12)}? It will move to Archived Incidents.`
                                  )
                                ) {
                                  runAction(
                                    () => api.archiveIncident(inc.incidentId),
                                    `Incident ${inc.incidentId.slice(0, 12)} archived.`
                                  );
                                }
                              }}
                            >
                              Archive
                            </button>
                          )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {selectedIncident && (
        <div className="card">
          <div className="card-header">
            <h3>
              Incident Details — <code>{selectedIncident.incidentId}</code>
            </h3>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => setSelectedId(null)}
            >
              Close
            </button>
          </div>

          <div className="form-grid" style={{ marginBottom: "16px" }}>
            <div>
              <strong>Status:</strong>{" "}
              <span
                className={`badge badge-${(selectedIncident.status || "").toLowerCase()}`}
              >
                {selectedIncident.status}
              </span>
            </div>
            <div>
              <strong>Priority / Severity:</strong>{" "}
              <span
                className={`badge badge-priority-${(
                  selectedIncident.priority ||
                  derivePriority(selectedIncident.severity)
                ).toLowerCase()}`}
              >
                {selectedIncident.priority ||
                  derivePriority(selectedIncident.severity)}
              </span>{" "}
              {selectedIncident.severity}
            </div>
            <div>
              <strong>Reported (IST):</strong>{" "}
              {formatIstDateTime(selectedIncident.createdAt)} (
              {formatElapsedFromIso(selectedIncident.createdAt)} ago)
            </div>
            <div>
              <strong>People Affected:</strong> {selectedIncident.peopleAffected}
            </div>
            {isOperator && (
              <>
                <div>
                  <strong>Reporter:</strong>{" "}
                  {selectedIncident.createdByUsername ||
                    "Legacy / Unrecorded Reporter"}
                </div>
                <div>
                  <strong>Reviewed By:</strong>{" "}
                  {selectedIncident.reviewedBy || "Not yet reviewed"}
                </div>
                <div>
                  <strong>Remarks:</strong>{" "}
                  {selectedIncident.verificationRemarks || "—"}
                </div>
                <div>
                  <strong>Equipment Needed:</strong>{" "}
                  {(selectedIncident.requiredEquipment || []).join(", ") || "None"}
                </div>
              </>
            )}
          </div>

          <div style={{ marginBottom: "16px" }}>
            <IncidentLocationMap incident={selectedIncident} />
          </div>

          {!isOperator && (
            <div className="alert alert-info" style={{ marginBottom: "12px" }}>
              Your incident has been logged. Verification, ambulance dispatch,
              and hospital coordination are managed internally by a{" "}
              <strong>RESOURCE_OPERATOR</strong>.
            </div>
          )}

          {isOperator && selectedIncident.status === "CREATED" && (
            <div className="btn-row">
              <button
                type="button"
                className="btn btn-primary"
                disabled={busy}
                onClick={() =>
                  runAction(
                    () => api.startReview(selectedIncident.incidentId),
                    "Incident moved to UNDER_REVIEW."
                  )
                }
              >
                Start Review
              </button>
              <button
                type="button"
                className="btn btn-danger"
                disabled={busy}
                onClick={() =>
                  runAction(
                    () => api.cancelIncident(selectedIncident.incidentId),
                    "Incident cancelled."
                  )
                }
              >
                Cancel Incident
              </button>
            </div>
          )}

          {isOperator && selectedIncident.status === "UNDER_REVIEW" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <div className="field">
                <label>Verification Remarks / Rejection Reason</label>
                <input
                  type="text"
                  value={remarks}
                  onChange={(e) => setRemarks(e.target.value)}
                  placeholder="e.g. Verified via callback, or reason for rejection"
                />
              </div>
              <div className="btn-row">
                <button
                  type="button"
                  className="btn btn-success"
                  disabled={busy}
                  onClick={() =>
                    runAction(
                      () =>
                        api.verifyIncident(selectedIncident.incidentId, {
                          decision: "VERIFIED",
                          remarks: remarks || undefined,
                        }),
                      "Incident VERIFIED. Ready for manual ambulance assignment."
                    )
                  }
                >
                  Verify Incident
                </button>
                <button
                  type="button"
                  className="btn btn-danger"
                  disabled={busy}
                  onClick={() =>
                    runAction(
                      () =>
                        api.verifyIncident(selectedIncident.incidentId, {
                          decision: "REJECTED",
                          remarks: remarks || "Rejected by Resource Operator",
                        }),
                      "Incident REJECTED."
                    )
                  }
                >
                  Reject Incident
                </button>
              </div>
            </div>
          )}

          {isOperator && selectedIncident.status === "VERIFIED" && (
            <button
              type="button"
              className="btn btn-primary"
              onClick={() =>
                onSelectForCoordination(selectedIncident.incidentId)
              }
            >
              Proceed to Manual Resource Coordination
            </button>
          )}
        </div>
      )}
    </>
  );
}
