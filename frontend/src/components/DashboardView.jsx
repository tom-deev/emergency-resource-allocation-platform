import {
  formatDurationSeconds,
  formatIstDateTime,
} from "../utils/time";

export default function DashboardView({
  incidents,
  ambulances,
  hospitals,
  summary,
  onNavigate,
}) {
  const totalIncidents = summary?.totalIncidents ?? incidents.length;
  const criticalIncidents =
    summary?.criticalIncidents ??
    incidents.filter((i) => i.severity === "CRITICAL").length;
  const highPriorityIncidents =
    summary?.highPriorityIncidents ??
    incidents.filter((i) => i.severity === "HIGH").length;
  const pendingVerification =
    summary?.pendingVerification ??
    incidents.filter((i) => ["CREATED", "UNDER_REVIEW"].includes(i.status))
      .length;
  const awaitingAmbulance =
    summary?.awaitingAmbulance ??
    incidents.filter((i) => i.status === "VERIFIED").length;
  const pendingHospital =
    summary?.pendingHospitalAdmission ??
    incidents.filter((i) => i.status === "HOSPITAL_REQUESTED").length;
  const completedIncidents =
    summary?.completedIncidents ??
    incidents.filter((i) => i.status === "COMPLETED").length;
  const archivedIncidents = summary?.archivedIncidents ?? 0;

  const availableAmbulances =
    summary?.availableAmbulances ??
    ambulances.filter((a) => a.status === "AVAILABLE").length;
  const busyAmbulances =
    summary?.busyAmbulances ??
    ambulances.filter((a) => a.status === "BUSY").length;

  const activeHospitals = hospitals.filter((h) => h.status === "ACTIVE").length;
  const totalAvailableBeds =
    summary?.totalAvailableBeds ??
    hospitals.reduce((sum, h) => sum + Number(h.availableBeds || 0), 0);
  const totalBeds =
    summary?.totalBeds ??
    hospitals.reduce((sum, h) => sum + Number(h.totalBeds || 0), 0);
  const totalReservedBeds =
    summary?.totalReservedBeds ??
    incidents.reduce((sum, inc) => {
      const r = inc.bedReservation;
      if (r && ["RESERVED", "CONFIRMED"].includes(r.status)) {
        return sum + Number(r.bedsReserved || 0);
      }
      return sum;
    }, 0);

  const avgResponseSec = summary?.averageResponseTimeSeconds ?? null;
  const avgResponseLabel =
    avgResponseSec !== null && avgResponseSec !== undefined
      ? formatDurationSeconds(avgResponseSec)
      : "Unavailable";
  const avgSampleCount = summary?.responseTimeSampleCount ?? 0;

  const recentActivity = summary?.recentActivity || [];

  const severities = [
    { key: "CRITICAL", color: "#dc2626" },
    { key: "HIGH", color: "#d97706" },
    { key: "MEDIUM", color: "#2563eb" },
    { key: "LOW", color: "#16a34a" },
  ];

  const recentIncidents = [...incidents]
    .sort((a, b) => (b.createdAt || "").localeCompare(a.createdAt || ""))
    .slice(0, 6);

  return (
    <>
      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-label">Total Incidents</div>
          <div className="kpi-value">{totalIncidents}</div>
          <div className="kpi-sub">
            {criticalIncidents} critical &middot; {highPriorityIncidents} high
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">Pending Verification</div>
          <div className="kpi-value">{pendingVerification}</div>
          <div className="kpi-sub">{awaitingAmbulance} awaiting ambulance</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">Pending Hospital Admission</div>
          <div className="kpi-value">{pendingHospital}</div>
          <div className="kpi-sub">
            {completedIncidents} completed ({archivedIncidents} archived)
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">Ambulances</div>
          <div className="kpi-value">
            {availableAmbulances} / {ambulances.length}
          </div>
          <div className="kpi-sub">{busyAmbulances} dispatched (BUSY)</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">Hospital Beds</div>
          <div className="kpi-value">
            {totalAvailableBeds} / {totalBeds}
          </div>
          <div className="kpi-sub">
            {totalReservedBeds} reserved &middot; {activeHospitals} active hospitals
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">Avg Response Time</div>
          <div className="kpi-value" style={{ fontSize: "24px" }}>
            {avgResponseLabel}
          </div>
          <div className="kpi-sub">
            {avgSampleCount > 0
              ? `Based on ${avgSampleCount} dispatched incident(s)`
              : "Insufficient dispatch timestamp data"}
          </div>
        </div>
      </div>

      <div className="panel-grid">
        <div className="card">
          <div className="card-header">
            <h3>Incident Severity Distribution</h3>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => onNavigate("queue")}
            >
              Open Priority Queue
            </button>
          </div>
          {totalIncidents === 0 ? (
            <div className="empty-state">No incidents recorded yet.</div>
          ) : (
            <div className="bar-list">
              {severities.map(({ key, color }) => {
                const count = incidents.filter((i) => i.severity === key).length;
                const pct = Math.round((count / totalIncidents) * 100);
                return (
                  <div key={key} className="bar-row">
                    <div className="bar-label">
                      <span>{key}</span>
                      <span>
                        {count} ({pct}%)
                      </span>
                    </div>
                    <div className="bar-track">
                      <div
                        className="bar-fill"
                        style={{ width: `${pct}%`, backgroundColor: color }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="card">
          <div className="card-header">
            <h3>Hospital Capacity Snapshot</h3>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => onNavigate("hospitals")}
            >
              View Hospitals
            </button>
          </div>
          {hospitals.length === 0 ? (
            <div className="empty-state">No hospitals registered yet.</div>
          ) : (
            <div className="bar-list">
              {hospitals.slice(0, 5).map((h) => {
                const avail = Number(h.availableBeds || 0);
                const total = Number(h.totalBeds || 0);
                const pct = total > 0 ? Math.round((avail / total) * 100) : 0;
                return (
                  <div key={h.hospitalId} className="bar-row">
                    <div className="bar-label">
                      <span>{h.name}</span>
                      <span>
                        {avail} / {total} beds ({h.status})
                      </span>
                    </div>
                    <div className="bar-track">
                      <div
                        className="bar-fill"
                        style={{
                          width: `${pct}%`,
                          backgroundColor:
                            h.status !== "ACTIVE"
                              ? "#94a3b8"
                              : avail > 5
                                ? "#16a34a"
                                : "#d97706",
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      <div className="panel-grid">
        <div className="card">
          <div className="card-header">
            <h3>Recent Incident Activity Timeline (IST)</h3>
          </div>
          {recentActivity.length === 0 ? (
            <div className="empty-state">No incident activity recorded yet.</div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Time (IST)</th>
                    <th>Incident</th>
                    <th>Event</th>
                  </tr>
                </thead>
                <tbody>
                  {recentActivity.slice(0, 8).map((ev, idx) => (
                    <tr key={`${ev.incidentId}-${ev.event}-${idx}`}>
                      <td style={{ whiteSpace: "nowrap", fontSize: "12px" }}>
                        {formatIstDateTime(ev.timestamp)}
                      </td>
                      <td>
                        <code>{(ev.incidentId || "").slice(0, 12)}</code>{" "}
                        <span
                          className={`badge badge-${(ev.severity || "").toLowerCase()}`}
                        >
                          {ev.severity}
                        </span>
                      </td>
                      <td>
                        <strong>{ev.event}</strong>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="card">
          <div className="card-header">
            <h3>Recent Incidents</h3>
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={() => onNavigate("coordination")}
            >
              Open Coordination
            </button>
          </div>

          {recentIncidents.length === 0 ? (
            <div className="empty-state">
              No incidents yet. Create one from the Incidents page.
            </div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Type</th>
                    <th>Severity</th>
                    <th>Status</th>
                    <th>Reported (IST)</th>
                  </tr>
                </thead>
                <tbody>
                  {recentIncidents.map((inc) => (
                    <tr key={inc.incidentId}>
                      <td>
                        <code>{inc.incidentId.slice(0, 12)}</code>
                      </td>
                      <td>{inc.type}</td>
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
                      </td>
                      <td style={{ fontSize: "12px" }}>
                        {formatIstDateTime(inc.createdAt)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
