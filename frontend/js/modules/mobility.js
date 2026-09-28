/**
 * Urban mobility tool: nearest-facility search + route planning.
 * Uses /api/nearest (PostGIS KNN + geodesic re-rank) and /api/route (OSRM).
 */
import { apiGet } from "./api.js";
import { pickOnMap } from "./mappick.js";

/* global Cesium */

const FACILITY_OPTIONS = [
  ["hospital", "Hospital / clinic"],
  ["police_station", "Police station"],
  ["fire_station", "Fire station"],
  ["fuel_station", "Fuel station"],
  ["ev_charging", "EV charging station"],
  ["parking", "Parking"],
  ["bus_stop", "Bus stop"],
  ["railway_station", "Railway station"],
];

export function formatDistance(m) {
  return m >= 1000 ? `${(m / 1000).toFixed(2)} km` : `${Math.round(m)} m`;
}

export function formatDuration(s) {
  const min = Math.round(s / 60);
  return min < 60 ? `${min} min` : `${Math.floor(min / 60)} h ${min % 60} min`;
}

export function routePositions(geometry) {
  // GeoJSON LineString -> flat [lon, lat, ...] for Cartesian3.fromDegreesArray
  return geometry.coordinates.flatMap(([lon, lat]) => [lon, lat]);
}

export function initMobilityTool(viewer) {
  const source = new Cesium.CustomDataSource("mobility-tool");
  viewer.dataSources.add(source);

  const select = document.getElementById("nearest-type");
  select.innerHTML = FACILITY_OPTIONS
    .map(([v, t]) => `<option value="${v}">${t}</option>`)
    .join("");

  const pickBtn = document.getElementById("nearest-pick");
  const resultsEl = document.getElementById("nearest-results");
  let origin = null;

  function clearGraphics() {
    source.entities.removeAll();
    viewer.scene.requestRender();
  }

  function addOriginMarker(lon, lat) {
    source.entities.add({
      position: Cesium.Cartesian3.fromDegrees(lon, lat),
      point: {
        pixelSize: 12,
        color: Cesium.Color.fromCssColorString("#35c4a2"),
        outlineColor: Cesium.Color.WHITE,
        outlineWidth: 2,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
      label: {
        text: "Origin",
        font: "13px sans-serif",
        pixelOffset: new Cesium.Cartesian2(0, -22),
        fillColor: Cesium.Color.WHITE,
        showBackground: true,
        backgroundColor: Cesium.Color.fromCssColorString("#131a2c").withAlpha(0.8),
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
    });
  }

  function addResultMarker(r, rank) {
    source.entities.add({
      position: Cesium.Cartesian3.fromDegrees(r.lon, r.lat),
      point: {
        pixelSize: 10,
        color: Cesium.Color.fromCssColorString("#4f8ef7"),
        outlineColor: Cesium.Color.WHITE,
        outlineWidth: 2,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
      label: {
        text: `${rank}. ${r.name ?? "(unnamed)"} — ${formatDistance(r.distance_m)}`,
        font: "12px sans-serif",
        pixelOffset: new Cesium.Cartesian2(0, -20),
        fillColor: Cesium.Color.WHITE,
        showBackground: true,
        backgroundColor: Cesium.Color.fromCssColorString("#131a2c").withAlpha(0.8),
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
    });
  }

  function drawRoute(geometry, color = "#35c4a2") {
    source.entities.add({
      polyline: {
        positions: Cesium.Cartesian3.fromDegreesArray(routePositions(geometry)),
        width: 6,
        clampToGround: true,
        material: new Cesium.PolylineGlowMaterialProperty({
          color: Cesium.Color.fromCssColorString(color),
          glowPower: 0.25,
        }),
      },
    });
    viewer.scene.requestRender();
  }

  async function routeTo(r) {
    if (!origin) return;
    resultsEl.querySelector(".route-summary")?.remove();
    try {
      const data = await apiGet("/api/route", {
        from_lon: origin.lon, from_lat: origin.lat,
        to_lon: r.lon, to_lat: r.lat,
      });
      drawRoute(data.geometry);
      const summary = document.createElement("div");
      summary.className = "route-summary";
      summary.innerHTML = `
        <strong>Route to ${r.name ?? "(unnamed)"}</strong><br>
        Road distance: ${formatDistance(data.distance_m)} ·
        Est. time: ${formatDuration(data.duration_s)}<br>
        Straight line: ${formatDistance(data.straight_line_m)}
        <p class="panel-note">${data.duration_note}</p>`;
      resultsEl.appendChild(summary);
    } catch (err) {
      resultsEl.insertAdjacentHTML("beforeend",
        `<p class="tool-error route-summary">Routing failed: ${err.message}</p>`);
    }
  }

  pickBtn.addEventListener("click", async () => {
    pickBtn.classList.add("active");
    pickBtn.textContent = "Click on the map… (Esc to cancel)";
    try {
      origin = await pickOnMap(viewer);
      clearGraphics();
      addOriginMarker(origin.lon, origin.lat);
      resultsEl.innerHTML = "<p class='panel-note'>Searching…</p>";
      const data = await apiGet("/api/nearest", {
        lon: origin.lon, lat: origin.lat, type: select.value, n: 5,
      });
      if (!data.results.length) {
        resultsEl.innerHTML = "<p class='panel-note'>No facilities of this type found in the study area.</p>";
        return;
      }
      resultsEl.innerHTML = "";
      data.results.forEach((r, i) => {
        addResultMarker(r, i + 1);
        const row = document.createElement("div");
        row.className = "result-row";
        row.innerHTML = `
          <span class="result-rank">${i + 1}</span>
          <span class="result-name">${r.name ?? "(unnamed)"}</span>
          <span class="result-dist">${formatDistance(r.distance_m)}</span>
          <button class="mini-btn" title="Route here">Route</button>`;
        row.querySelector("button").addEventListener("click", () => routeTo(r));
        resultsEl.appendChild(row);
      });
      viewer.flyTo(source, { duration: 1.5 });
    } catch (err) {
      if (err.message !== "cancelled") {
        resultsEl.innerHTML = `<p class="tool-error">Search failed: ${err.message}</p>`;
      }
    } finally {
      pickBtn.classList.remove("active");
      pickBtn.textContent = "Pick location on map";
    }
  });
}
