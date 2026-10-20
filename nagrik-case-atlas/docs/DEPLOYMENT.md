# Deployment notes

## Local development

Use Docker Compose. The database persists in a named volume. Do not expose the admin routes to the public internet without TLS, a strong `ADMIN_TOKEN`, rate limiting, and access controls.

## Production

A public deployment requires an account and a deployment target controlled by the project owner; this package does not contain credentials and has not been published to a public URL. Recommended baseline:

- Managed PostgreSQL/PostGIS with automated backups and restore tests.
- HTTPS reverse proxy and security headers.
- Separate app and worker services.
- Secrets stored in the hosting provider's secret manager, never committed to Git.
- Restricted admin access, token rotation, rate limits and audit logs.
- Monitoring for failed jobs, stale sources, API errors and backup failures.
- Versioned boundary artefacts and a documented rollback plan.
- Legal/editorial review before publishing individual criminal-case allegations.

## Current limitation

No national candidate/case feed is preloaded. Official ECI affidavit data is published per nomination/election, and eCourts public services provide search and case/order access rather than one unrestricted real-time API for this product's complete workflow. A reliable public service needs a maintained identity-resolution and review operation. Do not label the service “live nationwide” until that coverage exists and is measured.
