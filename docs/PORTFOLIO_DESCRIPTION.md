# Portfolio description

Use this wording only after running the application and reviewing the results.

## CV entry

**Islamabad 3D Urban Intelligence Digital Twin — Open-source adaptation**

Adapted and extended an MIT-licensed 3D WebGIS architecture for Islamabad using CesiumJS, PostGIS and FastAPI. Reconfigured the project to UTM Zone 43N, built an offline OpenStreetMap PBF extraction workflow, processed Islamabad buildings and public facilities, added Docker-based deployment, and validated the adaptation with automated backend, CRS and frontend tests.

## LinkedIn or portfolio description

I reproduced and adapted an open-source 3D digital-twin architecture for Islamabad, Pakistan. The adaptation uses a CesiumJS frontend, FastAPI services and a PostGIS database to visualize 3D building footprints and support public-service accessibility, nearest-facility, emergency-routing, green-space and building-density analysis.

The Islamabad data pipeline extracts current OpenStreetMap features from a Pakistan PBF file, repairs geometries and calculates metric attributes in WGS 84 / UTM Zone 43N. Building heights derived from levels or defaults are explicitly marked as estimates. Traffic, parking and animated vehicles are demonstration simulations and are not presented as live official data.

Original project architecture by Dilux Logeswaran under the MIT licence. Islamabad-specific data preparation, CRS conversion, configuration, testing and deployment workflow were completed as an attributed adaptation with AI-assisted development.

**Stack:** CesiumJS · JavaScript · PostgreSQL/PostGIS · Python/FastAPI · Chart.js · OpenStreetMap · Open-Meteo · OSRM · Docker

## Interview preparation

Be ready to explain:

- Why EPSG:32643 is used for Islamabad metric analysis
- How building heights are estimated and labelled
- How PostGIS buffers and nearest-neighbour searches work
- Why straight-line accessibility differs from network accessibility
- Which layers are observed data and which are simulations
- Which parts came from the upstream architecture and which were adapted
