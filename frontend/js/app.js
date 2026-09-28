/**
 * Application entry point — Islamabad 3D Urban Intelligence Digital Twin.
 * Wires the viewer, UI, and the smart-city layer registry together.
 */
import { CONFIG } from "./config.js";
import { createViewer, flyHome, faceNorth, toggleTilt } from "./modules/viewer.js";
import { initSidebarTabs, initFullscreen, initSearch, checkBackendStatus } from "./modules/ui.js";
import { initLayerControl } from "./modules/layers.js";
import { initMobilityTool } from "./modules/mobility.js";
import { initEmergencyTool } from "./modules/emergency.js";
import { initWeather } from "./modules/weather.js";
import { initDashboard } from "./modules/dashboard.js";
import { initSimulation } from "./modules/simulation.js";
import { initTimeViz } from "./modules/timeviz.js";
import { initAnalysisTools } from "./modules/analysis.js";
import { initQueryTool } from "./modules/query.js";
import { initMeasureTool } from "./modules/measure.js";

const viewer = createViewer();

// Camera controls
document.getElementById("btn-home").addEventListener("click", () => flyHome(viewer));
document.getElementById("btn-north").addEventListener("click", () => faceNorth(viewer));
document
  .getElementById("btn-2d3d")
  .addEventListener("click", (e) => toggleTilt(viewer, e.currentTarget));

// UI
initSidebarTabs();
initFullscreen();
initSearch(viewer);
checkBackendStatus();
setInterval(checkBackendStatus, 60 * 1000);

// Initial flight to Islamabad
flyHome(viewer, 3.5);

// Smart-city layers (Milestone 6): registry-driven layer control,
// lazy loading, per-kind styling, honest attribute inspection.
const layerManager = initLayerControl(viewer);

// GIS tools (Milestone 7): nearest facility search + emergency response
initMobilityTool(viewer);
initEmergencyTool(viewer);

// Weather card + analytics dashboard (Milestone 8)
initWeather();
initDashboard();

// Digital twin simulation overlays + time-based demo (Milestone 9)
initSimulation(viewer, layerManager);
initTimeViz(viewer);

// Advanced GIS analysis, spatial query, measurement (Milestone 10)
initAnalysisTools(viewer);
initQueryTool(viewer);
initMeasureTool(viewer);

// Expose for debugging in the browser console
window.__twin = { viewer, CONFIG, layerManager };
