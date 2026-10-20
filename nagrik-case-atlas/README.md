# Nagrik Case Atlas

A constituency-based, source-first public-interest explorer for disclosed criminal cases and verified court records involving political candidates in India.

## Current state

This repository package contains the interactive static frontend, the FastAPI/PostgreSQL backend source, data import templates, source-monitor worker, operational/data-policy documentation, tests, and a GitHub Pages deployment workflow.

**Important:** the Pages frontend alone is not a live nationwide case-monitoring service. GitHub Pages only hosts static files. To display verified case records, deploy the backend and PostgreSQL/PostGIS database separately, import validated source-linked records, and set `window.NCA_API_BASE` in `site/site-config.js` to the deployed API origin. The current API endpoint is intentionally blank, and no fictional candidate or criminal-case data is included.

## Publish on GitHub Pages

1. Create a new public GitHub repository named `nagrik-case-atlas` under `aditya01889`.
2. Upload the contents of this package to the repository root (including the `.github/workflows/pages.yml` file).
3. Ensure the default branch is `main` or `master`, then open **Actions** and allow the Pages workflow to run.
4. If prompted, enable GitHub Pages with **Build and deployment → Source: GitHub Actions**.
5. The deployment job will display the live URL when successful. For a project repository it should be `https://aditya01889.github.io/nagrik-case-atlas/`.

## Local frontend preview

Open `site/index.html` in a browser with an internet connection. MapLibre, the Carto basemap, Turf.js and constituency boundary GeoJSON are loaded from external public sources. Browser geolocation requires permission and a secure context (localhost or HTTPS).

## Backend

See `docs/DEPLOYMENT.md`, `docs/ARCHITECTURE.md`, `docs/DATA_POLICY.md`, and `docs/OPERATIONS.md`. Never import unverified allegations as confirmed case records. Counts must be deduplicated, linked to source documents, dated, and distinguished by procedural status; allegations are not findings of guilt.
