/**
 * Frontend pure-logic tests (no browser needed).
 * Run from the repository root:  node tests/frontend/logic_tests.mjs
 */
import { strict as assert } from "node:assert";

// Minimal Cesium mock for modules that touch Cesium at import time
globalThis.Cesium = {
  Color: { fromCssColorString: () => ({ withAlpha: () => ({}) }), WHITE: {} },
  JulianDate: { now: () => 0 },
  PointGraphics: function (o) { Object.assign(this, o); },
  CustomDataSource: function () {},
  EllipsoidGeodesic: function () { this.surfaceDistance = 0; },
};

const modules = new URL("../../frontend/js/modules/", import.meta.url);
let passed = 0;
const check = (name, fn) => Promise.resolve()
  .then(fn)
  .then(() => { passed += 1; console.log(`  ok  ${name}`); })
  .catch((err) => { console.error(`FAIL  ${name}: ${err.message}`); process.exitCode = 1; });

// ---------------------------------------------------------------- buildings
const buildings = await import(new URL("buildings.js", modules));
await check("height classes: <12 low, 12-30 mid, >30 high", () => {
  assert.equal(buildings.heightClass(5), "low");
  assert.equal(buildings.heightClass(12), "mid");
  assert.equal(buildings.heightClass(30), "mid");
  assert.equal(buildings.heightClass(31), "high");
});
await check("building description labels estimates honestly", () => {
  const html = buildings.describeBuilding({ osm_id: 1, height_m: 12, height_source: "levels_x3" });
  assert.match(html, /estimated: building levels/);
  assert.doesNotMatch(html, /undefined/);
});

// ----------------------------------------------------------------- mobility
const mobility = await import(new URL("mobility.js", modules));
await check("distance & duration formatting", () => {
  assert.equal(mobility.formatDistance(850), "850 m");
  assert.equal(mobility.formatDistance(1250), "1.25 km");
  assert.equal(mobility.formatDuration(300), "5 min");
  assert.equal(mobility.formatDuration(3900), "1 h 5 min");
});
await check("GeoJSON LineString flattening", () => {
  assert.deepEqual(
    mobility.routePositions({ coordinates: [[79.85, 6.93], [79.86, 6.94]] }),
    [79.85, 6.93, 79.86, 6.94]
  );
});

// ------------------------------------------------------------------ weather
const weather = await import(new URL("weather.js", modules));
await check("WMO weather codes", () => {
  assert.equal(weather.weatherDescription(0).text, "Clear sky");
  assert.equal(weather.weatherDescription(63).text, "Rain");
  assert.equal(weather.weatherDescription(96).text, "Thunderstorm");
});
await check("wind compass", () => {
  assert.equal(weather.windCompass(0), "N");
  assert.equal(weather.windCompass(225), "SW");
  assert.equal(weather.windCompass(359), "N");
});

// ------------------------------------------------------------------ timeviz
const timeviz = await import(new URL("timeviz.js", modules));
await check("haversine within 0.3% of 1-degree latitude arc", () => {
  const d = timeviz.haversineM(79.86, 6.0, 79.86, 7.0);
  assert.ok(Math.abs(d - 111195) < 300, `got ${d}`);
});
await check("CZML vehicle packet timing (1 km @ 36 km/h ~ 100 s)", () => {
  const { packet, durationS } = timeviz.buildVehiclePacket(
    { id: "x", name: "X", speedKmh: 36, color: "#4f8ef7", label: "X" },
    [[79.85, 6.90], [79.85, 6.909]],
    "2026-07-15T00:00:00.000Z"
  );
  assert.ok(durationS >= 98 && durationS <= 103, `got ${durationS}`);
  assert.match(packet.name, /Simulated/);
});

// --------------------------------------------------------------- simulation
const simulation = await import(new URL("simulation.js", modules));
await check("status summarisation", () => {
  const c = simulation.summarize([{ status: "low" }, { status: "low" }, { status: "severe" }]);
  assert.equal(c.low, 2);
  assert.equal(c.severe, 1);
});

// ------------------------------------------------------------------ measure
const measure = await import(new URL("measure.js", modules));
await check("planar area: ~1 km² square within 1%", () => {
  const sq = [
    { lon: 79.85, lat: 6.90 }, { lon: 79.859034, lat: 6.90 },
    { lon: 79.859034, lat: 6.909043 }, { lon: 79.85, lat: 6.909043 },
  ];
  const a = measure.planarAreaM2(sq);
  assert.ok(Math.abs(a - 1e6) / 1e6 < 0.01, `got ${a}`);
});
await check("area formatting units", () => {
  assert.equal(measure.formatArea(1_500_000), "1.500 km²");
  assert.equal(measure.formatArea(25_000), "2.50 ha");
});

// ----------------------------------------------------------------- analysis
const analysis = await import(new URL("analysis.js", modules));
await check("choropleth classification breaks", () => {
  const B = [{ max: 10, color: "a" }, { max: 50, color: "b" }, { max: Infinity, color: "c" }];
  assert.equal(analysis.classify(10, B), "a");
  assert.equal(analysis.classify(11, B), "b");
  assert.equal(analysis.classify(999, B), "c");
});

console.log(`\n${passed} frontend logic checks passed${process.exitCode ? " (with failures)" : ""}.`);
