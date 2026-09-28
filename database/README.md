# Database

PostgreSQL 15 + PostGIS 3.4 spatial database for the Islamabad digital twin.

- `schema/` — DDL scripts (tables, indexes, constraints), applied in numeric order.
- `queries/` — reusable analytical SQL (coverage, nearest-neighbor, accessibility).

Storage SRID: **4326** (WGS 84). Analysis SRID: **32643** (WGS 84 / UTM zone 43N) applied via `ST_Transform` inside queries — metric values are never computed in geographic coordinates.

Schema DDL, loader, ER diagram, and full documentation are produced in Milestone 3 (`schema/01_extensions.sql` onward, `docs/DATABASE.md`).
