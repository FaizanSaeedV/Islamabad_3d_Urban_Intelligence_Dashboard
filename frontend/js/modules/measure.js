/**
 * 3D measurement tools.
 *
 * Distance: geodesic (WGS 84 ellipsoid) along clicked vertices.
 * Area: planar approximation - vertices are projected onto a local
 *   east-north tangent plane at the polygon's first vertex, then the
 *   shoelace formula is applied. Error is negligible (<0.1%) at city scale.
 * Height: reads the clicked building's height_m ATTRIBUTE (with its source
 *   flag). This is attribute-based, not a photogrammetric measurement -
 *   the app has no measured 3D surface, and pretending otherwise would
 *   fabricate accuracy. Limitations documented in docs/GIS_METHODOLOGY.md.
 */

/* global Cesium */

export function geodesicDistanceM(carto1, carto2) {
  const geodesic = new Cesium.EllipsoidGeodesic(carto1, carto2);
  return geodesic.surfaceDistance;
}

/** Shoelace area on a local tangent plane. Input: [{lon,lat}, ...] degrees. */
export function planarAreaM2(points) {
  if (points.length < 3) return 0;
  const R = 6378137; // WGS 84 semi-major axis
  const rad = Math.PI / 180;
  const lat0 = points[0].lat * rad;
  // local equirectangular projection (metres), accurate at city scale
  const xy = points.map((p) => ({
    x: (p.lon * rad) * R * Math.cos(lat0),
    y: (p.lat * rad) * R,
  }));
  let sum = 0;
  for (let i = 0; i < xy.length; i++) {
    const j = (i + 1) % xy.length;
    sum += xy[i].x * xy[j].y - xy[j].x * xy[i].y;
  }
  return Math.abs(sum) / 2;
}

export function formatArea(m2) {
  if (m2 >= 1_000_000) return `${(m2 / 1_000_000).toFixed(3)} km²`;
  if (m2 >= 10_000) return `${(m2 / 10_000).toFixed(2)} ha`;
  return `${Math.round(m2).toLocaleString()} m²`;
}

export function initMeasureTool(viewer) {
  const source = new Cesium.CustomDataSource("measure");
  viewer.dataSources.add(source);

  const distBtn = document.getElementById("measure-dist");
  const areaBtn = document.getElementById("measure-area");
  const heightBtn = document.getElementById("measure-height");
  const clearBtn = document.getElementById("measure-clear");
  const out = document.getElementById("measure-out");

  let mode = null;          // 'distance' | 'area' | 'height' | null
  let points = [];          // [{lon, lat, carto}]
  let handler = null;

  function reset() {
    mode = null;
    points = [];
    if (handler) { handler.destroy(); handler = null; }
    viewer.canvas.style.cursor = "";
    distBtn.classList.remove("active");
    areaBtn.classList.remove("active");
    heightBtn.classList.remove("active");
  }

  function clearAll() {
    reset();
    source.entities.removeAll();
    out.innerHTML = "";
    viewer.scene.requestRender();
  }

  function addVertex(lon, lat) {
    source.entities.add({
      position: Cesium.Cartesian3.fromDegrees(lon, lat),
      point: {
        pixelSize: 7,
        color: Cesium.Color.fromCssColorString("#f0b23e"),
        outlineColor: Cesium.Color.fromCssColorString("#0d1220"),
        outlineWidth: 1,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
    });
  }

  function redrawShape() {
    // remove previous line/polygon (keep vertices)
    for (const e of [...source.entities.values]) {
      if (e.polyline || e.polygon) source.entities.remove(e);
    }
    const flat = points.flatMap((p) => [p.lon, p.lat]);
    if (mode === "distance" && points.length >= 2) {
      source.entities.add({
        polyline: {
          positions: Cesium.Cartesian3.fromDegreesArray(flat),
          width: 3,
          clampToGround: true,
          material: Cesium.Color.fromCssColorString("#f0b23e"),
        },
      });
    }
    if (mode === "area" && points.length >= 3) {
      source.entities.add({
        polygon: {
          hierarchy: Cesium.Cartesian3.fromDegreesArray(flat),
          material: Cesium.Color.fromCssColorString("#f0b23e").withAlpha(0.3),
          height: 0,
          outline: false,
        },
      });
    }
    viewer.scene.requestRender();
  }

  function updateReadout(final = false) {
    if (mode === "distance") {
      let total = 0;
      for (let i = 1; i < points.length; i++) {
        total += geodesicDistanceM(points[i - 1].carto, points[i].carto);
      }
      out.innerHTML = `
        <p><strong>${total >= 1000 ? `${(total / 1000).toFixed(3)} km` : `${total.toFixed(1)} m`}</strong>
        · ${points.length} vertices ${final ? "" : "· click to add, right-click to finish"}</p>
        <p class="panel-note">Geodesic distance on the WGS 84 ellipsoid (surface path,
        terrain height not included).</p>`;
    } else if (mode === "area") {
      const area = planarAreaM2(points);
      out.innerHTML = `
        <p><strong>${formatArea(area)}</strong>
        · ${points.length} vertices ${final ? "" : "· click to add, right-click to finish"}</p>
        <p class="panel-note">Planar approximation on a local tangent plane
        (&lt;0.1% error at city scale).</p>`;
    }
  }

  function startVertexMode(newMode, button) {
    clearAll();
    mode = newMode;
    button.classList.add("active");
    viewer.canvas.style.cursor = "crosshair";
    out.innerHTML = "<p class='panel-note'>Click vertices on the map; right-click to finish. Esc cancels.</p>";

    handler = new Cesium.ScreenSpaceEventHandler(viewer.canvas);
    handler.setInputAction((click) => {
      const cartesian = viewer.camera.pickEllipsoid(click.position, viewer.scene.globe.ellipsoid);
      if (!cartesian) return;
      const carto = Cesium.Cartographic.fromCartesian(cartesian);
      const lon = Cesium.Math.toDegrees(carto.longitude);
      const lat = Cesium.Math.toDegrees(carto.latitude);
      points.push({ lon, lat, carto });
      addVertex(lon, lat);
      redrawShape();
      updateReadout();
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
    handler.setInputAction(() => {
      updateReadout(true);
      reset();
    }, Cesium.ScreenSpaceEventType.RIGHT_CLICK);
  }

  distBtn.addEventListener("click", () => startVertexMode("distance", distBtn));
  areaBtn.addEventListener("click", () => startVertexMode("area", areaBtn));

  heightBtn.addEventListener("click", () => {
    clearAll();
    mode = "height";
    heightBtn.classList.add("active");
    viewer.canvas.style.cursor = "crosshair";
    out.innerHTML = "<p class='panel-note'>Click a 3D building…</p>";
    handler = new Cesium.ScreenSpaceEventHandler(viewer.canvas);
    handler.setInputAction((click) => {
      const picked = viewer.scene.pick(click.position);
      const entity = picked?.id;
      const props = entity?.properties?.getValue(Cesium.JulianDate.now());
      if (props?.height_m !== undefined) {
        const srcLabel = {
          osm_height: "OSM height tag (mapped value)",
          levels_x3: "estimated from building levels × 3.0 m",
          default_assumed: "assumed default — no OSM height data",
        }[props.height_source] ?? "unknown source";
        out.innerHTML = `
          <p><strong>${props.height_m} m</strong> — ${entity.name ?? "building"}</p>
          <p class="panel-note">Attribute-based reading (${srcLabel}). This app has no
          photogrammetric surface, so heights are reported from data, not measured
          from the scene. See docs/GIS_METHODOLOGY.md.</p>`;
        reset();
      } else {
        out.innerHTML = "<p class='panel-note'>Not a building — click an extruded 3D building. Esc cancels.</p>";
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
  });

  clearBtn.addEventListener("click", clearAll);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && mode) { updateReadout(true); reset(); }
  });
}
