/**
 * Cesium viewer initialisation and camera utilities.
 * Runs key-free by default: OpenStreetMap imagery + ellipsoid terrain.
 * If a Cesium ion token is configured, upgrades to World Terrain.
 */
import { CONFIG } from "../config.js";

/* global Cesium */

export function createViewer() {
  if (CONFIG.CESIUM_ION_TOKEN) {
    Cesium.Ion.defaultAccessToken = CONFIG.CESIUM_ION_TOKEN;
  }

  const viewer = new Cesium.Viewer("cesiumContainer", {
    baseLayer: new Cesium.ImageryLayer(
      new Cesium.OpenStreetMapImageryProvider({
        url: "https://tile.openstreetmap.org/",
      })
    ),
    baseLayerPicker: false,
    geocoder: false,           // custom search implemented instead
    homeButton: false,         // custom home button
    sceneModePicker: false,
    navigationHelpButton: false,
    animation: true,           // hidden via CSS until the time demo is active
    timeline: true,
    fullscreenButton: false,
    infoBox: true,
    selectionIndicator: true,
    requestRenderMode: true,
    maximumRenderTimeChange: Infinity,
  });

  // Upgrade to Cesium World Terrain when an ion token is available.
  if (CONFIG.CESIUM_ION_TOKEN) {
    Cesium.createWorldTerrainAsync()
      .then((terrain) => {
        viewer.terrainProvider = terrain;
        viewer.scene.requestRender();
      })
      .catch((err) => console.warn("World Terrain unavailable, using ellipsoid:", err));
  }

  viewer.scene.globe.depthTestAgainstTerrain = false;
  return viewer;
}

/** Fly the camera to the configured home view over Islamabad. */
export function flyHome(viewer, durationSeconds = 2.5) {
  const cam = CONFIG.HOME_CAMERA;
  viewer.camera.flyTo({
    destination: Cesium.Cartesian3.fromDegrees(cam.longitude, cam.latitude, cam.height),
    orientation: {
      heading: Cesium.Math.toRadians(cam.heading),
      pitch: Cesium.Math.toRadians(cam.pitch),
      roll: 0,
    },
    duration: durationSeconds,
  });
}

/** Fly to an arbitrary lon/lat with a sensible viewing height. */
export function flyToLocation(viewer, longitude, latitude, height = 1200) {
  viewer.camera.flyTo({
    destination: Cesium.Cartesian3.fromDegrees(longitude, latitude, height),
    orientation: {
      heading: 0,
      pitch: Cesium.Math.toRadians(-45),
      roll: 0,
    },
    duration: 2,
  });
}

/** Rotate camera to face north, keeping position. */
export function faceNorth(viewer) {
  viewer.camera.flyTo({
    destination: viewer.camera.position.clone(),
    orientation: {
      heading: 0,
      pitch: viewer.camera.pitch,
      roll: 0,
    },
    duration: 0.8,
  });
}

/** Toggle between a tilted 3D view and a top-down 2D-style view. */
export function toggleTilt(viewer, button) {
  const topDown = viewer.camera.pitch < Cesium.Math.toRadians(-80);
  const carto = viewer.camera.positionCartographic;
  viewer.camera.flyTo({
    destination: Cesium.Cartesian3.fromRadians(
      carto.longitude,
      carto.latitude,
      carto.height
    ),
    orientation: {
      heading: viewer.camera.heading,
      pitch: Cesium.Math.toRadians(topDown ? -35 : -90),
      roll: 0,
    },
    duration: 1,
  });
  if (button) button.textContent = topDown ? "3D" : "2D";
}
