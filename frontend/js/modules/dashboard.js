/**
 * Urban analytics dashboard: stat tiles + Chart.js charts fed by /api/analytics.
 */
import { apiGet } from "./api.js";

/* global Chart */

const PALETTE = ["#4f8ef7", "#35c4a2", "#e0a24f", "#e2604f", "#b085c9",
                 "#c9d84f", "#57a8d8", "#c98f6a", "#7d8aa8", "#d8b447"];

const TILE_DEFS = [
  ["total_buildings", "Buildings", ""],
  ["road_length_km", "Road network", " km"],
  ["hospitals", "Hospitals", ""],
  ["schools", "Schools", ""],
  ["fuel_stations", "Fuel stations", ""],
  ["ev_charging_stations", "EV chargers", ""],
  ["parking_locations", "Parking", ""],
  ["bus_stops", "Bus stops", ""],
  ["green_spaces", "Green spaces", ""],
  ["green_area_ha", "Green area", " ha"],
];

function applyChartTheme() {
  Chart.defaults.color = "#9fb0ce";
  Chart.defaults.borderColor = "#2a3655";
  Chart.defaults.font.size = 11;
  Chart.defaults.plugins.legend.labels.boxWidth = 10;
}

function statTiles(container, totals) {
  const grid = document.createElement("div");
  grid.className = "stat-grid";
  for (const [key, label, unit] of TILE_DEFS) {
    const value = totals[key];
    if (value === undefined) continue;
    grid.insertAdjacentHTML("beforeend", `
      <div class="stat-tile">
        <div class="stat-value">${Number(value).toLocaleString()}${unit}</div>
        <div class="stat-label">${label}</div>
      </div>`);
  }
  container.appendChild(grid);
}

function chartBlock(container, title, note = "") {
  const block = document.createElement("div");
  block.className = "chart-block";
  block.innerHTML = `<h3>${title}</h3><canvas></canvas>${note ? `<p class="panel-note">${note}</p>` : ""}`;
  container.appendChild(block);
  return block.querySelector("canvas");
}

function doughnut(canvas, data) {
  new Chart(canvas, {
    type: "doughnut",
    data: {
      labels: data.labels,
      datasets: [{ data: data.values, backgroundColor: PALETTE, borderWidth: 0 }],
    },
    options: { plugins: { legend: { position: "bottom" } }, cutout: "55%" },
  });
}

function bars(canvas, data, { horizontal = false, color = "#4f8ef7" } = {}) {
  new Chart(canvas, {
    type: "bar",
    data: {
      labels: data.labels,
      datasets: [{ data: data.values, backgroundColor: color, borderRadius: 3 }],
    },
    options: {
      indexAxis: horizontal ? "y" : "x",
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { display: !horizontal } },
        y: { grid: { display: horizontal } },
      },
    },
  });
}

export async function initDashboard() {
  const container = document.getElementById("analytics-content");
  container.innerHTML = "<p class='panel-note'>Loading analytics…</p>";
  let data;
  try {
    data = await apiGet("/api/analytics");
  } catch (err) {
    container.innerHTML = `
      <p class="panel-note">Analytics unavailable: ${err.message}.
      Load the database (Milestone 3) and start the backend, then reload.</p>`;
    return;
  }

  applyChartTheme();
  container.innerHTML = "";
  statTiles(container, data.totals);

  doughnut(
    chartBlock(container, "Building height distribution", data.height_classification_note),
    data.building_height_classes
  );
  bars(chartBlock(container, "Building types (top 8)"), data.building_types,
       { horizontal: true, color: "#4f8ef7" });
  bars(chartBlock(container, "Facility distribution"), data.facility_distribution,
       { horizontal: true, color: "#35c4a2" });
  doughnut(chartBlock(container, "Land-use distribution (ha)"), data.landuse_distribution);
  bars(chartBlock(container, "Smart mobility infrastructure"), data.mobility_infrastructure,
       { horizontal: true, color: "#e0a24f" });

  container.insertAdjacentHTML("beforeend",
    `<p class="panel-note">Generated ${new Date(data.generated_at).toLocaleString()} ·
     data © OpenStreetMap contributors (ODbL)</p>`);
}
