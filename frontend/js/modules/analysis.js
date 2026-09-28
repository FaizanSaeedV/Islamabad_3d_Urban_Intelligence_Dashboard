/**
 * Advanced GIS analysis UI:
 *  - Building density grid (choropleth from /api/analysis/building-density)
 *  - Green-space accessibility: point stats + accessibility grid
 *  - Infrastructure coverage (/api/coverage): service area + underserved share
 * Classification breaks are documented inline and in docs/GIS_METHODOLOGY.md.
 */
import { apiGet } from "./api.js";
import { pickOnMap } from "./mappick.js";

/* global Cesium */

// Quantile-free fixed breaks, chosen for readability and documented:
// density (buildings / cell): 1-10, 11-50, 51-150, >150
const DENSITY_BREAKS = [
  { max: 10, color: "#2a3655" }, { max: 50, color: "#4f8ef7" },
  { max: 150, color: "#e0a24f" }, { max: Infinity, color: "#e2604f" },
];
// green access (m to nearest green space): WHO-inspired 300 m target,
// then 600/1000 m bands
const ACCESS_BREAKS = [
  { max: 300, color: "#35c4a2" }, { max: 600, color: "#c9d84f" },
  { max: 1000, color: "#e0a24f" }, { max: Infinity, color: "#e2604f" },
];

export function classify(value, breaks) {
  for (const b of breaks) if (value <= b.max) return b.color;
  return breaks[breaks.length - 1].color;
}

function gridToEntities(viewer, geojson, valueKey, breaks, name) {
  const source = new Cesium.CustomDataSource(name);
  for (const f of geojson.features) {
    const v = f.properties[valueKey];
    if (v === null || v === undefined) continue;
    const ring = f.geometry.coordinates[0];
    source.entities.add({
      polygon: {
        hierarchy: Cesium.Cartesian3.fromDegreesArray(ring.flat()),
        material: Cesium.Color.fromCssColorString(classify(v, breaks)).withAlpha(0.45),
        height: 0,
        outline: false,
      },
      description: `<p>${valueKey.replace(/_/g, " ")}: <strong>${v}</strong></p>
        <p style="color:#9fb0ce;font-size:11px">${geojson.metadata?.method ?? ""} ·
        cell ${geojson.metadata?.cell_m} m (EPSG:32643)</p>`,
    });
  }
  viewer.dataSources.add(source);
  viewer.scene.requestRender();
  return source;
}

function legendHtml(breaks, labels) {
  return `<div class="sim-legend">${breaks.map((b, i) => `
    <span class="sim-chip"><span class="layer-swatch" style="background:${b.color}"></span>
    ${labels[i]}</span>`).join("")}</div>`;
}

export function initAnalysisTools(viewer) {
  const grids = { density: null, access: null };
  const coverageSource = new Cesium.CustomDataSource("coverage-area");
  viewer.dataSources.add(coverageSource);

  // ---------------------------------------------------- building density grid
  const densityBtn = document.getElementById("density-btn");
  const densityOut = document.getElementById("density-out");
  densityBtn.addEventListener("click", async () => {
    if (grids.density) {
      viewer.dataSources.remove(grids.density, true);
      grids.density = null;
      densityBtn.textContent = "Show density grid";
      densityOut.innerHTML = "";
      viewer.scene.requestRender();
      return;
    }
    densityBtn.disabled = true;
    densityOut.innerHTML = "<p class='panel-note'>Computing 250 m grid…</p>";
    try {
      const gj = await apiGet("/api/analysis/building-density", { cell_m: 250 });
      grids.density = gridToEntities(viewer, gj, "count", DENSITY_BREAKS, "density-grid");
      densityBtn.textContent = "Hide density grid";
      densityOut.innerHTML =
        `<p class="panel-note">${gj.features.length} cells (250 m, EPSG:32643).</p>` +
        legendHtml(DENSITY_BREAKS, ["≤10", "11–50", "51–150", ">150 bldgs"]);
    } catch (err) {
      densityOut.innerHTML = `<p class="tool-error">${err.message}</p>`;
    } finally {
      densityBtn.disabled = false;
    }
  });

  // ------------------------------------------------- green accessibility grid
  const accessBtn = document.getElementById("access-btn");
  const accessOut = document.getElementById("access-out");
  accessBtn.addEventListener("click", async () => {
    if (grids.access) {
      viewer.dataSources.remove(grids.access, true);
      grids.access = null;
      accessBtn.textContent = "Show accessibility grid";
      accessOut.innerHTML = "";
      viewer.scene.requestRender();
      return;
    }
    accessBtn.disabled = true;
    accessOut.innerHTML = "<p class='panel-note'>Computing accessibility surface…</p>";
    try {
      const gj = await apiGet("/api/analysis/green-access-grid", { cell_m: 250 });
      grids.access = gridToEntities(viewer, gj, "distance_m", ACCESS_BREAKS, "access-grid");
      accessBtn.textContent = "Hide accessibility grid";
      accessOut.innerHTML =
        `<p class="panel-note">Distance from each 250 m cell to the nearest
         green space. Red cells (>1 km) indicate poor accessibility.</p>` +
        legendHtml(ACCESS_BREAKS, ["≤300 m", "≤600 m", "≤1 km", ">1 km"]);
    } catch (err) {
      accessOut.innerHTML = `<p class="tool-error">${err.message}</p>`;
    } finally {
      accessBtn.disabled = false;
    }
  });

  // ------------------------------------------------- green stats from a point
  const greenPickBtn = document.getElementById("green-pick");
  const greenOut = document.getElementById("green-out");
  greenPickBtn.addEventListener("click", async () => {
    greenPickBtn.classList.add("active");
    greenPickBtn.textContent = "Click on the map… (Esc to cancel)";
    try {
      const p = await pickOnMap(viewer);
      greenOut.innerHTML = "<p class='panel-note'>Analysing…</p>";
      const s = await apiGet("/api/analysis/green-space",
        { lon: p.lon, lat: p.lat, radius_m: 1000 });
      greenOut.innerHTML = `
        <table class="mini-table">
          <tr><th>Nearest green space</th>
              <td>${s.nearest_green_space_m != null
                ? `${s.nearest_green_space_m} m${s.nearest_green_space_name ? ` (${s.nearest_green_space_name})` : ""}`
                : "none found"}</td></tr>
          <tr><th>Within 1 km</th><td>${s.green_spaces_within_radius} green spaces</td></tr>
          <tr><th>Green area in 1 km</th><td>${s.green_area_ha_within_radius} ha</td></tr>
        </table>`;
    } catch (err) {
      if (err.message !== "cancelled") greenOut.innerHTML = `<p class="tool-error">${err.message}</p>`;
    } finally {
      greenPickBtn.classList.remove("active");
      greenPickBtn.textContent = "Pick a point";
    }
  });

  // ----------------------------------------------------------- coverage tool
  const covBtn = document.getElementById("coverage-btn");
  const covType = document.getElementById("coverage-type");
  const covRadius = document.getElementById("coverage-radius");
  const covOut = document.getElementById("coverage-out");
  covBtn.addEventListener("click", async () => {
    covBtn.disabled = true;
    covOut.innerHTML = "<p class='panel-note'>Running buffer analysis…</p>";
    coverageSource.entities.removeAll();
    try {
      const c = await apiGet("/api/coverage", {
        type: covType.value, radius_m: covRadius.value, include_geometry: true,
      });
      if (c.service_area) {
        const geom = c.service_area;
        const polys = geom.type === "MultiPolygon" ? geom.coordinates : [geom.coordinates];
        for (const poly of polys) {
          coverageSource.entities.add({
            polygon: {
              hierarchy: new Cesium.PolygonHierarchy(
                Cesium.Cartesian3.fromDegreesArray(poly[0].flat()),
                poly.slice(1).map((hole) => new Cesium.PolygonHierarchy(
                  Cesium.Cartesian3.fromDegreesArray(hole.flat())))),
              material: Cesium.Color.fromCssColorString("#35c4a2").withAlpha(0.25),
              outline: false,
              height: 0,
            },
          });
        }
        viewer.scene.requestRender();
      }
      covOut.innerHTML = `
        <table class="mini-table">
          <tr><th>Facilities</th><td>${c.facility_count}</td></tr>
          <tr><th>Buildings covered</th><td>${c.covered_buildings.toLocaleString()} / ${c.total_buildings.toLocaleString()}</td></tr>
          <tr><th>Underserved</th><td><strong>${c.underserved_pct}%</strong> of buildings</td></tr>
        </table>
        <p class="panel-note">${c.method}</p>`;
    } catch (err) {
      covOut.innerHTML = `<p class="tool-error">${err.message}</p>`;
    } finally {
      covBtn.disabled = false;
    }
  });
}
