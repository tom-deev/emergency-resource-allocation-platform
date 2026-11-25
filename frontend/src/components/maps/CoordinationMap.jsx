import { useMemo } from "react";
import { MapContainer, Marker, Popup, TileLayer } from "react-leaflet";
import {
  DEFAULT_MAP_CENTER,
  DEFAULT_MAP_ZOOM,
  isValidCoordinates,
  MAP_ICONS,
  OSM_ATTRIBUTION,
  OSM_TILE_URL,
  parseCoordinate,
} from "../../utils/maps";
import { MapFitBounds, MapResizeFix } from "./MapHelpers";

export default function CoordinationMap({ incident, ambulances, hospitals }) {
  const incLat = parseCoordinate(incident?.latitude);
  const incLng = parseCoordinate(incident?.longitude);
  const hasIncidentCoords = isValidCoordinates(incLat, incLng);

  const visibleAmbulances = useMemo(() => {
    return (ambulances || []).filter((amb) => {
      const lat = parseCoordinate(amb.latitude);
      const lng = parseCoordinate(amb.longitude);
      if (!isValidCoordinates(lat, lng)) return false;
      // Show all AVAILABLE ambulances plus the incident's assigned ambulance
      return (
        amb.status === "AVAILABLE" ||
        amb.ambulanceId === incident?.assignedAmbulanceId
      );
    });
  }, [ambulances, incident?.assignedAmbulanceId]);

  const visibleHospitals = useMemo(() => {
    return (hospitals || []).filter((h) => {
      const lat = parseCoordinate(h.latitude);
      const lng = parseCoordinate(h.longitude);
      return isValidCoordinates(lat, lng);
    });
  }, [hospitals]);

  const boundsPoints = useMemo(() => {
    const pts = [];
    if (hasIncidentCoords) pts.push([incLat, incLng]);
    visibleAmbulances.forEach((a) =>
      pts.push([parseCoordinate(a.latitude), parseCoordinate(a.longitude)])
    );
    visibleHospitals.forEach((h) =>
      pts.push([parseCoordinate(h.latitude), parseCoordinate(h.longitude)])
    );
    return pts;
  }, [hasIncidentCoords, incLat, incLng, visibleAmbulances, visibleHospitals]);

  const initialCenter = hasIncidentCoords
    ? [incLat, incLng]
    : [DEFAULT_MAP_CENTER.lat, DEFAULT_MAP_CENTER.lng];

  return (
    <div className="map-section">
      <div className="map-toolbar">
        <div>
          <strong style={{ fontSize: "14px" }}>
            Operational Resource Map (Read-Only Visualization)
          </strong>
          <div style={{ fontSize: "12px", color: "#64748b" }}>
            Click any marker to inspect details. Resource assignment remains
            strictly manual below.
          </div>
        </div>
        <div className="map-legend">
          <span className="legend-item">
            <span className="legend-dot" style={{ background: "#dc2626" }} />
            Incident
          </span>
          <span className="legend-item">
            <span className="legend-dot" style={{ background: "#2563eb" }} />
            Available Ambulance
          </span>
          <span className="legend-item">
            <span className="legend-dot" style={{ background: "#7c3aed" }} />
            Assigned Ambulance
          </span>
          <span className="legend-item">
            <span className="legend-dot" style={{ background: "#16a34a" }} />
            Hospital
          </span>
        </div>
      </div>

      <div className="map-frame map-frame-coord">
        <MapContainer
          center={initialCenter}
          zoom={DEFAULT_MAP_ZOOM}
          scrollWheelZoom={true}
          className="leaflet-container-responsive"
        >
          <TileLayer attribution={OSM_ATTRIBUTION} url={OSM_TILE_URL} />
          <MapResizeFix />
          <MapFitBounds points={boundsPoints} />

          {hasIncidentCoords && (
            <Marker position={[incLat, incLng]} icon={MAP_ICONS.incident}>
              <Popup>
                <strong>Incident: {incident.incidentId.slice(0, 12)}</strong>
                <br />
                Type: {incident.type}
                <br />
                Severity: <strong>{incident.severity}</strong>
                <br />
                Status: {incident.status}
              </Popup>
            </Marker>
          )}

          {visibleAmbulances.map((amb) => {
            const isAssigned = amb.ambulanceId === incident?.assignedAmbulanceId;
            const lat = parseCoordinate(amb.latitude);
            const lng = parseCoordinate(amb.longitude);
            return (
              <Marker
                key={amb.ambulanceId}
                position={[lat, lng]}
                icon={
                  isAssigned
                    ? MAP_ICONS.ambulanceAssigned
                    : MAP_ICONS.ambulanceAvailable
                }
              >
                <Popup>
                  <strong>
                    {amb.registrationNumber}
                    {isAssigned ? " (ASSIGNED)" : ""}
                  </strong>
                  <br />
                  Status: {amb.status}
                  <br />
                  Equipment:{" "}
                  {(amb.equipment || []).length > 0
                    ? amb.equipment.join(", ")
                    : "None listed"}
                </Popup>
              </Marker>
            );
          })}

          {visibleHospitals.map((h) => {
            const lat = parseCoordinate(h.latitude);
            const lng = parseCoordinate(h.longitude);
            const isSelected = h.hospitalId === incident?.assignedHospitalId;
            return (
              <Marker
                key={h.hospitalId}
                position={[lat, lng]}
                icon={MAP_ICONS.hospital}
              >
                <Popup>
                  <strong>
                    {h.name}
                    {isSelected ? " (REQUESTED/ASSIGNED)" : ""}
                  </strong>
                  <br />
                  Beds: <strong>{h.availableBeds}</strong> / {h.totalBeds} (
                  {h.status})
                  <br />
                  Facilities:{" "}
                  {(h.facilities || []).length > 0
                    ? h.facilities.join(", ")
                    : "None listed"}
                </Popup>
              </Marker>
            );
          })}
        </MapContainer>
      </div>
    </div>
  );
}
