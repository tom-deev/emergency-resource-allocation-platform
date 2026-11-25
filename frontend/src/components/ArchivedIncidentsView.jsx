import { useState } from "react";
import { derivePriority, formatIstDateTime } from "../utils/time";
import IncidentLocationMap from "./maps/IncidentLocationMap";

export default function ArchivedIncidentsView({ archivedIncidents = [] }) {
  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState(null);

  const filtered = archivedIncidents.filter((inc) => {
    const q = search.trim().toLowerCase();
    if (!q) return true;
    return (
      (inc.incidentId || "").toLowerCase().includes(q) ||
      (inc.type || "").toLowerCase().includes(q) ||
      (inc.description || "").toLowerCase().includes(q)
    );
  });

  const selected = archivedIncidents.find((i) => i.incidentId === selectedId);

  return (
    <>
      <div className="card">
        <div className="card-header">
          <div>
            <h3>Archived Incidents ({filtered.length})</h3>
            <p style={{ fontSize: "12px", color: "#64748b", marginTop: "3px" }}>
              Completed incidents archived by Resource Operators (sorted newest
              archived first). Workflow status remains <strong>COMPLETED</strong>{" "}
              with all timestamps and reservation history preserved.
            </p>
          </div>
          <input
            type="text"
            placeholder="Search archived ID, type..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{
              padding: "8px 10px",
              border: "1px solid #cbd5e1",
              borderRadius: "7px",
              fontSize: "13px",
              minWidth: "220px",
            }}
          />
        </div>

        {filtered.length === 0 ? (
          <div className="empty-state">
            No archived incidents yet. Completed incidents can be archived from
            Incidents or Resource Coordination.
          </div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Incident ID</th>
                  <th>Type</th>
                  <th>Severity / Priority</th>
                  <th>Completed (IST)</th>
                  <th>Archived (IST)</th>
                  <th>Archived By</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((inc) => {
                  const priority = inc.priority || derivePriority(inc.severity);
                  return (
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
                          className={`badge badge-priority-${priority.toLowerCase()}`}
                        >
                          {priority}
                        </span>{" "}
                        <span
                          className={`badge badge-${(inc.severity || "").toLowerCase()}`}
                        >
                          {inc.severity}
                        </span>
                      </td>
                      <td style={{ fontSize: "12px" }}>
                        {formatIstDateTime(inc.completedAt)}
                      </td>
                      <td style={{ fontSize: "12px" }}>
                        {formatIstDateTime(inc.archivedAt)}
                      </td>
                      <td>
                        <code>{inc.archivedBy || "—"}</code>
                      </td>
                      <td>
                        <button
                          type="button"
                          className="btn btn-secondary btn-sm"
                          onClick={() => setSelectedId(inc.incidentId)}
                        >
                          View Record
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {selected && (
        <div className="card">
          <div className="card-header">
            <h3>
              Archived Record — <code>{selected.incidentId}</code>
            </h3>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => setSelectedId(null)}
            >
              Close
            </button>
          </div>

          <div className="form-grid" style={{ marginBottom: "14px" }}>
            <div>
              <strong>Status:</strong>{" "}
              <span className="badge badge-completed">{selected.status}</span>{" "}
              <span className="badge badge-low">ARCHIVED</span>
            </div>
            <div>
              <strong>Reporter:</strong>{" "}
              {selected.createdByUsername || "Legacy / Unrecorded Reporter"}
            </div>
            <div>
              <strong>People Affected:</strong> {selected.peopleAffected}
            </div>
            <div>
              <strong>Assigned Ambulance:</strong>{" "}
              {selected.assignedAmbulanceId || "None"}
            </div>
            <div>
              <strong>Assigned Hospital:</strong>{" "}
              {selected.assignedHospitalId || "None"}
            </div>
            <div>
              <strong>Bed Reservation:</strong>{" "}
              {selected.bedReservation
                ? `${selected.bedReservation.bedsReserved} bed(s) (${selected.bedReservation.status})`
                : "None"}
            </div>
          </div>

          <div className="threshold-bar">
            <span>
              <strong>Reported:</strong> {formatIstDateTime(selected.createdAt)}
            </span>
            {selected.verifiedAt && (
              <span>
                <strong>Verified:</strong>{" "}
                {formatIstDateTime(selected.verifiedAt)}
              </span>
            )}
            {selected.ambulanceAssignedAt && (
              <span>
                <strong>Dispatched:</strong>{" "}
                {formatIstDateTime(selected.ambulanceAssignedAt)}
              </span>
            )}
            {selected.hospitalAcceptedAt && (
              <span>
                <strong>Hospital Accepted:</strong>{" "}
                {formatIstDateTime(selected.hospitalAcceptedAt)}
              </span>
            )}
            {selected.transportedAt && (
              <span>
                <strong>Transported:</strong>{" "}
                {formatIstDateTime(selected.transportedAt)}
              </span>
            )}
            {selected.completedAt && (
              <span>
                <strong>Completed:</strong>{" "}
                {formatIstDateTime(selected.completedAt)}
              </span>
            )}
            {selected.archivedAt && (
              <span>
                <strong>Archived:</strong>{" "}
                {formatIstDateTime(selected.archivedAt)}
              </span>
            )}
          </div>

          <IncidentLocationMap incident={selected} />
        </div>
      )}
    </>
  );
}
