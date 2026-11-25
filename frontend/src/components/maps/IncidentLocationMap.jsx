import { MapContainer, Marker, Popup, TileLayer } from "react-leaflet";
import {
  buildGoogleMapsPlaceUrl,
  DEFAULT_MAP_ZOOM,
  formatCoord,
  isValidCoordinates,
  MAP_ICONS,
  OSM_ATTRIBUTION,
  OSM_TILE_URL,
  parseCoordinate,
} from "../../utils/maps";
import { MapRecenter, MapResizeFix } from "./MapHelpers";

export default function IncidentLocationMap({ incident }) {
  const lat = parseCoordinate(incident?.latitude);
  const lng = parseCoordinate(incident?.longitude);

  if (!incident || !isValidCoordinates(lat, lng)) {
    return (
      <div className="empty-state">
        Valid coordinates are not available for this incident.
      </div>
    );
  }

  const googleMapsUrl = buildGoogleMapsPlaceUrl(lat, lng);

  return (
    <div className="map-section">
      <div className="map-toolbar">
        <div>
          <strong style={{ fontSize: "13px" }}>Incident Location Map</strong>
          <div style={{ fontSize: "12px", color: "#64748b" }}>
            Coordinates:{" "}
            <code>
              {formatCoord(lat)}, {formatCoord(lng)}
            </code>
          </div>
        </div>
        <a
          href={googleMapsUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="btn btn-secondary btn-sm"
          style={{ textDecoration: "none" }}
        >
          Open in Google Maps (External)
        </a>
      </div>

      <div className="map-frame map-frame-detail">
        <MapContainer
          center={[lat, lng]}
          zoom={DEFAULT_MAP_ZOOM + 1}
          scrollWheelZoom={true}
          className="leaflet-container-responsive"
        >
          <TileLayer attribution={OSM_ATTRIBUTION} url={OSM_TILE_URL} />
          <MapResizeFix />
          <MapRecenter lat={lat} lng={lng} zoom={14} />
          <Marker position={[lat, lng]} icon={MAP_ICONS.incident}>
            <Popup>
              <strong>Incident {incident.incidentId.slice(0, 12)}</strong>
              <br />
              Type: {incident.type}
              <br />
              Severity: <strong>{incident.severity}</strong>
              <br />
              Status: {incident.status}
            </Popup>
          </Marker>
        </MapContainer>
      </div>
    </div>
  );
}
