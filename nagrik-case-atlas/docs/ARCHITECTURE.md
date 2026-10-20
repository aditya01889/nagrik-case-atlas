# Architecture and data contract

## Components

- `web/index.html`: public clean-atlas map and timeline. Uses MapLibre GL JS, Turf.js, a CARTO basemap and a published 543-feature parliamentary GeoJSON source. Public records are fetched from the same-origin FastAPI API.
- `web/admin.html`: token-gated editorial source/event review UI. The bearer token remains in page memory and is not saved to local storage.
- `backend/app/main.py`: public API, coverage and admin endpoints.
- `backend/app/models.py`: normalized SQLAlchemy schema.
- `backend/app/import_csv.py`: repeatable normalized CSV import.
- `backend/app/sync_boundaries.py`: source GeoJSON structure check and registration; new boundary versions are marked `unverified`.
- `backend/app/monitor.py`: optional integrity monitor for registered individual source documents. It hashes content, records checks and queues changed documents for review; it does not parse law or update a case outcome automatically.

## Public endpoints

- `GET /api/health`
- `GET /api/coverage`
- `GET /api/constituencies?legislature=&state=&q=`
- `GET /api/candidates?legislature=&constituency_name=&state=&as_of=&history_mode=known|corrected&sort=cases|serious|name`
- `GET /api/changes?since=&limit=`
- `GET /api/sources`
- `GET /docs` (OpenAPI)

## Admin endpoints

All `/api/admin/*` routes require `Authorization: Bearer $ADMIN_TOKEN`.

- `POST /api/admin/source-documents`
- `GET /api/admin/queue`
- `POST /api/admin/review-source/{source_id}`
- `POST /api/admin/review-event/{event_id}`

## Case-count semantics

The API returns `verified_case_count`, `declared_case_count` and `serious_case_count` separately. These are counts of distinct normalized case IDs linked to a candidate via a verified identity link. They are not claims of complete coverage. An appeal should normally be modelled as an event or linked proceeding, not blindly counted as a new underlying case. The import/review process must establish deduplication rules for related proceedings.

## Seriousness semantics

`is_serious` is a reviewed classification flag. `seriousness_rank` is optional, with 1 meaning highest severity under the project's documented classification framework. The API only names a “most serious” case when a reviewer has assigned a rank. Do not assign rank from an LLM summary alone.

## Historical semantics

- `event_date`: when a court/legal/political event happened.
- `recorded_at`: when the platform recorded/discovered it.
- `valid_from`/`valid_to`: validity period for a candidacy record.
- `as known then`: excludes cases created in the database after the selected date and events recorded after the selected date.
- `corrected historical view`: reconstructs from known event dates, and only includes cases with a filed date at or before the selected date.

Historical accuracy depends on reliable original event dates and preservation of source versions. Imported records added today cannot magically recreate what the platform knew years ago.
