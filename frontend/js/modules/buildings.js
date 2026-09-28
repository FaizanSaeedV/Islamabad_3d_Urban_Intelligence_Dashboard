/**
 * 3D buildings layer: loads footprints from the backend, extrudes them by
 * height_m, colours by height class, and provides honest click-to-inspect
 * attribute panels (only attributes present in the data are shown; estimated
 * heights are labelled as estimates, never presented as measured).
 */
import { apiGet } from "./api.js";

/* global Cesium */

// Height classification (matches backend/docs/GIS_METHODOLOGY.md):
// low-rise < 12 m, mid-rise 12-30 m, high-rise > 30 m
const CLASS_COLORS = {
  low: Cesium.Color.fromCssColorString("#8fa8c9").withAlpha(0.95),
  mid: Cesium.Color.fromCssColorString("#4f8ef7").withAlpha(0.95),
  high: Cesium.Color.fromCssColorString("#35c4a2").withAlpha(0.97),
};

export function heightClass(heightM) {
  if (heightM > 30) return "high";
  if (heightM >= 12) return "mid";
  return "low";
}

const HEIGHT_SOURCE_LABEL = {
  osm_height: "OSM height tag (mapped value)",
  levels_x3: "estimated: building levels × 3.0 m",
  default_assumed: "assumed default (6 m) — no height data in OSM",
};

/** Build an honest attribute table for the info box: only fields that exist. */
export function describeBuilding(props) {
  const rows = [];
  const add = (label, value) => {
    if (value !== undefined && value !== null && value !== "") {
      rows.push(`<tr><th>${label}</th><td>${value}</td></tr>`);
    }
  };
  add("Building ID", `${props.osm_id ?? "n/a"} (OSM)`);
  add("Name", props.name);
  add("Building type", props.building_type);
  add("Levels", props.levels);
  if (props.height_m !== undefined && props.height_m !== null) {
    const src = HEIGHT_SOURCE_LABEL[props.height_source] ?? props.height_source ?? "";
    add("Height", `${props.height_m} m <span class="attr-note">(${src})</span>`);
  }
  add("Amenity", props.amenity);
  if (props.footprint_area_m2) add("Footprint area", `${Number(props.footprint_area_m2).toLocaleString()} m²`);
  add("Height class", { low: "Low-rise", mid: "Mid-rise", high: "High-rise" }[heightClass(props.height_m ?? 0)]);

  // Cesium's InfoBox renders inside an iframe; inline a minimal style block
  // so the table is readable regardless of outer CSS.
  return `
    <style>
      .attr-table { width:100%; border-collapse:collapse; font-size:13px; }
      .attr-table th { text-align:left; padding:3px 10px 3px 0; color:#9fb0ce;
                       white-space:nowrap; vertical-align:top; }
      .attr-table td { padding:3px 0; }
      .attr-note, .attr-footer { color:#9fb0ce; font-size:11px; }
      .attr-footer { margin-top:8px; }
    </style>
    <table class="attr-table">${rows.join("")}</table>
    <p class="attr-footer">Source: OpenStreetMap contributors (ODbL). Attributes not
    mapped in OSM are omitted rather than invented.</p>`;
}

/**
 * Load buildings from the API into the viewer.
 * Returns the Cesium DataSource (or null on failure).
 */
export async function loadBuildings(viewer, { limit = 100000, onProgress } = {}) {
  onProgress?.("loading building data…");
  const geojson = await apiGet("/api/buildings", { limit });
  onProgress?.(`rendering ${geojson.features.length.toLocaleString()} buildings…`);

  const dataSource = await Cesium.GeoJsonDataSource.load(geojson, { clampToGround: false });
  dataSource.name = "buildings";

  for (const entity of dataSource.entities.values) {
    if (!entity.polygon) continue;
    const props = entity.properties?.getValue(Cesium.JulianDate.now()) ?? {};
    const h = Number(props.height_m) || 6.0;
    entity.polygon.extrudedHeight = h;
    entity.polygon.height = 0;
    entity.polygon.material = CLASS_COLORS[heightClass(h)];
    entity.polygon.outline = false;
    // Name shown in the info box title; description built on demand (honest attrs)
    entity.name = props.name || props.building_type || "Building";
    entity.description = describeBuilding(props);
  }

  await viewer.dataSources.add(dataSource);
  viewer.scene.requestRender();
  onProgress?.(null);
  return dataSource;
}
