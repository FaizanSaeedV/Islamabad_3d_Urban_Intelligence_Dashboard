/**
 * Interactive spatial query tool (PostGIS-backed).
 * Three parameterised query templates; results are highlighted in the scene.
 */
import { apiGet } from "./api.js";
import { pickOnMap } from "./mappick.js";

/* global Cesium */

const FACILITY_OPTIONS = `
  <option value="hospital">Hospitals</option>
  <option value="police_station">Police stations</option>
  <option value="fire_station">Fire stations</option>
  <option value="school">Schools</option>
  <option value="fuel_station">Fuel stations</option>
  <option value="ev_charging">EV chargers</option>
  <option value="bus_stop">Bus stops</option>
  <option value="parking">Parking</option>
  <option value="railway_station">Railway stations</option>`;

const QUERIES = {
  "buildings-near": {
    label: "Buildings within radius of a facility type",
    params: `
      <select id="q-type" class="tool-select">${FACILITY_OPTIONS}</select>
      <input id="q-radius" class="tool-select" type="number" value="500" min="10" max="10000" /> m`,
    needsPick: false,
  },
  "facilities-within": {
    label: "Facilities within radius of a picked point",
    params: `
      <select id="q-type" class="tool-select"><option value="">All types</option>${FACILITY_OPTIONS}</select>
      <input id="q-radius" class="tool-select" type="number" value="1000" min="10" max="10000" /> m`,
    needsPick: true,
  },
  "near-roads": {
    label: "Facilities near major roads",
    params: `
      <select id="q-type" class="tool-select">${FACILITY_OPTIONS}</select>
      <input id="q-radius" class="tool-select" type="number" value="100" min="10" max="10000" /> m`,
    needsPick: false,
  },
};

export function initQueryTool(viewer) {
  const source = new Cesium.CustomDataSource("query-results");
  viewer.dataSources.add(source);

  const select = document.getElementById("query-select");
  const paramsEl = document.getElementById("query-params");
  const runBtn = document.getElementById("query-run");
  const clearBtn = document.getElementById("query-clear");
  const out = document.getElementById("query-out");

  select.innerHTML = Object.entries(QUERIES)
    .map(([k, q]) => `<option value="${k}">${q.label}</option>`)
    .join("");
  const renderParams = () => { paramsEl.innerHTML = QUERIES[select.value].params; };
  select.addEventListener("change", renderParams);
  renderParams();

  function highlight(geojson) {
    source.entities.removeAll();
    for (const f of geojson.features) {
      const props = f.properties ?? {};
      if (f.geometry.type === "Point") {
        source.entities.add({
          position: Cesium.Cartesian3.fromDegrees(...f.geometry.coordinates.slice(0, 2), 2),
          point: {
            pixelSize: 11,
            color: Cesium.Color.fromCssColorString("#f0b23e"),
            outlineColor: Cesium.Color.fromCssColorString("#0d1220"),
            outlineWidth: 2,
            disableDepthTestDistance: Number.POSITIVE_INFINITY,
          },
          name: props.name ?? "Query result",
          description: `<p>${props.name ?? "(unnamed)"}${props.facility_type ? ` — ${props.facility_type}` : ""}
            ${props.distance_m != null ? `<br>Distance: ${props.distance_m} m` : ""}</p>`,
        });
      } else {
        const rings = f.geometry.type === "MultiPolygon"
          ? f.geometry.coordinates.map((p) => p[0])
          : [f.geometry.coordinates[0]];
        for (const ring of rings) {
          source.entities.add({
            polygon: {
              hierarchy: Cesium.Cartesian3.fromDegreesArray(ring.flat()),
              material: Cesium.Color.fromCssColorString("#f0b23e").withAlpha(0.6),
              height: 0,
              extrudedHeight: Number(props.height_m) || 6,
            },
            name: props.name ?? "Query result",
            description: `<p>${props.name ?? "(unnamed building)"}
              ${props.building_type ? `— ${props.building_type}` : ""}
              ${props.height_m ? `<br>Height: ${props.height_m} m` : ""}</p>`,
          });
        }
      }
    }
    viewer.scene.requestRender();
  }

  runBtn.addEventListener("click", async () => {
    const kind = select.value;
    const q = QUERIES[kind];
    const type = document.getElementById("q-type").value || null;
    const radius = Number(document.getElementById("q-radius").value);
    runBtn.disabled = true;
    try {
      let geojson;
      if (kind === "buildings-near") {
        out.innerHTML = "<p class='panel-note'>Querying…</p>";
        geojson = await apiGet("/api/query/buildings-near-facility",
          { type, radius_m: radius });
      } else if (kind === "near-roads") {
        out.innerHTML = "<p class='panel-note'>Querying…</p>";
        geojson = await apiGet("/api/query/facilities-near-roads",
          { type, radius_m: radius });
      } else {
        out.innerHTML = "<p class='panel-note'>Click a point on the map… (Esc to cancel)</p>";
        const p = await pickOnMap(viewer);
        out.innerHTML = "<p class='panel-note'>Querying…</p>";
        geojson = await apiGet("/api/query/facilities-within",
          { lon: p.lon, lat: p.lat, radius_m: radius, type });
      }
      highlight(geojson);
      out.innerHTML = `<p class="panel-note"><strong>${geojson.features.length.toLocaleString()}</strong>
        result${geojson.features.length === 1 ? "" : "s"} highlighted (PostGIS spatial query).</p>`;
      if (geojson.features.length) viewer.flyTo(source, { duration: 1.5 });
    } catch (err) {
      if (err.message !== "cancelled") out.innerHTML = `<p class="tool-error">${err.message}</p>`;
      else out.innerHTML = "";
    } finally {
      runBtn.disabled = false;
    }
  });

  clearBtn.addEventListener("click", () => {
    source.entities.removeAll();
    out.innerHTML = "";
    viewer.scene.requestRender();
  });
}
