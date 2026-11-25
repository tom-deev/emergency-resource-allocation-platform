import { useEffect, useState } from "react";
import { api } from "../api/client";
import {
  buildGoogleMapsDirectionsUrl,
  formatCoord,
  isValidCoordinates,
  parseCoordinate,
} from "../utils/maps";
import {
  derivePriority,
  formatElapsedFromIso,
  formatIstDateTime,
} from "../utils/time";
import CoordinationMap from "./maps/CoordinationMap";

const WORKFLOW_STEPS = [
  "CREATED",
  "UNDER_REVIEW",
  "VERIFIED",
  "AMBULANCE_ASSIGNED",
  "HOSPITAL_REQUESTED",
  "HOSPITAL_ACCEPTED",
  "PATIENT_TRANSPORTED",
  "COMPLETED",
];

export default function CoordinationView({
  user,
  incidents,
  ambulances = [],
  hospitals = [],
  initialIncidentId,
  onRefresh,
}) {
  const isOperator = user.role === "RESOURCE_OPERATOR";

  const [selectedId, setSelectedId] = useState(initialIncidentId || "");
  const [candidates, setCandidates] = useState(null);
  const [facilityFilter, setFacilityFilter] = useState("");
  const [bedsInputByIncident, setBedsInputByIncident] = useState({});
  const [reviewRemarks, setReviewRemarks] = useState("");
  const [rejectionReason, setRejectionReason] = useState("");
  const [browserOrigin, setBrowserOrigin] = useState(null);
  const [locatingOrigin, setLocatingOrigin] = useState(false);
  const [loadingCands, setLoadingCands] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const preferredIncident =
    incidents.find((i) =>
      [
        "CREATED",
        "UNDER_REVIEW",
        "VERIFIED",
        "AMBULANCE_ASSIGNED",
        "HOSPITAL_REQUESTED",
        "HOSPITAL_ACCEPTED",
        "HOSPITAL_REJECTED",
        "PATIENT_TRANSPORTED",
      ].includes(i.status)
    ) || incidents[0];

  const effectiveSelectedId =
    selectedId || initialIncidentId || preferredIncident?.incidentId || "";

  const incident = incidents.find((i) => i.incidentId === effectiveSelectedId);
  const incidentId = incident?.incidentId || "";
  const incidentStatus = incident?.status || "";
  const needsCandidates =
    isOperator &&
    Boolean(incidentId) &&
    [
      "CREATED",
      "UNDER_REVIEW",
      "VERIFIED",
      "AMBULANCE_ASSIGNED",
      "HOSPITAL_REJECTED",
    ].includes(incidentStatus);

  async function loadCandidates(
    incId,
    rawFacilities = facilityFilter,
    bedsOverride = null
  ) {
    if (!incId || !isOperator) return;
    setLoadingCands(true);
    setError("");
    try {
      const facs = rawFacilities
        .split(",")
        .map((s) => s.trim().toUpperCase())
        .filter(Boolean);
      const data = await api.getCandidates(incId, facs, bedsOverride);
      setCandidates(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingCands(false);
    }
  }

  useEffect(() => {
    if (!needsCandidates) return;
    let cancelled = false;

    async function fetchCands() {
      try {
        const data = await api.getCandidates(incidentId, []);
        if (!cancelled) {
          setCandidates(data);
          setError("");
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message);
        }
      }
    }

    fetchCands();
    return () => {
      cancelled = true;
    };
  }, [incidentId, incidentStatus, needsCandidates]);

  async function runAction(fn, okMessage) {
    setError("");
    setSuccess("");
    setBusy(true);
    try {
      await fn();
      setSuccess(okMessage);
      setRejectionReason("");
      await onRefresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const currentStepIdx = incident
    ? WORKFLOW_STEPS.indexOf(incident.status)
    : -1;

  const incLat = parseCoordinate(incident?.latitude);
  const incLng = parseCoordinate(incident?.longitude);
  const hasIncidentCoords = isValidCoordinates(incLat, incLng);
  const showResponderNav = Boolean(incident?.assignedAmbulanceId) && hasIncidentCoords;
  const directionsUrl = showResponderNav
    ? buildGoogleMapsDirectionsUrl(incLat, incLng, browserOrigin)
    : "";

  const assignedHospital = hospitals.find(
    (h) => h.hospitalId === incident?.assignedHospitalId
  );
  const hospLat = parseCoordinate(assignedHospital?.latitude);
  const hospLng = parseCoordinate(assignedHospital?.longitude);
  const hasHospitalCoords = isValidCoordinates(hospLat, hospLng);
  const showHospitalNav =
    Boolean(assignedHospital) &&
    hasHospitalCoords &&
    ["HOSPITAL_ACCEPTED", "PATIENT_TRANSPORTED", "COMPLETED"].includes(
      incident?.status
    );
  const hospitalDirectionsUrl = showHospitalNav
    ? buildGoogleMapsDirectionsUrl(hospLat, hospLng, browserOrigin)
    : "";

  function openExternalDirectionsWithOrigin(destLat, destLng) {
    if (!isValidCoordinates(destLat, destLng)) return;
    if (!navigator.geolocation) {
      window.open(
        buildGoogleMapsDirectionsUrl(destLat, destLng),
        "_blank",
        "noopener,noreferrer"
      );
      return;
    }

    setLocatingOrigin(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const origin = {
          lat: Number(position.coords.latitude.toFixed(6)),
          lng: Number(position.coords.longitude.toFixed(6)),
        };
        setBrowserOrigin(origin);
        setLocatingOrigin(false);
        window.open(
          buildGoogleMapsDirectionsUrl(destLat, destLng, origin),
          "_blank",
          "noopener,noreferrer"
        );
      },
      () => {
        setLocatingOrigin(false);
        window.open(
          buildGoogleMapsDirectionsUrl(destLat, destLng),
          "_blank",
          "noopener,noreferrer"
        );
      },
      { enableHighAccuracy: true, timeout: 6000 }
    );
  }

  function handleNavigateWithCurrentOrigin() {
    openExternalDirectionsWithOrigin(incLat, incLng);
  }

  const pendingHospitalRequests = incidents.filter(
    (i) => i.status === "HOSPITAL_REQUESTED"
  );

  return (
    <>
      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      {isOperator && (
        <div className="card">
          <div className="card-header">
            <h3>
              Pending Hospital Admission Requests ({pendingHospitalRequests.length})
            </h3>
          </div>
          {pendingHospitalRequests.length === 0 ? (
            <div className="empty-state">
              No pending hospital admission requests at this time.
            </div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Incident</th>
                    <th>Type &amp; Severity</th>
                    <th>Requested Hospital</th>
                    <th>People</th>
                    <th>Decision</th>
                  </tr>
                </thead>
                <tbody>
                  {pendingHospitalRequests.map((inc) => (
                    <tr key={inc.incidentId}>
                      <td>
                        <code>{inc.incidentId.slice(0, 12)}</code>
                      </td>
                      <td>
                        <strong>{inc.type}</strong>{" "}
                        <span
                          className={`badge badge-${(inc.severity || "").toLowerCase()}`}
                        >
                          {inc.severity}
                        </span>
                      </td>
                      <td>
                        <code>{inc.assignedHospitalId}</code>
                      </td>
                      <td>{inc.peopleAffected}</td>
                      <td>
                        <div className="btn-row">
                          <button
                            type="button"
                            className="btn btn-success btn-sm"
                            disabled={busy}
                            onClick={() =>
                              runAction(
                                () =>
                                  api.recordHospitalDecision(inc.incidentId, {
                                    decision: "ACCEPTED",
                                  }),
                                `Admission CONFIRMED for ${inc.incidentId}. Reserved beds confirmed.`
                              )
                            }
                          >
                            Confirm Admission
                          </button>
                          <input
                            type="text"
                            placeholder="Rejection / cancel reason..."
                            value={rejectionReason}
                            onChange={(e) => setRejectionReason(e.target.value)}
                            style={{
                              padding: "5px 8px",
                              border: "1px solid #cbd5e1",
                              borderRadius: "6px",
                              fontSize: "12px",
                            }}
                          />
                          <button
                            type="button"
                            className="btn btn-danger btn-sm"
                            disabled={busy}
                            onClick={() =>
                              runAction(
                                () =>
                                  api.recordHospitalDecision(inc.incidentId, {
                                    decision: "REJECTED",
                                    reason:
                                      rejectionReason || "Capacity unavailable",
                                  }),
                                `Admission REJECTED for ${inc.incidentId}. Reserved beds released.`
                              )
                            }
                          >
                            Reject (Release Beds)
                          </button>
                          <button
                            type="button"
                            className="btn btn-secondary btn-sm"
                            disabled={busy}
                            onClick={() =>
                              runAction(
                                () =>
                                  api.cancelHospitalReservation(
                                    inc.incidentId,
                                    rejectionReason || "Cancelled by operator"
                                  ),
                                `Reservation cancelled for ${inc.incidentId}. Beds released.`
                              )
                            }
                          >
                            Cancel Reservation
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      <div className="card">
        <div className="card-header">
          <h3>
            {isOperator
              ? "Incident Inspection & Resource Coordination"
              : "Incident Workflow Monitor (Read-Only)"}
          </h3>
          <select
            value={effectiveSelectedId}
            onChange={(e) => {
              setSelectedId(e.target.value);
              setError("");
              setSuccess("");
            }}
            style={{
              padding: "8px 10px",
              border: "1px solid #cbd5e1",
              borderRadius: "7px",
              fontSize: "13px",
              minWidth: "280px",
            }}
          >
            <option value="">-- Select an incident --</option>
            {incidents.map((inc) => (
              <option key={inc.incidentId} value={inc.incidentId}>
                [{inc.priority || derivePriority(inc.severity)}]{" "}
                {inc.incidentId.slice(0, 12)} | {inc.type} | {inc.status}
              </option>
            ))}
          </select>
        </div>

        {!isOperator && (
          <div className="alert alert-info" style={{ marginBottom: "14px" }}>
            <strong>Dispatcher Monitoring View:</strong> Incident verification,
            ambulance dispatch, hospital admission, transport, and completion
            are executed by a <strong>RESOURCE_OPERATOR</strong>.
          </div>
        )}

        {!incident ? (
          <div className="empty-state">
            Select an incident above to view its lifecycle and coordinate resources.
          </div>
        ) : (
          <>
            <div className="stepper">
              {WORKFLOW_STEPS.map((step, idx) => (
                <span
                  key={step}
                  className={`step-pill ${
                    step === incident.status
                      ? "current"
                      : currentStepIdx > idx
                        ? "done"
                        : ""
                  }`}
                >
                  {idx + 1}. {step}
                </span>
              ))}
            </div>

            <div className="form-grid" style={{ marginBottom: "16px" }}>
              <div>
                <strong>Status:</strong>{" "}
                <span
                  className={`badge badge-${(incident.status || "").toLowerCase()}`}
                >
                  {incident.status}
                </span>
              </div>
              <div>
                <strong>Priority / Severity:</strong>{" "}
                <span
                  className={`badge badge-priority-${(
                    incident.priority || derivePriority(incident.severity)
                  ).toLowerCase()}`}
                >
                  {incident.priority || derivePriority(incident.severity)}
                </span>{" "}
                {incident.severity}
              </div>
              <div>
                <strong>Reported (IST):</strong>{" "}
                {formatIstDateTime(incident.createdAt)} (
                {formatElapsedFromIso(incident.createdAt)} ago)
              </div>
              <div>
                <strong>People Affected:</strong> {incident.peopleAffected}
              </div>
              <div>
                <strong>Equipment Required:</strong>{" "}
                {(incident.requiredEquipment || []).join(", ") || "None"}
              </div>
              <div>
                <strong>Assigned Ambulance:</strong>{" "}
                {incident.assignedAmbulanceId || "None"}
              </div>
              <div>
                <strong>Requested / Assigned Hospital:</strong>{" "}
                {incident.assignedHospitalId || "None"} (
                {incident.hospitalRequestStatus || "NOT_REQUESTED"})
              </div>
              <div>
                <strong>Description:</strong> {incident.description}
              </div>
              {incident.hospitalRejectionReason && (
                <div>
                  <strong>Last Rejection Reason:</strong>{" "}
                  {incident.hospitalRejectionReason}
                </div>
              )}
            </div>

            <div className="threshold-bar">
              <span>
                <strong>Created:</strong> {formatIstDateTime(incident.createdAt)}
              </span>
              {incident.verifiedAt && (
                <span>
                  <strong>Verified:</strong>{" "}
                  {formatIstDateTime(incident.verifiedAt)}
                </span>
              )}
              {incident.ambulanceAssignedAt && (
                <span>
                  <strong>Dispatched:</strong>{" "}
                  {formatIstDateTime(incident.ambulanceAssignedAt)}
                </span>
              )}
              {incident.hospitalRequestedAt && (
                <span>
                  <strong>Hospital Req:</strong>{" "}
                  {formatIstDateTime(incident.hospitalRequestedAt)}
                </span>
              )}
              {incident.hospitalAcceptedAt && (
                <span>
                  <strong>Accepted:</strong>{" "}
                  {formatIstDateTime(incident.hospitalAcceptedAt)}
                </span>
              )}
              {incident.transportedAt && (
                <span>
                  <strong>Transported:</strong>{" "}
                  {formatIstDateTime(incident.transportedAt)}
                </span>
              )}
              {incident.completedAt && (
                <span>
                  <strong>Completed:</strong>{" "}
                  {formatIstDateTime(incident.completedAt)}
                </span>
              )}
            </div>

            {showResponderNav && (
              <div className="nav-banner">
                <div>
                  <strong style={{ fontSize: "14px", color: "#0f172a" }}>
                    Assigned Ambulance &amp; External Responder Navigation
                  </strong>
                  <div style={{ fontSize: "12px", color: "#475569", marginTop: "3px" }}>
                    Assigned Ambulance:{" "}
                    <code>{incident.assignedAmbulanceId}</code>
                    {incident.ambulanceAssignedAt && (
                      <>
                        {" "}
                        &middot; Dispatched:{" "}
                        <strong>
                          {formatIstDateTime(incident.ambulanceAssignedAt)}
                        </strong>
                      </>
                    )}
                  </div>
                  <div style={{ fontSize: "12px", color: "#475569", marginTop: "2px" }}>
                    Destination:{" "}
                    <code>
                      {formatCoord(incLat)}, {formatCoord(incLng)}
                    </code>
                  </div>
                  <div style={{ fontSize: "11px", color: "#64748b", marginTop: "3px" }}>
                    Opens external Google Maps driving directions (app on mobile,
                    browser on desktop). This prototype does not perform live
                    ambulance GPS tracking.
                  </div>
                </div>
                <div className="btn-row">
                  <a
                    href={directionsUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn btn-primary"
                    style={{ textDecoration: "none" }}
                  >
                    Navigate to Incident
                  </a>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    disabled={locatingOrigin}
                    onClick={handleNavigateWithCurrentOrigin}
                  >
                    {locatingOrigin
                      ? "Getting Origin..."
                      : "Navigate from My Current Location"}
                  </button>
                </div>
              </div>
            )}

            {showHospitalNav && (
              <div
                className="nav-banner"
                style={{
                  background: "#f0fdf4",
                  borderColor: "#bbf7d0",
                }}
              >
                <div>
                  <strong style={{ fontSize: "14px", color: "#14532d" }}>
                    Destination Hospital &amp; External Navigation (Google Maps)
                  </strong>
                  <div style={{ fontSize: "12px", color: "#166534", marginTop: "3px" }}>
                    Hospital: <strong>{assignedHospital.name}</strong> (
                    <code>{assignedHospital.hospitalId}</code>) &middot; Beds
                    Reserved:{" "}
                    <strong>
                      {incident.bedReservation?.bedsReserved ?? "—"}
                    </strong>
                  </div>
                  <div style={{ fontSize: "12px", color: "#166534", marginTop: "2px" }}>
                    Hospital Coordinates:{" "}
                    <code>
                      {formatCoord(hospLat)}, {formatCoord(hospLng)}
                    </code>
                  </div>
                  <div style={{ fontSize: "11px", color: "#475569", marginTop: "3px" }}>
                    Opens external Google Maps driving directions to the
                    confirmed hospital (app on mobile, browser on desktop). Live
                    GPS tracking is not implemented.
                  </div>
                </div>
                <div className="btn-row">
                  <a
                    href={hospitalDirectionsUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn btn-success"
                    style={{ textDecoration: "none" }}
                  >
                    Navigate to Hospital
                  </a>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    disabled={locatingOrigin}
                    onClick={() =>
                      openExternalDirectionsWithOrigin(hospLat, hospLng)
                    }
                  >
                    {locatingOrigin
                      ? "Getting Origin..."
                      : "Navigate to Hospital from My Location"}
                  </button>
                </div>
              </div>
            )}

            <div style={{ marginBottom: "18px" }}>
              <CoordinationMap
                incident={incident}
                ambulances={ambulances}
                hospitals={hospitals}
              />
            </div>

            {isOperator && incident.status === "CREATED" && (
              <div style={{ marginBottom: "16px" }}>
                <h4 style={{ marginBottom: "10px", fontSize: "14px" }}>
                  Step 2: Incident Inspection — Start Review
                </h4>
                <button
                  type="button"
                  className="btn btn-primary"
                  disabled={busy}
                  onClick={() =>
                    runAction(
                      () => api.startReview(incident.incidentId),
                      "Incident moved to UNDER_REVIEW."
                    )
                  }
                >
                  Start Review
                </button>
              </div>
            )}

            {isOperator && incident.status === "UNDER_REVIEW" && (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "12px",
                  marginBottom: "16px",
                }}
              >
                <h4 style={{ fontSize: "14px" }}>
                  Step 3: Verify or Reject Incident
                </h4>
                <div className="field">
                  <label>Verification Remarks / Rejection Reason</label>
                  <input
                    type="text"
                    value={reviewRemarks}
                    onChange={(e) => setReviewRemarks(e.target.value)}
                    placeholder="Record verification notes or rejection reason..."
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
                          api.verifyIncident(incident.incidentId, {
                            decision: "VERIFIED",
                            remarks: reviewRemarks || undefined,
                          }),
                        "Incident VERIFIED. You may now manually assign an ambulance."
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
                          api.verifyIncident(incident.incidentId, {
                            decision: "REJECTED",
                            remarks:
                              reviewRemarks || "Rejected by Resource Operator",
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

            {!isOperator &&
              ["CREATED", "UNDER_REVIEW"].includes(incident.status) && (
                <div className="alert alert-info">
                  Awaiting inspection and verification by a{" "}
                  <strong>RESOURCE_OPERATOR</strong>.
                </div>
              )}

            {isOperator && incident.status === "VERIFIED" && (
              <div>
                <h4 style={{ marginBottom: "10px", fontSize: "14px" }}>
                  Step 4: Manually Select an Available Ambulance (Haversine Distance Ranked)
                </h4>
                {loadingCands ? (
                  <div className="empty-state">Calculating distances...</div>
                ) : !candidates || candidates.ambulances.length === 0 ? (
                  <div className="empty-state">No ambulances registered.</div>
                ) : (
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Vehicle &amp; Coordinates</th>
                          <th>Status</th>
                          <th>Distance</th>
                          <th>Suitability</th>
                          <th>Equipment</th>
                          <th>Action</th>
                        </tr>
                      </thead>
                      <tbody>
                        {candidates.ambulances.map((item) => {
                          const amb = item.ambulance;
                          return (
                            <tr key={amb.ambulanceId}>
                              <td>
                                <strong>{amb.registrationNumber}</strong>
                                <div style={{ fontSize: "11px", color: "#64748b" }}>
                                  {amb.ambulanceId} &middot;{" "}
                                  {formatCoord(amb.latitude)},{" "}
                                  {formatCoord(amb.longitude)}
                                </div>
                              </td>
                              <td>
                                <span
                                  className={`badge badge-${(amb.status || "").toLowerCase()}`}
                                >
                                  {amb.status}
                                </span>
                              </td>
                              <td>{item.distanceKm} km</td>
                              <td>
                                {item.eligible ? (
                                  <span className="badge badge-available">
                                    Suitable
                                  </span>
                                ) : (
                                  <div>
                                    <span className="badge badge-rejected">
                                      Unsuitable
                                    </span>
                                    {item.unsuitabilityReason && (
                                      <div
                                        style={{
                                          fontSize: "11px",
                                          color: "#b91c1c",
                                          marginTop: "3px",
                                        }}
                                      >
                                        {item.unsuitabilityReason}
                                      </div>
                                    )}
                                  </div>
                                )}
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
                              <td>
                                <button
                                  type="button"
                                  className="btn btn-primary btn-sm"
                                  disabled={busy || !item.eligible}
                                  onClick={() =>
                                    runAction(
                                      () =>
                                        api.assignAmbulance(
                                          incident.incidentId,
                                          amb.ambulanceId
                                        ),
                                      `Ambulance ${amb.registrationNumber} dispatched atomically.`
                                    )
                                  }
                                >
                                  Assign Ambulance
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
            )}

            {isOperator &&
              ["AMBULANCE_ASSIGNED", "HOSPITAL_REJECTED"].includes(
                incident.status
              ) && (() => {
                const defaultBeds = Math.max(
                  1,
                  Number(incident.peopleAffected || 1)
                );
                const bedsInputVal =
                  bedsInputByIncident[incident.incidentId] ??
                  String(defaultBeds);
                const parsedBeds = Number(bedsInputVal);
                const validBeds =
                  Number.isInteger(parsedBeds) && parsedBeds > 0;

                return (
                  <div>
                    <div
                      className="card-header"
                      style={{ marginTop: "8px", marginBottom: "10px" }}
                    >
                      <div>
                        <h4 style={{ fontSize: "14px" }}>
                          Step 5: Select Hospital &amp; Atomically Reserve Beds
                        </h4>
                        <div style={{ fontSize: "12px", color: "#64748b" }}>
                          Default required beds ={" "}
                          <strong>{incident.peopleAffected}</strong> (people
                          affected). Adjust below if needed.
                        </div>
                      </div>
                      <div className="btn-row">
                        <label
                          style={{
                            fontSize: "12px",
                            fontWeight: 600,
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "6px",
                          }}
                        >
                          Beds:
                          <input
                            type="number"
                            min="1"
                            step="1"
                            value={bedsInputVal}
                            onChange={(e) =>
                              setBedsInputByIncident((prev) => ({
                                ...prev,
                                [incident.incidentId]: e.target.value,
                              }))
                            }
                            style={{
                              width: "68px",
                              padding: "6px 8px",
                              border: "1px solid #cbd5e1",
                              borderRadius: "6px",
                              fontSize: "12px",
                            }}
                          />
                        </label>
                        <input
                          type="text"
                          placeholder="Filter facilities (e.g. ICU, TRAUMA)"
                          value={facilityFilter}
                          onChange={(e) => setFacilityFilter(e.target.value)}
                          style={{
                            padding: "6px 10px",
                            border: "1px solid #cbd5e1",
                            borderRadius: "6px",
                            fontSize: "12px",
                          }}
                        />
                        <button
                          type="button"
                          className="btn btn-secondary btn-sm"
                          onClick={() =>
                            loadCandidates(
                              incident.incidentId,
                              facilityFilter,
                              validBeds ? parsedBeds : null
                            )
                          }
                        >
                          Apply Filter
                        </button>
                      </div>
                    </div>
                    {loadingCands ? (
                      <div className="empty-state">Evaluating hospitals...</div>
                    ) : !candidates || candidates.hospitals.length === 0 ? (
                      <div className="empty-state">No hospitals registered.</div>
                    ) : (
                      <div className="table-wrap">
                        <table>
                          <thead>
                            <tr>
                              <th>Hospital</th>
                              <th>Status</th>
                              <th>Distance</th>
                              <th>Beds (Avail / Total)</th>
                              <th>Suitability</th>
                              <th>Facilities</th>
                              <th>Action</th>
                            </tr>
                          </thead>
                          <tbody>
                            {candidates.hospitals.map((item) => {
                              const h = item.hospital;
                              const hasEnoughForInput =
                                validBeds &&
                                Number(h.availableBeds) >= parsedBeds;
                              const canReserve =
                                h.status === "ACTIVE" && hasEnoughForInput;
                              return (
                                <tr key={h.hospitalId}>
                                  <td>
                                    <strong>{h.name}</strong>
                                    <div
                                      style={{
                                        fontSize: "11px",
                                        color: "#64748b",
                                      }}
                                    >
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
                                  <td>{item.distanceKm} km</td>
                                  <td>
                                    <strong>{h.availableBeds}</strong> /{" "}
                                    {h.totalBeds}
                                  </td>
                                  <td>
                                    {canReserve && item.facilityMatch ? (
                                      <span className="badge badge-available">
                                        Suitable
                                      </span>
                                    ) : (
                                      <div>
                                        <span className="badge badge-rejected">
                                          Unsuitable
                                        </span>
                                        <div
                                          style={{
                                            fontSize: "11px",
                                            color: "#b91c1c",
                                            marginTop: "2px",
                                          }}
                                        >
                                          {h.status !== "ACTIVE"
                                            ? `Status is ${h.status}`
                                            : !hasEnoughForInput
                                              ? `Needs ${parsedBeds} bed(s), only ${h.availableBeds} available`
                                              : item.unsuitabilityReason}
                                        </div>
                                      </div>
                                    )}
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
                                  <td>
                                    <button
                                      type="button"
                                      className="btn btn-primary btn-sm"
                                      disabled={busy || !canReserve}
                                      onClick={() =>
                                        runAction(
                                          () =>
                                            api.requestHospital(
                                              incident.incidentId,
                                              h.hospitalId,
                                              parsedBeds
                                            ),
                                          `Reserved ${parsedBeds} bed(s) at ${h.name} (status: RESERVED).`
                                        )
                                      }
                                    >
                                      Reserve {validBeds ? parsedBeds : ""} Bed(s)
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
                );
              })()}

            {incident.bedReservation && (
              <div className="threshold-bar" style={{ marginTop: "14px" }}>
                <span>
                  <strong>Active Reservation:</strong>{" "}
                  <code>{incident.bedReservation.reservationId}</code>
                </span>
                <span>
                  <strong>Hospital:</strong>{" "}
                  <code>{incident.bedReservation.hospitalId}</code>
                </span>
                <span>
                  <strong>Beds Reserved:</strong>{" "}
                  {incident.bedReservation.bedsReserved}
                </span>
                <span>
                  <strong>Status:</strong>{" "}
                  <span
                    className={`badge badge-${(incident.bedReservation.status || "").toLowerCase()}`}
                  >
                    {incident.bedReservation.status}
                  </span>
                </span>
                {incident.bedReservation.reason && (
                  <span>
                    <strong>Reason:</strong> {incident.bedReservation.reason}
                  </span>
                )}
              </div>
            )}

            {isOperator && incident.status === "HOSPITAL_REQUESTED" && (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "10px",
                  marginTop: "10px",
                }}
              >
                <div className="field">
                  <label>Rejection / Cancellation Reason (optional)</label>
                  <input
                    type="text"
                    value={rejectionReason}
                    onChange={(e) => setRejectionReason(e.target.value)}
                    placeholder="e.g. Trauma bay full or operator rerouting"
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
                          api.recordHospitalDecision(incident.incidentId, {
                            decision: "ACCEPTED",
                          }),
                        "Hospital admission CONFIRMED (reserved beds confirmed)."
                      )
                    }
                  >
                    Step 6: Confirm Admission
                  </button>
                  <button
                    type="button"
                    className="btn btn-danger"
                    disabled={busy}
                    onClick={() =>
                      runAction(
                        () =>
                          api.recordHospitalDecision(incident.incidentId, {
                            decision: "REJECTED",
                            reason: rejectionReason || "Rejected by hospital",
                          }),
                        "Hospital admission REJECTED and reserved beds released."
                      )
                    }
                  >
                    Reject Admission (Release Beds)
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    disabled={busy}
                    onClick={() =>
                      runAction(
                        () =>
                          api.cancelHospitalReservation(
                            incident.incidentId,
                            rejectionReason || "Cancelled by Resource Operator"
                          ),
                        "Reservation cancelled and beds released. You may select another hospital."
                      )
                    }
                  >
                    Cancel Reservation (Release Beds)
                  </button>
                </div>
              </div>
            )}

            {incident.status === "HOSPITAL_REQUESTED" && !isOperator && (
              <div className="alert alert-info">
                Waiting for a <strong>RESOURCE_OPERATOR</strong> to accept or
                reject the admission request for hospital{" "}
                <code>{incident.assignedHospitalId}</code>.
              </div>
            )}

            {isOperator && incident.status === "HOSPITAL_ACCEPTED" && (
              <button
                type="button"
                className="btn btn-primary"
                disabled={busy}
                onClick={() =>
                  runAction(
                    () => api.markTransported(incident.incidentId),
                    "Patient transport recorded (PATIENT_TRANSPORTED)."
                  )
                }
              >
                Step 7: Record Patient Transported
              </button>
            )}

            {isOperator && incident.status === "PATIENT_TRANSPORTED" && (
              <button
                type="button"
                className="btn btn-success"
                disabled={busy}
                onClick={() =>
                  runAction(
                    () => api.completeIncident(incident.incidentId),
                    "Incident COMPLETED and assigned ambulance released to AVAILABLE."
                  )
                }
              >
                Step 8: Mark Incident Completed
              </button>
            )}

            {incident.status === "COMPLETED" && (
              <div className="alert alert-success">
                <span>
                  This incident has been completed and its assigned ambulance
                  has been returned to AVAILABLE status.
                </span>
                {isOperator && !incident.isArchived && (
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    disabled={busy}
                    onClick={() => {
                      if (
                        window.confirm(
                          `Archive completed incident ${incident.incidentId.slice(0, 12)}?`
                        )
                      ) {
                        runAction(
                          () => api.archiveIncident(incident.incidentId),
                          "Incident archived and moved to Archived Incidents."
                        );
                      }
                    }}
                  >
                    Archive Completed Incident
                  </button>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </>
  );
}
