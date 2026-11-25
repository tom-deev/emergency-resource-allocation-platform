import L from "leaflet";

// Pune, Maharashtra, India (matching existing project demo coordinates)
export const DEFAULT_MAP_CENTER = {
  lat: 18.5204,
  lng: 73.8567,
};

export const DEFAULT_MAP_ZOOM = 13;

export const OSM_TILE_URL = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
export const OSM_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

export function parseCoordinate(value) {
  if (value === "" || value === null || value === undefined) return null;
  const num = Number(value);
  return Number.isFinite(num) ? num : null;
}

export function isValidCoordinates(lat, lng) {
  return (
    typeof lat === "number" &&
    typeof lng === "number" &&
    Number.isFinite(lat) &&
    Number.isFinite(lng) &&
    lat >= -90 &&
    lat <= 90 &&
    lng >= -180 &&
    lng <= 180
  );
}

export function formatCoord(value) {
  const num = parseCoordinate(value);
  return num === null ? "—" : num.toFixed(6);
}

export function buildGoogleMapsPlaceUrl(lat, lng) {
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
    `${lat},${lng}`
  )}`;
}

export function buildGoogleMapsDirectionsUrl(destLat, destLng, origin = null) {
  let url = `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(
    `${destLat},${destLng}`
  )}&travelmode=driving`;

  if (
    origin &&
    isValidCoordinates(origin.lat, origin.lng)
  ) {
    url += `&origin=${encodeURIComponent(`${origin.lat},${origin.lng}`)}`;
  }

  return url;
}

function createPinIcon({ fill, stroke = "#ffffff", label = "", size = 30, ring = false }) {
  const ringMarkup = ring
    ? `<circle cx="16" cy="14" r="13" fill="none" stroke="${fill}" stroke-width="2.5" stroke-opacity="0.45" />`
    : "";

  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size + 8}" viewBox="0 0 32 40">
      ${ringMarkup}
      <path d="M16 2C9.4 2 4 7.4 4 14c0 9.4 12 24 12 24s12-14.6 12-24C28 7.4 22.6 2 16 2z"
            fill="${fill}" stroke="${stroke}" stroke-width="2.2" />
      <text x="16" y="18" text-anchor="middle" font-size="11" font-weight="700"
            font-family="Inter, Arial, sans-serif" fill="#ffffff">${label}</text>
    </svg>
  `.trim();

  return L.divIcon({
    html: svg,
    className: "erap-map-pin",
    iconSize: [size, size + 8],
    iconAnchor: [size / 2, size + 6],
    popupAnchor: [0, -(size + 2)],
  });
}

export const MAP_ICONS = {
  incident: createPinIcon({ fill: "#dc2626", label: "!", size: 32, ring: true }),
  ambulanceAvailable: createPinIcon({ fill: "#2563eb", label: "A", size: 28 }),
  ambulanceAssigned: createPinIcon({ fill: "#7c3aed", label: "★", size: 32, ring: true }),
  ambulanceBusy: createPinIcon({ fill: "#d97706", label: "A", size: 26 }),
  hospital: createPinIcon({ fill: "#16a34a", label: "H", size: 28 }),
};
