/**
 * UI wiring: sidebar tabs, fullscreen, backend status indicator, search.
 * Search uses OSM Nominatim (free, no key; usage policy: max 1 req/sec,
 * results limited to the Islamabad bounding box).
 */
import { CONFIG } from "../config.js";
import { flyToLocation } from "./viewer.js";

export function initSidebarTabs() {
  const tabs = document.querySelectorAll(".tab-btn");
  const panels = document.querySelectorAll(".panel");
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.remove("active"));
      panels.forEach((p) => p.classList.remove("active"));
      tab.classList.add("active");
      document.getElementById(tab.dataset.panel).classList.add("active");
    });
  });
}

export function initFullscreen() {
  document.getElementById("btn-fullscreen").addEventListener("click", () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen();
    } else {
      document.exitFullscreen();
    }
  });
}

/** Ping the backend and update the API status chip. */
export async function checkBackendStatus() {
  const chip = document.getElementById("api-status");
  try {
    const res = await fetch(`${CONFIG.API_BASE_URL}/api/health`, { signal: AbortSignal.timeout(5000) });
    const data = await res.json();
    if (res.ok && data.status === "ok") {
      const dbOk = data.database && data.database.connected;
      chip.textContent = dbOk ? "API: online" : "API: online (no DB)";
      chip.className = `status-chip ${dbOk ? "status-ok" : "status-warn"}`;
    } else {
      throw new Error("unhealthy");
    }
  } catch {
    chip.textContent = "API: offline";
    chip.className = "status-chip status-err";
  }
}

/** Place search restricted to the Islamabad bounding box (Nominatim). */
export function initSearch(viewer) {
  const input = document.getElementById("search-input");
  const btn = document.getElementById("search-btn");
  const list = document.getElementById("search-results");
  const bb = CONFIG.STUDY_AREA.boundingBox;

  async function runSearch() {
    const q = input.value.trim();
    if (q.length < 2) return;
    const url =
      "https://nominatim.openstreetmap.org/search?format=jsonv2&limit=6" +
      `&viewbox=${bb.west},${bb.north},${bb.east},${bb.south}&bounded=1` +
      `&q=${encodeURIComponent(q)}`;
    try {
      const res = await fetch(url, { headers: { Accept: "application/json" } });
      const results = await res.json();
      list.innerHTML = "";
      if (!results.length) {
        list.innerHTML = "<li class='no-result'>No results in Islamabad</li>";
      }
      results.forEach((r) => {
        const li = document.createElement("li");
        li.textContent = r.display_name;
        li.addEventListener("click", () => {
          flyToLocation(viewer, parseFloat(r.lon), parseFloat(r.lat));
          list.classList.add("hidden");
          input.value = r.display_name.split(",")[0];
        });
        list.appendChild(li);
      });
      list.classList.remove("hidden");
    } catch (err) {
      console.warn("Search failed:", err);
    }
  }

  btn.addEventListener("click", runSearch);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") runSearch();
  });
  document.addEventListener("click", (e) => {
    if (!e.target.closest("#search-container")) list.classList.add("hidden");
  });
}
