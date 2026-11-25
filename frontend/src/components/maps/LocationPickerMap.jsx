import { useState } from "react";
import { MapContainer, Marker, Popup, TileLayer, useMapEvents } from "react-leaflet";
import {
  DEFAULT_MAP_CENTER,
  DEFAULT_MAP_ZOOM,
  formatCoord,
  isValidCoordinates,
  MAP_ICONS,
  OSM_ATTRIBUTION,
  OSM_TILE_URL,
  parseCoordinate,
} from "../../utils/maps";
import { MapRecenter, MapResizeFix } from "./MapHelpers";

function MapClickSelector({ onSelect }) {
  useMapEvents({
    click(event) {
      onSelect(event.latlng.lat, event.latlng.lng);
    },
  });
  return null;
}

export default function LocationPickerMap({ latitude, longitude, onChange }) {
  const [locating, setLocating] = useState(false);
  const [geoMessage, setGeoMessage] = useState("");
  const [geoError, setGeoError] = useState("");

  const parsedLat = parseCoordinate(latitude);
  const parsedLng = parseCoordinate(longitude);
  const hasValidCoords = isValidCoordinates(parsedLat, parsedLng);

  const markerLat = hasValidCoords ? parsedLat : DEFAULT_MAP_CENTER.lat;
  const markerLng = hasValidCoords ? parsedLng : DEFAULT_MAP_CENTER.lng;

  function updateCoords(lat, lng) {
    setGeoError("");
    onChange(Number(lat.toFixed(6)), Number(lng.toFixed(6)));
  }

  function handleUseMyLocation() {
    setGeoError("");
    setGeoMessage("");

    if (!navigator.geolocation) {
      setGeoError(
        "Geolocation is not supported by this browser. Click the map or enter coordinates manually."
      );
      return;
    }

    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude: lat, longitude: lng } = position.coords;
        updateCoords(lat, lng);
        setGeoMessage("Current browser location applied.");
        setLocating(false);
      },
      (err) => {
        if (err.code === err.PERMISSION_DENIED) {
          setGeoError(
            "Location permission was denied. You can click the map, drag the pin, or enter coordinates manually."
          );
        } else {
          setGeoError(
            "Unable to determine your current location. Please select a point on the map or enter coordinates manually."
          );
        }
        setLocating(false);
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }

  return (
    <div className="map-section">
      <div className="map-toolbar">
        <div>
          <strong style={{ fontSize: "13px" }}>
            Select Incident Location on Map
          </strong>
          <div style={{ fontSize: "12px", color: "#64748b" }}>
            Click anywhere on the map or drag the red marker. Selected:{" "}
            <code>
              {formatCoord(markerLat)}, {formatCoord(markerLng)}
            </code>
          </div>
        </div>
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={handleUseMyLocation}
          disabled={locating}
        >
          {locating ? "Locating..." : "Use My Current Location"}
        </button>
      </div>

      {geoError && <div className="alert alert-error">{geoError}</div>}
      {geoMessage && <div className="alert alert-success">{geoMessage}</div>}

      <div className="map-frame map-frame-picker">
        <MapContainer
          center={[markerLat, markerLng]}
          zoom={DEFAULT_MAP_ZOOM}
          scrollWheelZoom={true}
          className="leaflet-container-responsive"
        >
          <TileLayer attribution={OSM_ATTRIBUTION} url={OSM_TILE_URL} />
          <MapResizeFix />
          <MapRecenter lat={markerLat} lng={markerLng} />
          <MapClickSelector onSelect={updateCoords} />
          <Marker
            position={[markerLat, markerLng]}
            icon={MAP_ICONS.incident}
            draggable={true}
            eventHandlers={{
              dragend(e) {
                const pos = e.target.getLatLng();
                updateCoords(pos.lat, pos.lng);
              },
            }}
          >
            <Popup>
              <strong>Selected Incident Location</strong>
              <br />
              Lat: {formatCoord(markerLat)}
              <br />
              Lng: {formatCoord(markerLng)}
              <br />
              <em>Drag marker to adjust</em>
            </Popup>
          </Marker>
        </MapContainer>
      </div>
    </div>
  );
}
