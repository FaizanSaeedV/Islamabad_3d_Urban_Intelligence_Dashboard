# Islamabad adaptation status

This branch adapts the upstream Islamabad digital-twin project for Islamabad, Pakistan.

## Completed

- Islamabad study-area bounds and camera configuration
- Metric analysis CRS changed to WGS 84 / UTM zone 43N (EPSG:32643)
- Pakistan coordinate validation and Islamabad weather configuration
- Islamabad branding, place search, and demonstration routes
- OSM pipeline bounds and synthetic test fixtures updated
- Core backend and frontend logic tests passing
- Original MIT licence and upstream attribution preserved

## In progress

- Acquisition of current Islamabad OSM layers
- PostGIS load and database-backed integration tests
- Islamabad-specific documentation and screenshots
- Deployment configuration and public hosting

## Data integrity

Traffic, parking, EV availability, and animated vehicles are demonstrative simulation layers and must remain labelled as simulated. Building heights inferred from levels or defaults are estimates, not survey measurements. Results derived from OpenStreetMap depend on local mapping completeness and the acquisition date.
