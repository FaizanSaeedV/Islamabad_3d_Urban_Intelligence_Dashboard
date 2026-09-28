/**
 * Smart-city layer registry and layer-control panel.
 *
 * Every layer is lazy-loaded from the backend on first activation, styled by
 * geometry kind, and toggleable. Attribute panels show only fields present
 * in the data (OSM); nothing is invented.
 */
import { apiGet } from "./api.js";
import { loadBuildings } from "./buildings.js";

/* global Cesium */

// ---------------------------------------------------------------------------
// Registry
// ---------------------------------------------------------------------------
export const LAYER_DEFS = [
  // 3D city
  { id: "buildings", title: "Buildings (3D)", group: "3D City",
    kind: "buildings", endpoint: "/api/buildings", color: "#4f8ef7", defaultOn: true },

  // Environment
  { id: "water_bodies", title: "Water bodies", group: "Environment",
    kind: "polygon", endpoint: "/api/water-bodies", color: "#3f7fbf", alpha: 0.55, defaultOn: true },
  { id: "green_spaces", title: "Green spaces", group: "Environment",
    kind: "polygon", endpoint: "/api/green-spaces", color: "#3f9f5f", alpha: 0.5, defaultOn: true },
  { id: "waterways", title: "Rivers & canals", group: "Environment",
    kind: "line", endpoint: "/api/waterways", color: "#57a8d8", width: 2.5 },
  { id: "landuse", title: "Land use", group: "Environment",
    kind: "landuse", endpoint: "/api/landuse", params: { simplify_m: 3 }, color: "#8a795d", alpha: 0.35 },

  // Transport & mobility
  { id: "roads", title: "Roads", group: "Transport & Mobility",
    kind: "roads", endpoint: "/api/roads", params: { simplify_m: 2 }, color: "#c9b458" },
  { id: "railways", title: "Railways", group: "Transport & Mobility",
    kind: "line", endpoint: "/api/railways", color: "#b085c9", width: 3 },
  { id: "railway_station", title: "Railway stations", group: "Transport & Mobility",
    kind: "point", endpoint: "/api/facilities", params: { type: "railway_station" }, color: "#b085c9" },
  { id: "bus_stop", title: "Bus stops", group: "Transport & Mobility",
    kind: "point", endpoint: "/api/facilities", params: { type: "bus_stop" }, color: "#d8b447", pointSize: 6 },
  { id: "parking", title: "Parking", group: "Transport & Mobility",
    kind: "point", endpoint: "/api/facilities", params: { type: "parking" }, color: "#7f9fc9", pointSize: 7 },
  { id: "fuel_station", title: "Fuel stations", group: "Transport & Mobility",
    kind: "point", endpoint: "/api/facilities", params: { type: "fuel_station" }, color: "#e0824f" },
  { id: "ev_charging", title: "EV charging", group: "Transport & Mobility",
    kind: "point", endpoint: "/api/facilities", params: { type: "ev_charging" }, color: "#35c4a2" },

  // Emergency & public services
  { id: "hospital", title: "Hospitals & clinics", group: "Emergency & Public Services",
    kind: "point", endpoint: "/api/facilities", params: { type: "hospital" }, color: "#e2604f", pointSize: 10 },
  { id: "police_station", title: "Police stations", group: "Emergency & Public Services",
    kind: "point", endpoint: "/api/facilities", params: { type: "police_station" }, color: "#5f7fe0", pointSize: 9 },
  { id: "fire_station", title: "Fire stations", group: "Emergency & Public Services",
    kind: "point", endpoint: "/api/facilities", params: { type: "fire_station" }, color: "#e0a24f", pointSize: 9 },
  { id: "school", title: "Schools & universities", group: "Emergency & Public Services",
    kind: "point", endpoint: "/api/facilities", params: { type: "school" }, color: "#c9d84f", pointSize: 7 },
];

const FACILITY_TITLES = {
  hospital: "Hospital / clinic", police_station: "Police station",
  fire_station: "Fire station", school: "School / university",
  fuel_station: "Fuel station", ev_charging: "EV charging station",
  bus_stop: "Bus stop", parking: "Parking", railway_station: "Railway station",
};

// Road styling by class
const ROAD_STYLE = {
  motorway: { color: "#e0824f", width: 4.5 }, trunk: { color: "#e0824f", width: 4 },
  primary: { color: "#d8b447", width: 3.5 }, secondary: { color: "#c9b458", width: 3 },
  tertiary: { color: "#a8a878", width: 2.5 },
};
const ROAD_DEFAULT = { color: "#8a8f99", width: 1.5 };

// Land-use categorical colours (muted)
const LANDUSE_COLORS = {
  residential: "#7d8aa8", commercial: "#c98f6a", industrial: "#a87d7d",
  retail: "#c9a86a", construction: "#9a8f7d", military: "#8f7d9a",
  cemetery: "#7d9a8f", religious: "#9a7d8f",
};

// ---------------------------------------------------------------------------
// Honest attribute descriptions
// ---------------------------------------------------------------------------
const INFO_STYLE = `
  <style>
    .attr-table { width:100%; border-collapse:collapse; font-size:13px; }
    .attr-table th { text-align:left; padding:3px 10px 3px 0; color:#9fb0ce;
                     white-space:nowrap; vertical-align:top; }
    .attr-table td { padding:3px 0; }
    .attr-footer { color:#9fb0ce; font-size:11px; margin-top:8px; }
  </style>`;

export function describeGeneric(props, title) {
  const rows = [];
  const add = (label, value) => {
    if (value !== undefined && value !== null && value !== "") {
      rows.push(`<tr><th>${label}</th><td>${value}</td></tr>`);
    }
  };
  add("Type", title);
  add("Name", props.name);
  add("OSM ID", props.osm_id);
  add("Operator", props.operator);
  add("Opening hours", props.opening_hours);
  add("Capacity", props.capacity);
  add("Beds", props.beds);
  add("Road class", props.highway);
  add("Railway", props.railway);
  add("Waterway", props.waterway);
  add("Land use", props.landuse);
  add("Leisure", props.leisure);
  add("Natural", props.natural);
  if (props.length_m) add("Length", `${Number(props.length_m).toLocaleString()} m`);
  if (props.area_m2) add("Area", `${Number(props.area_m2).toLocaleString()} m²`);
  if (props.lanes) add("Lanes", props.lanes);
  if (props.maxspeed) add("Max speed", `${props.maxspeed} km/h`);
  return `${INFO_STYLE}<table class="attr-table">${rows.join("")}</table>
    <p class="attr-footer">Source: OpenStreetMap contributors (ODbL).
    Unmapped attributes are omitted rather than invented.</p>`;
}

// ---------------------------------------------------------------------------
// Styling per kind
// ---------------------------------------------------------------------------
function cssColor(hex, alpha = 1) {
  return Cesium.Color.fromCssColorString(hex).withAlpha(alpha);
}

function props(entity) {
  return entity.properties?.getValue(Cesium.JulianDate.now()) ?? {};
}

function stylePoint(dataSource, def) {
  for (const entity of dataSource.entities.values) {
    const p = props(entity);
    entity.billboard = undefined;
    entity.point = new Cesium.PointGraphics({
      pixelSize: def.pointSize ?? 8,
      color: cssColor(def.color),
      outlineColor: Cesium.Color.fromCssColorString("#0d1220"),
      outlineWidth: 1.5,
      disableDepthTestDistance: Number.POSITIVE_INFINITY,
    });
    const title = FACILITY_TITLES[p.facility_type] ?? def.title;
    entity.name = p.name || title;
    entity.description = describeGeneric(p, title);
  }
}

function styleLine(dataSource, def) {
  for (const entity of dataSource.entities.values) {
    if (!entity.polyline) continue;
    const p = props(entity);
    entity.polyline.material = cssColor(def.color);
    entity.polyline.width = def.width ?? 2;
    entity.polyline.clampToGround = true;
    entity.name = p.name || def.title;
    entity.description = describeGeneric(p, def.title);
  }
}

function styleRoads(dataSource, def) {
  for (const entity of dataSource.entities.values) {
    if (!entity.polyline) continue;
    const p = props(entity);
    const s = ROAD_STYLE[p.highway] ?? ROAD_DEFAULT;
    entity.polyline.material = cssColor(s.color);
    entity.polyline.width = s.width;
    entity.polyline.clampToGround = true;
    entity.name = p.name || `Road (${p.highway ?? "unclassified"})`;
    entity.description = describeGeneric(p, def.title);
  }
}

function stylePolygon(dataSource, def) {
  for (const entity of dataSource.entities.values) {
    if (!entity.polygon) continue;
    const p = props(entity);
    entity.polygon.material = cssColor(def.color, def.alpha ?? 0.5);
    entity.polygon.outline = false;
    entity.polygon.height = 0;
    entity.name = p.name || def.title;
    entity.description = describeGeneric(p, def.title);
  }
}

function styleLanduse(dataSource, def) {
  for (const entity of dataSource.entities.values) {
    if (!entity.polygon) continue;
    const p = props(entity);
    const hex = LANDUSE_COLORS[p.landuse] ?? def.color;
    entity.polygon.material = cssColor(hex, def.alpha ?? 0.35);
    entity.polygon.outline = false;
    entity.polygon.height = 0;
    entity.name = p.landuse ? `Land use: ${p.landuse}` : def.title;
    entity.description = describeGeneric(p, def.title);
  }
}

const STYLERS = {
  point: stylePoint,
  line: styleLine,
  roads: styleRoads,
  polygon: stylePolygon,
  landuse: styleLanduse,
};

/** Re-apply a layer's default styling (used to undo simulation overlays). */
export function restyle(dataSource, layerId) {
  const def = LAYER_DEFS.find((d) => d.id === layerId);
  if (def && dataSource) STYLERS[def.kind]?.(dataSource, def);
}

// ---------------------------------------------------------------------------
// Layer manager
// ---------------------------------------------------------------------------
export class LayerManager {
  constructor(viewer) {
    this.viewer = viewer;
    this.state = new Map(); // id -> { def, dataSource | null, loading }
    for (const def of LAYER_DEFS) this.state.set(def.id, { def, dataSource: null, loading: false });
  }

  /** Lazy-load a layer's data source on first activation. */
  async ensureLoaded(id, onStatus) {
    const item = this.state.get(id);
    if (!item || item.dataSource || item.loading) return item?.dataSource ?? null;
    item.loading = true;
    try {
      if (item.def.kind === "buildings") {
        item.dataSource = await loadBuildings(this.viewer, { onProgress: onStatus });
      } else {
        onStatus?.(`loading ${item.def.title.toLowerCase()}…`);
        const geojson = await apiGet(item.def.endpoint, item.def.params ?? {});
        const dataSource = await Cesium.GeoJsonDataSource.load(geojson, { clampToGround: true });
        dataSource.name = id;
        STYLERS[item.def.kind](dataSource, item.def);
        await this.viewer.dataSources.add(dataSource);
        item.dataSource = dataSource;
        onStatus?.(null);
      }
      this.viewer.scene.requestRender();
      return item.dataSource;
    } finally {
      item.loading = false;
    }
  }

  setVisible(id, visible) {
    const item = this.state.get(id);
    if (item?.dataSource) {
      item.dataSource.show = visible;
      this.viewer.scene.requestRender();
    }
  }

  featureCount(id) {
    return this.state.get(id)?.dataSource?.entities.values.length ?? null;
  }
}

// ---------------------------------------------------------------------------
// Layer-control panel (sidebar)
// ---------------------------------------------------------------------------
export function initLayerControl(viewer) {
  const manager = new LayerManager(viewer);
  const container = document.getElementById("layer-list");
  container.innerHTML = "";

  const statusLine = document.createElement("p");
  statusLine.className = "panel-note hidden";
  const setStatus = (text) => {
    statusLine.textContent = text ?? "";
    statusLine.classList.toggle("hidden", !text);
  };

  const groups = [...new Set(LAYER_DEFS.map((d) => d.group))];
  for (const group of groups) {
    const title = document.createElement("p");
    title.className = "layer-group-title";
    title.textContent = group;
    container.appendChild(title);

    for (const def of LAYER_DEFS.filter((d) => d.group === group)) {
      const label = document.createElement("label");
      label.className = "layer-item";
      label.innerHTML = `
        <input type="checkbox" ${def.defaultOn ? "checked" : ""} />
        <span class="layer-swatch" style="background:${def.color}"></span>
        <span class="layer-name">${def.title}</span>
        <span class="layer-count" id="count-${def.id}"></span>`;
      const checkbox = label.querySelector("input");

      checkbox.addEventListener("change", async () => {
        if (checkbox.checked) {
          checkbox.disabled = true;
          try {
            await manager.ensureLoaded(def.id, setStatus);
            manager.setVisible(def.id, true);
            const count = manager.featureCount(def.id);
            if (count !== null) {
              document.getElementById(`count-${def.id}`).textContent = count.toLocaleString();
            }
          } catch (err) {
            setStatus(`${def.title} failed: ${err.message}`);
            checkbox.checked = false;
          } finally {
            checkbox.disabled = false;
          }
        } else {
          manager.setVisible(def.id, false);
        }
      });

      container.appendChild(label);
      if (def.defaultOn) checkbox.dispatchEvent(new Event("change"));
    }
  }
  container.appendChild(statusLine);
  return manager;
}
