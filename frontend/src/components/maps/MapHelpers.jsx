import { useEffect } from "react";
import { useMap } from "react-leaflet";
import { isValidCoordinates } from "../../utils/maps";

/**
 * Ensures Leaflet recalculates tile dimensions when containers resize,
 * tabs switch, or mobile viewports rotate.
 */
export function MapResizeFix() {
  const map = useMap();

  useEffect(() => {
    const container = map.getContainer();
    const timer = setTimeout(() => {
      map.invalidateSize();
    }, 120);

    let observer;
    if (typeof ResizeObserver !== "undefined" && container) {
      observer = new ResizeObserver(() => {
        map.invalidateSize();
      });
      observer.observe(container);
    }

    const handleResize = () => map.invalidateSize();
    window.addEventListener("resize", handleResize);

    return () => {
      clearTimeout(timer);
      if (observer) observer.disconnect();
      window.removeEventListener("resize", handleResize);
    };
  }, [map]);

  return null;
}

/**
 * Smoothly re-centers the map when external coordinates change.
 */
export function MapRecenter({ lat, lng, zoom }) {
  const map = useMap();

  useEffect(() => {
    if (!isValidCoordinates(lat, lng)) return;
    map.setView([lat, lng], zoom ?? map.getZoom(), { animate: true });
  }, [map, lat, lng, zoom]);

  return null;
}

/**
 * Fits map bounds around a list of [lat, lng] points with comfortable padding.
 */
export function MapFitBounds({ points }) {
  const map = useMap();

  useEffect(() => {
    const validPoints = (points || []).filter(
      (pt) => Array.isArray(pt) && isValidCoordinates(pt[0], pt[1])
    );
    if (validPoints.length === 0) return;

    if (validPoints.length === 1) {
      map.setView(validPoints[0], 14, { animate: true });
    } else {
      map.fitBounds(validPoints, { padding: [36, 36], maxZoom: 15 });
    }
  }, [map, points]);

  return null;
}
