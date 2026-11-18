# Admin dashboard update — current folder structure

Built against local commit a229051 (Merge pull request #6, feature/frontend-dashboard).

The existing React dashboard stays in frontend/app.
The separate admin panel goes in frontend/admin-dashbord (this exact spelling is intentional).
The admin panel is served by FastAPI at http://127.0.0.1:8000/panel.
It is not a React route and does not require npm. Both frontends share the repository; this package does not wire a navigation link into the React app.

## Install

1. Use this ZIP instead of the earlier MachGuard_Admin_Panel.zip.
2. In your friend's current repository, commit or back up existing work.
3. Extract directly into the repo root: the folder already containing backend, frontend and README.md.
4. Choose Replace when prompted for backend/app/main.py. If that file has newer changes, compare and merge first.
5. Do not extract into frontend or frontend/app. Do not create an extra nested ZIP-name folder.
6. frontend/admin-dashbord is created automatically by extraction.

PowerShell alternative — edit both paths to match her computer:

```powershell
$zipPath = "$env:USERPROFILE\Downloads\MachGuard_Admin_Dashboard_v2.zip"
$repoPath = "E:\TransitionX\mechguard"
if (!(Test-Path -LiteralPath "$repoPath\backend\app\main.py")) {
    throw "Select the existing repository root."
}
Expand-Archive -LiteralPath $zipPath -DestinationPath $repoPath -Force
```

The ZIP only replaces backend/app/main.py. It adds:
- backend/app/registry_routes.py
- backend/check_registry.py
- frontend/admin-dashbord/index.html
- frontend/admin-dashbord/styles.css
- frontend/admin-dashbord/app.js
- docs/ADMIN_PANEL_GUIDE.md
- docs/INSTALL_ADMIN_PANEL.md

It does not include README.md, frontend/app files, .git, .env, databases, virtual environments or private material.
If an earlier version was already installed, compare existing files before replacing; this ZIP does not delete old root-level frontend files.

## Run

Open a terminal inside backend:

```powershell
.\venv\Scripts\python.exe check_auth.py
.\venv\Scripts\python.exe check_registry.py
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

If no venv exists, first run:

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

Open http://127.0.0.1:8000/panel and sign in as admin.
To create an administrator only if needed, run from backend:

```powershell
.\venv\Scripts\python.exe -m app.create_admin
```

Try: add a category, add an engineer, add a machine, edit its status or assignment, create a maintenance report.
Use compressor-1 for a machine intended to match the simulator's default ID.

Engineer entries are staff records, not login accounts. Working-machine counts are manually entered statuses, not live telemetry.
Browser refresh requires signing in again; saved records remain in SQLite.
Uploads, device keys and AI widgets are not part of this panel. Existing simulator/reading endpoint security is unchanged.

## Five commits

Run from the repository root, after extraction and tests:

```powershell
git add backend/app/registry_routes.py
git commit -m "feat: add protected machine and engineer registry"

git add frontend/admin-dashbord/index.html frontend/admin-dashbord/styles.css frontend/admin-dashbord/app.js
git commit -m "feat: add separate admin dashboard under frontend"

git add backend/app/main.py
git commit -m "feat: serve admin dashboard and connect registry routes"

git add backend/check_registry.py
git commit -m "test: cover registry access control and record management"

git add docs/ADMIN_PANEL_GUIDE.md docs/INSTALL_ADMIN_PANEL.md
git commit -m "docs: add admin dashboard installation and source guide"
```

Review git status and git diff before pushing to the team's intended branch.
