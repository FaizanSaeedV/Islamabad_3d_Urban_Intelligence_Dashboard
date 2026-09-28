/**
 * Emergency response decision-support module.
 * User sets an incident location; the nearest hospital, police station and
 * fire station are found (PostGIS KNN + geodesic), each with an OSRM network
 * route: straight-line distance, road distance, and estimated travel time
 * (free-flow — clearly noted). Optimal routes are drawn in the 3D scene.
 */
import { apiGet } from "./api.js";
import { pickOnMap } from "./mappick.js";
import { formatDistance, formatDuration, routePositions } from "./mobility.js";

/* global Cesium */

const SERVICES = [
  { type: "hospital", label: "Hospital", color: "#e2604f", icon: "H" },
  { type: "police_station", label: "Police", color: "#5f7fe0", icon: "P" },
  { type: "fire_station", label: "Fire", color: "#e0a24f", icon: "F" },
];

export function initEmergencyTool(viewer) {
  const source = new Cesium.CustomDataSource("emergency-tool");
  viewer.dataSources.add(source);

  const pickBtn = document.getElementById("incident-pick");
  const resultsEl = document.getElementById("emergency-results");

  function marker(lon, lat, color, text, size = 12) {
    source.entities.add({
      position: Cesium.Cartesian3.fromDegrees(lon, lat),
      point: {
        pixelSize: size,
        color: Cesium.Color.fromCssColorString(color),
        outlineColor: Cesium.Color.WHITE,
        outlineWidth: 2,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
      label: {
        text,
        font: "13px sans-serif",
        pixelOffset: new Cesium.Cartesian2(0, -22),
        fillColor: Cesium.Color.WHITE,
        showBackground: true,
        backgroundColor: Cesium.Color.fromCssColorString("#131a2c").withAlpha(0.85),
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
    });
  }

  function drawRoute(geometry, color) {
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
  }

  async function respond(service, incident) {
    const card = document.createElement("div");
    card.className = "response-card";
    card.style.borderLeftColor = service.color;
    card.innerHTML = `<strong>${service.label}</strong><p class="panel-note">searching…</p>`;
    resultsEl.appendChild(card);

    try {
      const nearest = await apiGet("/api/nearest", {
        lon: incident.lon, lat: incident.lat, type: service.type, n: 1,
      });
      if (!nearest.results.length) {
        card.innerHTML = `<strong>${service.label}</strong>
          <p class="panel-note">No ${service.label.toLowerCase()} facility found in the study area.</p>`;
        return;
      }
      const facility = nearest.results[0];
      marker(facility.lon, facility.lat, service.color,
        `${service.icon}: ${facility.name ?? "(unnamed)"}`);

      let routeInfo = null;
      try {
        // Response route: from the facility TO the incident
        routeInfo = await apiGet("/api/route", {
          from_lon: facility.lon, from_lat: facility.lat,
          to_lon: incident.lon, to_lat: incident.lat,
        });
        drawRoute(routeInfo.geometry, service.color);
      } catch { /* routing engine unavailable - straight-line data still shown */ }

      card.innerHTML = `
        <strong>${service.label}: ${facility.name ?? "(unnamed)"}</strong>
        <table class="mini-table">
          <tr><th>Straight line</th><td>${formatDistance(facility.distance_m)}</td></tr>
          ${routeInfo ? `
            <tr><th>Road distance</th><td>${formatDistance(routeInfo.distance_m)}</td></tr>
            <tr><th>Est. travel time</th><td>${formatDuration(routeInfo.duration_s)}</td></tr>`
          : `<tr><th>Network route</th><td>unavailable (routing engine offline)</td></tr>`}
        </table>`;
    } catch (err) {
      card.innerHTML = `<strong>${service.label}</strong>
        <p class="tool-error">Failed: ${err.message}</p>`;
    }
  }

  pickBtn.addEventListener("click", async () => {
    pickBtn.classList.add("active");
    pickBtn.textContent = "Click incident location… (Esc to cancel)";
    try {
      const incident = await pickOnMap(viewer);
      source.entities.removeAll();
      resultsEl.innerHTML = "";
      marker(incident.lon, incident.lat, "#e2604f", "⚠ INCIDENT", 16);

      await Promise.all(SERVICES.map((s) => respond(s, incident)));
      resultsEl.insertAdjacentHTML("beforeend",
        `<p class="panel-note">Travel times are free-flow OSRM estimates on the OSM
         network — no live traffic. For demonstration and planning support only.</p>`);
      viewer.flyTo(source, { duration: 1.5 });
    } catch (err) {
      if (err.message !== "cancelled") {
        resultsEl.innerHTML = `<p class="tool-error">Failed: ${err.message}</p>`;
      }
    } finally {
      pickBtn.classList.remove("active");
      pickBtn.textContent = "Set incident location";
      viewer.scene.requestRender();
    }
  });
}
