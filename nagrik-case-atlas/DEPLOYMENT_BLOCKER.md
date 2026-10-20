# Deployment status and required action

This package is prepared for GitHub Pages, but it has **not** been published. The available GitHub integration in the current session can commit files to existing repositories, but it does not expose a create-repository operation or the Pages settings API. To avoid placing this project into an unrelated existing repository, repository creation must be completed by the account owner or via a GitHub connection with repository-creation permissions.

Even after the frontend is published, the full live data service requires separately hosted API/database infrastructure and verified data ingestion. GitHub Pages is static hosting and cannot run FastAPI, PostgreSQL, or the background monitoring worker.
