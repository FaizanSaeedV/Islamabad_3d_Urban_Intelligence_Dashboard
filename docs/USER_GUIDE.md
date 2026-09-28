# User Guide

## The interface

- **Top bar** — place search (Islamabad-bounded), backend status chip, fullscreen.
- **Left sidebar** — four tabs: **Layers**, **Analytics**, **Tools**, **Twin**.
- **Map** — full-screen 3D globe. **Right panel** — live weather card.
- **Bottom-right buttons** — ⌂ reset camera · N face north · 3D/2D tilt toggle.

**Navigation:** left-drag pan · wheel or right-drag zoom · middle-drag (or Ctrl+drag) rotate & tilt.

## Layers tab

Tick a layer to load it (first activation downloads it; count appears when ready). Buildings are 3D — colour = height class (steel-blue low-rise < 12 m, blue mid-rise, teal high-rise > 30 m). **Click any feature** for its attributes; estimated heights are labelled as estimates.

## Analytics tab

City statistics (building count, road km, facility counts, green area) and five charts. Height classes always sum to the total building count.

## Tools tab

- **Nearest Facility** — choose a type, *Pick location on map*, click anywhere: the 5 nearest appear ranked with distances. *Route* draws the road route with distance and estimated time (free-flow — no live traffic).
- **Emergency Response** — *Set incident location*, click the map: nearest hospital, police and fire station are found simultaneously, each with straight-line distance, road distance, travel time, and a colour-coded response route (red/blue/orange).
- **Measurement** — *Distance*: click vertices, right-click to finish (geodesic metres/km). *Area*: ≥3 vertices (m²/ha/km²). *Height*: click a building — reports its data height with the source. *Esc* cancels any mode.
- **Spatial Query** — three templates (buildings near a facility type · facilities around a picked point · facilities near major roads); results are highlighted amber; *Clear* removes them.
- **Building Density / Green-Space Accessibility / Infrastructure Coverage** — one-click analytical overlays with legends. Red accessibility cells are > 1 km from any green space; the coverage card reports the share of buildings outside the chosen service buffer.

## Twin tab

⚠ Everything here is **Simulated for Digital Twin Demonstration** — a clearly-labelled synthetic layer, not real telemetry.

- **Traffic status** recolours roads (green → red); states evolve every ~60 s.
- **Parking occupancy** and **EV charger availability** show status-coloured points; click for details (all popups repeat the SIM warning).
- **Time-Based Demo** animates a bus and an emergency vehicle along real road routes — timeline and playback controls appear at the bottom; scrub, change speed, or *Stop* to clean up.

## Tips

- If the status chip shows *offline*, start the backend (see INSTALLATION.md); on the free-tier demo the first request can take a minute (server waking).
- Layers stay cached after first load — toggling is instant.
- Attribute panels omit anything not mapped in OpenStreetMap rather than guessing.
