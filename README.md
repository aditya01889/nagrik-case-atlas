# Nagrik Case Atlas

A public-interest constituency explorer for source-linked disclosures of criminal cases in Indian elections. **An allegation is not a finding of guilt.**

## Source code

The complete application source is committed in the [nagrik-case-atlas/](./nagrik-case-atlas/) directory. Start with [START_HERE.md](./nagrik-case-atlas/START_HERE.md), then see the architecture, data policy, deployment, and operations documents under [nagrik-case-atlas/docs/](./nagrik-case-atlas/docs/).

## GitHub Pages

A GitHub Actions workflow publishes the static frontend from [nagrik-case-atlas/site/](./nagrik-case-atlas/site/). Deployment status is visible in the [Actions tab](./actions).

## Important data limitation

The project does not ship with a verified, complete live national case database. Live API functionality requires a separately hosted backend, database, and verified source ingestion. Do not interpret the map as complete nationwide reporting until those components are configured and validated.
