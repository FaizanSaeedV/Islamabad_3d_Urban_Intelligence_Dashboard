/**
 * One-shot "pick a location on the map" helper.
 * Resolves with { lon, lat } on left click; rejects on Escape.
 */

/* global Cesium */

export function pickOnMap(viewer) {
  return new Promise((resolve, reject) => {
    const canvas = viewer.canvas;
    const previousCursor = canvas.style.cursor;
    canvas.style.cursor = "crosshair";

    const handler = new Cesium.ScreenSpaceEventHandler(canvas);

    const cleanup = () => {
      handler.destroy();
      canvas.style.cursor = previousCursor;
      document.removeEventListener("keydown", onKey);
    };

    const onKey = (e) => {
      if (e.key === "Escape") {
        cleanup();
        reject(new Error("cancelled"));
      }
    };
    document.addEventListener("keydown", onKey);

    handler.setInputAction((click) => {
      const cartesian = viewer.camera.pickEllipsoid(
        click.position,
        viewer.scene.globe.ellipsoid
      );
      if (!cartesian) return; // clicked sky; keep waiting
      const carto = Cesium.Cartographic.fromCartesian(cartesian);
      cleanup();
      resolve({
        lon: Cesium.Math.toDegrees(carto.longitude),
        lat: Cesium.Math.toDegrees(carto.latitude),
      });
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
  });
}
