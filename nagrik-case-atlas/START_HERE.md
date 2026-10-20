# Start here

You do not need to do anything from your phone right now. This ZIP is the source package to keep for when you are back at a computer.

## What this package contains

- Public clean-atlas map interface.
- FastAPI record API and database schema.
- Source-document and legal-event review page (`/admin`).
- CSV templates and boundary sync utility.
- Optional source integrity monitor.
- Deployment, data policy and operations notes.

## What it does not contain yet

- No fabricated politician names or criminal allegations.
- No populated national case database.
- No verified national Assembly boundary layer in the UI.
- No nationwide automated discovery of every new case or FIR.
- No public hosted URL. A hosting account and an editorially verified dataset are needed for that.

## When you are back at a computer

1. Download and extract `india_constituency_explorer_fullstack.zip`.
2. Install Docker Desktop.
3. Copy `.env.example` to `.env` and change the example secrets.
4. Run `START_WINDOWS.bat` on Windows, or `./start_mac_linux.sh` on macOS/Linux.
5. Open `http://localhost:8000`.
6. Open `http://localhost:8000/docs` for the API or `http://localhost:8000/admin` for source review.

The map requires internet access for MapLibre, the basemap and the remote constituency GeoJSON. The app/API runs locally. Public records only appear after a reviewed import; an empty result is not a claim that no cases exist.
