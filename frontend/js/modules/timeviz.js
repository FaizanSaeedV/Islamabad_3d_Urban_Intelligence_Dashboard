/**
 * Time-based visualization: animated demonstration vehicles on real routes.
 *
 * Routes are fetched at runtime from the routing engine (real OSM network
 * geometry between real Islamabad landmarks); the moving vehicles themselves
 * are DEMONSTRATIONS, clearly labelled — not real transit or emergency
 * telemetry. Animation uses CZML with Cesium's timeline/clock controls.
 */
import { apiGet } from "./api.js";

/* global Cesium */

// Real Islamabad landmarks used as route endpoints (approximate coordinates)
const DEMOS = [
  {
    id: "demo-bus",
    name: "Demo bus (Faizabad → Blue Area)",
    from: { lon: 73.0790, lat: 33.6642 },   // Faizabad interchange
    to: { lon: 73.0561, lat: 33.7112 },     // Blue Area
    speedKmh: 25,
    color: "#4f8ef7",
    label: "BUS [SIM]",
  },
  {
    id: "demo-ambulance",
    name: "Demo emergency vehicle (PIMS → F-9 Park)",
    from: { lon: 73.0551, lat: 33.7060 },   // PIMS area
    to: { lon: 73.0225, lat: 33.7007 },     // F-9 Park
    speedKmh: 55,
    color: "#e2604f",
    label: "EMERGENCY [SIM]",
  },
];

export function haversineM(lon1, lat1, lon2, lat2) {
  const R = 6371000;
  const rad = Math.PI / 180;
  const dLat = (lat2 - lat1) * rad;
  const dLon = (lon2 - lon1) * rad;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1 * rad) * Math.cos(lat2 * rad) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(a));
}

/**
 * Build a CZML packet animating a vehicle along a GeoJSON LineString at a
 * constant speed. Returns { packet, durationS }.
 */
export function buildVehiclePacket(demo, coordinates, startIso) {
  const samples = [];
  let t = 0;
  const mPerS = (demo.speedKmh * 1000) / 3600;
  for (let i = 0; i < coordinates.length; i++) {
    const [lon, lat] = coordinates[i];
    if (i > 0) {
      const [plon, plat] = coordinates[i - 1];
      t += haversineM(plon, plat, lon, lat) / mPerS;
    }
    samples.push(t, lon, lat, 12); // 12 m above ellipsoid so the point reads over roads
  }
  const durationS = Math.ceil(t);
  const packet = {
    id: demo.id,
    name: `${demo.name} — Simulated for Digital Twin Demonstration`,
    availability: `${startIso}/${addSeconds(startIso, durationS)}`,
    position: {
      epoch: startIso,
      cartographicDegrees: samples,
      interpolationAlgorithm: "LAGRANGE",
      interpolationDegree: 1,
    },
    point: {
      pixelSize: 14,
      color: { rgba: hexToRgba(demo.color) },
      outlineColor: { rgba: [255, 255, 255, 255] },
      outlineWidth: 2,
      disableDepthTestDistance: 1e12,
    },
    label: {
      text: demo.label,
      font: "12px sans-serif",
      pixelOffset: { cartesian2: [0, -22] },
      fillColor: { rgba: [255, 255, 255, 255] },
      showBackground: true,
      backgroundColor: { rgba: [19, 26, 44, 220] },
      disableDepthTestDistance: 1e12,
    },
    path: {
      material: { solidColor: { color: { rgba: hexToRgba(demo.color, 140) } } },
      width: 4,
      leadTime: 0,
      trailTime: 600,
      resolution: 5,
    },
    description:
      `<p>${demo.name}.</p><p style="color:#f0b23e">⚠ Simulated for Digital Twin ` +
      `Demonstration — a synthetic vehicle animated along a real OSM route. ` +
      `Not real transit/emergency telemetry.</p>`,
  };
  return { packet, durationS };
}

export function hexToRgba(hex, alpha = 255) {
  const n = parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255, alpha];
}

export function addSeconds(iso, seconds) {
  return new Date(new Date(iso).getTime() + seconds * 1000).toISOString();
}

export function initTimeViz(viewer) {
  const btn = document.getElementById("timeviz-btn");
  const status = document.getElementById("timeviz-status");
  let dataSource = null;

  async function start() {
    btn.disabled = true;
    status.textContent = "Fetching real routes from the routing engine…";
    try {
      const startIso = new Date().toISOString();
      const packets = [
        { id: "document", name: "Demo vehicles", version: "1.0" },
      ];
      let maxDuration = 0;

      for (const demo of DEMOS) {
        const route = await apiGet("/api/route", {
          from_lon: demo.from.lon, from_lat: demo.from.lat,
          to_lon: demo.to.lon, to_lat: demo.to.lat,
        });
        const { packet, durationS } = buildVehiclePacket(
          demo, route.geometry.coordinates, startIso
        );
        packets.push(packet);
        maxDuration = Math.max(maxDuration, durationS);
      }

      packets[0].clock = {
        interval: `${startIso}/${addSeconds(startIso, maxDuration)}`,
        currentTime: startIso,
        multiplier: 20,
        range: "LOOP_STOP",
        step: "SYSTEM_CLOCK_MULTIPLIER",
      };

      dataSource = await Cesium.CzmlDataSource.load(packets);
      await viewer.dataSources.add(dataSource);

      document.body.classList.add("time-active");
      viewer.clock.shouldAnimate = true;
      viewer.scene.requestRender();
      viewer.flyTo(dataSource, { duration: 2 });

      btn.textContent = "Stop vehicle animation";
      status.textContent =
        "Playing at 20× speed — use the timeline and clock controls at the bottom. " +
        "Vehicles are simulated demonstrations on real OSM routes.";
    } catch (err) {
      status.textContent = `Time demo unavailable: ${err.message} ` +
        "(the routing engine must be reachable).";
    } finally {
      btn.disabled = false;
    }
  }

  function stop() {
    if (dataSource) {
      viewer.dataSources.remove(dataSource, true);
      dataSource = null;
    }
    document.body.classList.remove("time-active");
    viewer.clock.shouldAnimate = false;
    viewer.scene.requestRender();
    btn.textContent = "Start vehicle animation";
    status.textContent = "";
  }

  btn.addEventListener("click", () => (dataSource ? stop() : start()));
}
