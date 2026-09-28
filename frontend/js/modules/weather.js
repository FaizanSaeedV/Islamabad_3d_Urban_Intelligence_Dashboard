/**
 * Real-time weather card (Open-Meteo via backend proxy).
 *
 * Spatial note: Open-Meteo returns a point forecast for central Islamabad
 * (33.6844 N, 73.0479 E). Interpolating a single point spatially would
 * fabricate variation, so the card states the reference point instead.
 */
import { CONFIG } from "../config.js";
import { apiGet } from "./api.js";

// WMO weather interpretation codes (Open-Meteo docs)
export function weatherDescription(code) {
  if (code === 0) return { text: "Clear sky", icon: "☀" };
  if (code >= 1 && code <= 2) return { text: "Partly cloudy", icon: "⛅" };
  if (code === 3) return { text: "Overcast", icon: "☁" };
  if (code === 45 || code === 48) return { text: "Fog", icon: "🌫" };
  if (code >= 51 && code <= 57) return { text: "Drizzle", icon: "🌦" };
  if (code >= 61 && code <= 67) return { text: "Rain", icon: "🌧" };
  if (code >= 80 && code <= 82) return { text: "Rain showers", icon: "🌧" };
  if (code >= 95) return { text: "Thunderstorm", icon: "⛈" };
  return { text: "—", icon: "•" };
}

export function windCompass(deg) {
  if (deg === null || deg === undefined) return "—";
  const dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"];
  return dirs[Math.round(deg / 22.5) % 16];
}

function row(label, value) {
  return value === null || value === undefined
    ? ""
    : `<div class="wx-row"><span>${label}</span><strong>${value}</strong></div>`;
}

async function refresh(card, body) {
  try {
    const w = await apiGet("/api/weather");
    const desc = weatherDescription(w.weather_code);
    body.innerHTML = `
      <div class="wx-main">
        <span class="wx-icon">${desc.icon}</span>
        <span class="wx-temp">${w.temperature_c != null ? `${w.temperature_c.toFixed(1)}°C` : "—"}</span>
        <span class="wx-desc">${desc.text}${w.is_day === false ? " (night)" : ""}</span>
      </div>
      ${row("Humidity", w.humidity_pct != null ? `${w.humidity_pct}%` : null)}
      ${row("Rainfall", w.precipitation_mm != null ? `${w.precipitation_mm} mm` : null)}
      ${row("Cloud cover", w.cloud_cover_pct != null ? `${w.cloud_cover_pct}%` : null)}
      ${row("Wind", w.wind_speed_kmh != null
          ? `${w.wind_speed_kmh} km/h
             <span class="wx-arrow" style="transform:rotate(${(w.wind_direction_deg ?? 0) + 180}deg)">↑</span>
             ${windCompass(w.wind_direction_deg)}`
          : null)}
      <div class="wx-footer">Point forecast @ 33.68 N, 73.05 E ·
        ${new Date(w.fetched_at).toLocaleTimeString()} · Open-Meteo (CC BY 4.0)</div>`;
    card.classList.remove("hidden");
  } catch (err) {
    body.innerHTML = `<p class="panel-note">Weather unavailable: ${err.message}</p>`;
    card.classList.remove("hidden");
  }
}

export function initWeather() {
  const card = document.getElementById("weather-card");
  const body = document.getElementById("weather-body");
  refresh(card, body);
  setInterval(() => refresh(card, body), CONFIG.WEATHER_REFRESH_MS);
}
