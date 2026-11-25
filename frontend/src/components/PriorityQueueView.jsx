import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import {
  derivePriority,
  formatElapsedFromIso,
  formatIstDate,
  formatIstTime,
} from "../utils/time";

export default function PriorityQueueView({ onInspectIncident }) {
  const [queueData, setQueueData] = useState({
    incidents: [],
    thresholdsMinutes: { P1: 5, P2: 15, P3: 30, P4: 60 },
    generatedAt: null,
  });
  const [priorityFilter, setPriorityFilter] = useState("ALL");
  const [severityFilter, setSeverityFilter] = useState("ALL");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [dateFilter, setDateFilter] = useState("");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [nowMs, setNowMs] = useState(() => Date.now());

  const loadQueue = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await api.getIncidentQueue({
        priority: priorityFilter,
        severity: severityFilter,
        status: statusFilter,
        date: dateFilter,
        search: search.trim(),
      });
      setQueueData({
        incidents: Array.isArray(data?.incidents) ? data.incidents : [],
        thresholdsMinutes: data?.thresholdsMinutes || {
          P1: 5,
          P2: 15,
          P3: 30,
          P4: 60,
        },
        generatedAt: data?.generatedAt || null,
      });
      setNowMs(Date.now());
    } catch (err) {
      setError(err.message || "Failed to load incident priority queue.");
    } finally {
      setLoading(false);
    }
  }, [priorityFilter, severityFilter, statusFilter, dateFilter, search]);

  useEffect(() => {
    let cancelled = false;

    async function fetchInitial() {
      try {
        const data = await api.getIncidentQueue({
          priority: priorityFilter,
          severity: severityFilter,
          status: statusFilter,
          date: dateFilter,
          search: search.trim(),
        });
        if (cancelled) return;
        setQueueData({
          incidents: Array.isArray(data?.incidents) ? data.incidents : [],
          thresholdsMinutes: data?.thresholdsMinutes || {
            P1: 5,
            P2: 15,
            P3: 30,
            P4: 60,
          },
          generatedAt: data?.generatedAt || null,
        });
        setNowMs(Date.now());
        setError("");
      } catch (err) {
        if (!cancelled) {
          setError(err.message || "Failed to load incident priority queue.");
        }
      }
    }

    fetchInitial();
    return () => {
      cancelled = true;
    };
  }, [priorityFilter, severityFilter, statusFilter, dateFilter, search]);

  // Update displayed elapsed waiting timers locally every 30s without aggressive API polling
  useEffect(() => {
    const id = setInterval(() => {
      setNowMs(Date.now());
    }, 30000);
    return () => clearInterval(id);
  }, []);

  const { incidents, thresholdsMinutes } = queueData;
  const overdueCount = incidents.filter((inc) => inc.isOverdue).length;

  return (
    <>
      {error && <div className="alert alert-error">{error}</div>}

      <div className="card">
        <div className="card-header">
          <div>
            <h3>Incoming Incidents — Priority Queue ({incidents.length})</h3>
            <p style={{ fontSize: "12px", color: "#64748b", marginTop: "3px" }}>
              Sorted deterministically: <strong>P1 (CRITICAL) → P4 (LOW)</strong>,
              then oldest reporting time first. All timestamps shown in{" "}
              <strong>Asia/Kolkata (IST)</strong>.
            </p>
          </div>
          <div className="btn-row">
            {overdueCount > 0 && (
              <span className="badge badge-overdue">
                {overdueCount} Waiting Over Threshold
              </span>
            )}
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={loadQueue}
              disabled={loading}
            >
              {loading ? "Refreshing..." : "Refresh Queue"}
            </button>
          </div>
        </div>

        <div className="threshold-bar">
          <span>Waiting alert thresholds:</span>
          <span>
            <strong>P1:</strong> {thresholdsMinutes.P1}m
          </span>
          <span>
            <strong>P2:</strong> {thresholdsMinutes.P2}m
          </span>
          <span>
            <strong>P3:</strong> {thresholdsMinutes.P3}m
          </span>
          <span>
            <strong>P4:</strong> {thresholdsMinutes.P4}m
          </span>
        </div>

        <div className="filters-bar">
          <input
            type="text"
            placeholder="Search Incident ID or emergency type..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ minWidth: "230px" }}
          />
          <select
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
            aria-label="Filter by priority"
          >
            <option value="ALL">All Priorities</option>
            <option value="P1">P1 — CRITICAL</option>
            <option value="P2">P2 — HIGH</option>
            <option value="P3">P3 — MEDIUM</option>
            <option value="P4">P4 — LOW</option>
          </select>
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            aria-label="Filter by severity"
          >
            <option value="ALL">All Severities</option>
            <option value="CRITICAL">CRITICAL</option>
            <option value="HIGH">HIGH</option>
            <option value="MEDIUM">MEDIUM</option>
            <option value="LOW">LOW</option>
          </select>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            aria-label="Filter by status"
          >
            <option value="ALL">All Statuses</option>
            <option value="CREATED">CREATED</option>
            <option value="UNDER_REVIEW">UNDER_REVIEW</option>
            <option value="VERIFIED">VERIFIED</option>
            <option value="AMBULANCE_ASSIGNED">AMBULANCE_ASSIGNED</option>
            <option value="HOSPITAL_REQUESTED">HOSPITAL_REQUESTED</option>
            <option value="HOSPITAL_ACCEPTED">HOSPITAL_ACCEPTED</option>
            <option value="HOSPITAL_REJECTED">HOSPITAL_REJECTED</option>
            <option value="PATIENT_TRANSPORTED">PATIENT_TRANSPORTED</option>
            <option value="COMPLETED">COMPLETED</option>
            <option value="REJECTED">REJECTED</option>
            <option value="CANCELLED">CANCELLED</option>
          </select>
          <input
            type="date"
            value={dateFilter}
            onChange={(e) => setDateFilter(e.target.value)}
            title="Filter by IST reporting date"
          />
          {(priorityFilter !== "ALL" ||
            severityFilter !== "ALL" ||
            statusFilter !== "ALL" ||
            dateFilter ||
            search) && (
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => {
                setPriorityFilter("ALL");
                setSeverityFilter("ALL");
                setStatusFilter("ALL");
                setDateFilter("");
                setSearch("");
              }}
            >
              Clear Filters
            </button>
          )}
        </div>

        {incidents.length === 0 ? (
          <div className="empty-state">
            No incidents match the selected queue filters.
          </div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Priority</th>
                  <th>Incident ID &amp; Type</th>
                  <th>Severity</th>
                  <th>Reported (IST)</th>
                  <th>Waiting / Last Update</th>
                  <th>People</th>
                  <th>Location</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {incidents.map((inc) => {
                  const priority = inc.priority || derivePriority(inc.severity);
                  return (
                    <tr
                      key={inc.incidentId}
                      className={inc.isOverdue ? "row-overdue" : ""}
                    >
                      <td>
                        <span
                          className={`badge badge-priority-${priority.toLowerCase()}`}
                        >
                          {priority}
                        </span>
                      </td>
                      <td>
                        <code>{inc.incidentId.slice(0, 12)}</code>
                        <div style={{ fontWeight: 600, marginTop: "2px" }}>
                          {inc.type}
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
                        <div>{formatIstDate(inc.createdAt)}</div>
                        <div style={{ fontSize: "12px", color: "#64748b" }}>
                          {formatIstTime(inc.createdAt)}
                        </div>
                      </td>
                      <td>
                        <div style={{ fontWeight: 600 }}>
                          {formatElapsedFromIso(inc.createdAt, nowMs)}
                          {inc.isOverdue && (
                            <span
                              className="badge badge-overdue"
                              style={{ marginLeft: "6px" }}
                            >
                              OVERDUE
                            </span>
                          )}
                        </div>
                        <div style={{ fontSize: "11px", color: "#64748b" }}>
                          Updated{" "}
                          {formatElapsedFromIso(
                            inc.updatedAt || inc.createdAt,
                            nowMs
                          )}{" "}
                          ago
                        </div>
                      </td>
                      <td>{inc.peopleAffected}</td>
                      <td>
                        <code>
                          {Number(inc.latitude).toFixed(4)},{" "}
                          {Number(inc.longitude).toFixed(4)}
                        </code>
                      </td>
                      <td>
                        <span
                          className={`badge badge-${(inc.status || "").toLowerCase()}`}
                        >
                          {inc.status}
                        </span>
                      </td>
                      <td>
                        <button
                          type="button"
                          className="btn btn-primary btn-sm"
                          onClick={() => onInspectIncident(inc.incidentId)}
                        >
                          Inspect
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
    </>
  );
}
