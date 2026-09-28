/**
 * Frontend configuration.
 *
 * CESIUM_ION_TOKEN is OPTIONAL. Leave it empty to run entirely key-free
 * (OpenStreetMap imagery + ellipsoid terrain). To enable Cesium World
 * Terrain and Cesium OSM Buildings, create a free account at
 * https://ion.cesium.com/ and paste your default access token here.
 * The token is a public client-side token by design (restrict it to your
 * deployed domain in the ion dashboard).
 */
const runtimeApiBase = typeof window === "undefined"
  ? "http://localhost:8000"
  : (window.location.port === "5500" ? "http://localhost:8000" : window.location.origin);

export const CONFIG = {
  // Docker deployment uses the same origin through the web proxy. The original
  // lightweight local server on port 5500 continues to use port 8000 directly.
  API_BASE_URL: runtimeApiBase,

  // Optional Cesium ion token (see note above).
  CESIUM_ION_TOKEN: "",

  // Study area: Islamabad, Pakistan
  STUDY_AREA: {
    longitude: 73.0479,
    latitude: 33.6844,
    boundingBox: { west: 72.80, south: 33.60, east: 73.25, north: 33.82 },
  },

  // Default camera: tilted view over central Islamabad
  HOME_CAMERA: {
    longitude: 73.0479,
    latitude: 33.6844,
    height: 13500,         // metres
    heading: 10,           // degrees
    pitch: -40,            // degrees
  },

  // Refresh intervals (ms)
  WEATHER_REFRESH_MS: 10 * 60 * 1000,   // 10 minutes
  SIMULATION_REFRESH_MS: 30 * 1000,     // 30 seconds
};
