# Frontend Manual Testing Checklist

Prerequisites: PostGIS loaded (M3), backend on :8000, frontend on :5500.
Test in Chrome/Edge/Firefox at desktop width, then at < 860 px width.

## 1. Core viewer

- [ ] Page loads; camera flies to a tilted view over Islamabad
- [ ] Top-right chip shows **API: online** (green)
- [ ] Zoom (wheel/right-drag), pan (left-drag), rotate+tilt (middle/Ctrl-drag) all work
- [ ] ⌂ resets the camera; **N** faces north; **3D/2D** toggles top-down view
- [ ] Fullscreen button enters/exits fullscreen
- [ ] Search "Galle Face" → result list appears → clicking flies to location
- [ ] OSM attribution visible in footer

## 2. Layers tab

- [ ] Buildings/water/green load automatically with feature counts
- [ ] Buildings are extruded; colours vary (steel-blue/blue/teal by height)
- [ ] Clicking a building opens attributes; estimated heights say *estimated*/*assumed*
- [ ] No invented attributes (unnamed buildings show no name row)
- [ ] Ticking Roads streams the network; classes have different colours/widths
- [ ] Each facility layer loads and shows count; points visible over buildings
- [ ] Un-tick/re-tick a layer: hides instantly, re-shows without re-downloading

## 3. Weather card

- [ ] Card appears with temperature, condition, humidity, rain, cloud, wind
- [ ] Wind arrow rotates to a plausible direction; compass label sensible
- [ ] Footer shows fetch time + Open-Meteo attribution

## 4. Analytics tab

- [ ] Stat tiles populated (buildings, road km, hospitals, …)
- [ ] All five charts render; height classes sum equals total buildings
- [ ] Tooltips work on hover

## 5. Tools tab — Nearest Facility

- [ ] Pick location → 5 ranked markers + list with distances (ascending)
- [ ] Route button draws glowing route; summary shows road distance, time, straight line
- [ ] Esc during pick cancels cleanly

## 6. Tools tab — Emergency Response

- [ ] Set incident → ⚠ marker + three colour-coded routes toward the incident
- [ ] Cards show straight-line, road distance, travel time for each service
- [ ] Free-flow disclaimer visible
- [ ] With backend stopped mid-test: clean error message, no crash

## 7. Tools tab — Measurement

- [ ] Distance: vertices → running geodesic total; right-click finishes
- [ ] Area: ≥3 vertices → polygon + total in m²/ha/km² (test Galle Face Green ≈ 5 ha)
- [ ] Height: click building → attribute height with source note; click non-building → hint
- [ ] Clear removes all measurement graphics

## 8. Tools tab — Spatial Query / Analysis

- [ ] "Buildings near hospital 500 m" highlights buildings + count
- [ ] "Facilities within radius of point" works with pick; "near major roads" returns results
- [ ] Density grid renders with legend; dense core visibly red (Pettah/Fort)
- [ ] Accessibility grid: green near parks, red in park-poor areas
- [ ] Coverage: service area polygon + underserved % consistent when radius grows (% falls)

## 9. Twin tab

- [ ] Disclaimer banner visible: "Simulated for Digital Twin Demonstration"
- [ ] Traffic toggle auto-loads roads and recolours them; legend counts shown
- [ ] Parking/EV overlays show status points; popups carry the SIM warning
- [ ] Status values change over a few minutes (engine ticks every 60 s)
- [ ] Time demo: vehicles animate along roads; timeline scrubs; Stop cleans up

## 10. Degradation

- [ ] Backend stopped → chip goes red **API: offline**; panels show guidance, no JS errors
- [ ] Database stopped (backend up) → chip **online (no DB)**; layer loads report cleanly
- [ ] Browser console free of uncaught exceptions during all of the above

## 11. Responsive (< 860 px)

- [ ] Sidebar collapses; map fills width; floating cards shrink; no overlap
