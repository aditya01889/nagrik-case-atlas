# Deploy the Nagrik Case Atlas API to Vercel

## Vercel project settings

- Import the GitHub repository: `aditya01889/nagrik-case-atlas`.
- Set **Root Directory** to `nagrik-case-atlas/backend`.
- Leave the framework preset as **Other** (Vercel should detect the Python function).
- The entrypoint is `api/index.py`; dependencies are in `requirements.txt`.

## Required environment variables

Set these in Vercel Project Settings → Environment Variables for Production (and Preview if desired):

- `DATABASE_URL`: a managed PostgreSQL connection string. Use a provider's serverless/pooler URL if provided. Never use SQLite for production; Vercel function filesystems are ephemeral.
- `CORS_ORIGINS`: `https://aditya01889.github.io`
- `ADMIN_TOKEN`: a long, random secret. Keep it private and do not put it in the frontend or GitHub.
- Optional `ALLOWED_SOURCE_HOSTS`: comma-separated official source host allowlist.

After adding or changing variables, redeploy the project.

## Verify deployment

Open `https://YOUR-VERCEL-DOMAIN/api/health`. A healthy response should report database `ok`. If the API responds with a database error, confirm `DATABASE_URL` is set and that the database allows connections from Vercel.

## Connect the GitHub Pages frontend

After the Vercel deployment is successful, update `site/site-config.js` in the repository to set:

```js
window.NCA_API_BASE = 'https://YOUR-VERCEL-DOMAIN';
```

Use only the deployed HTTPS origin, with no trailing path. Commit the change and wait for GitHub Pages to redeploy.

## Important limits

- Vercel hosts the request/response API; it is not a persistent database or a reliable always-on background worker.
- The source-monitor worker should run separately on a scheduled worker/cron service and must be configured with official sources and a human review process.
- The database starts empty. Do not describe the atlas as complete or live nationwide until verified source-linked records and coverage are actually loaded.
- Never publish allegations as findings of guilt.
