# Deployment status

The source tree has been imported into the public GitHub repository. The static frontend is prepared for GitHub Pages, but the Pages workflow currently cannot enable the Pages site because the workflow token lacks permission to create the Pages site. In the repository settings, set Settings → Pages → Build and deployment → Source to GitHub Actions, then rerun the Pages workflow.

The live data service is not yet operational: it requires separately hosted API/database infrastructure and verified data ingestion. GitHub Pages is static hosting and cannot run FastAPI, PostgreSQL, or the background monitoring worker.
