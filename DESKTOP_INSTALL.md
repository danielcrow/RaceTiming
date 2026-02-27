# Race Timing System — Desktop Installation Guide

This guide explains how to build and install the Race Timing System as a
standalone desktop application on macOS, Linux, or Windows.  
No Python installation is required on the target workstation.

---

## How it works

The packaging uses **PyInstaller** to bundle the Python interpreter, all
dependencies, Flask templates, and static assets into a single distributable
folder.  A `launcher.py` entry-point starts the Flask server on
`http://127.0.0.1:5001` and automatically opens the default browser.

Data (SQLite database, logs) is stored in a `data/` folder next to the
executable so it survives application updates.

---

## Building the package

### Prerequisites (build machine only)

| Requirement | Version |
|---|---|
| Python | 3.11 or later |
| pip | latest |
| Git (optional) | any |

> The target workstation does **not** need Python installed.

### macOS / Linux

```bash
# 1. Clone / copy the project
cd /path/to/RaceTiming

# 2. Run the build script
chmod +x build_desktop.sh
./build_desktop.sh
```

The distributable is created at `dist/RaceTimingSystem/`.

### Windows

```bat
REM 1. Open a Command Prompt in the project folder
REM 2. Double-click build_desktop.bat  OR  run:
build_desktop.bat
```

The distributable is created at `dist\RaceTimingSystem\`.

---

## Distributing to other workstations

1. Zip the entire `dist/RaceTimingSystem/` folder:

   ```bash
   # macOS / Linux
   zip -r RaceTimingSystem-mac.zip dist/RaceTimingSystem

   # Windows (PowerShell)
   Compress-Archive dist\RaceTimingSystem RaceTimingSystem-win.zip
   ```

2. Copy the zip to the target workstation and extract it anywhere (e.g.
   `C:\RaceTimingSystem` or `~/Applications/RaceTimingSystem`).

> **Important:** Build on the same OS as the target.  A macOS build will not
> run on Windows and vice-versa.

---

## First-run configuration

### Database

By default the application uses **SQLite** stored at `data/race_timing.db`
next to the executable — no setup required.

To use **PostgreSQL** instead, create a `.env` file next to the executable
(copy `.env.example` as a starting point) and set the database variables:

```dotenv
DB_HOST=localhost
DB_PORT=5432
DB_NAME=race_timing
DB_USER=postgres
DB_PASSWORD=your_password
```

### Results publishing URL

If you run the public results site, set `RESULTS_PUBLISH_URL` in `.env`:

```dotenv
RESULTS_PUBLISH_URL=https://your-results-site.example.com
WEBHOOK_SECRET=your-shared-secret
```

---

## Running the application

### macOS / Linux

```bash
./RaceTimingSystem/RaceTimingSystem
```

Or double-click the `RaceTimingSystem` executable in Finder / file manager.

### Windows

Double-click `RaceTimingSystem.exe` inside the extracted folder.

A console window will appear showing startup logs.  
The browser opens automatically at `http://127.0.0.1:5001`.

---

## Stopping the application

Close the console window, or press **Ctrl+C** in the terminal.

---

## Logs

Application logs are written to `data/race_timing.log` next to the executable.

---

## Updating

1. Build a new package from the updated source.
2. Extract the new zip alongside the existing installation.
3. Copy your existing `data/` folder (and `.env` if present) into the new
   folder to preserve your database and configuration.
4. Replace the old folder with the new one.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Browser does not open | Navigate manually to `http://127.0.0.1:5001` |
| Port 5001 already in use | Stop the other process, or set `PORT=5001` to a free port in `.env` (requires launcher code change) |
| `data/` folder missing | The launcher creates it automatically on first run |
| Database errors on startup | Check `data/race_timing.log` for details |
| Missing DLL on Windows | Install [Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe) |
| `libpq` not found (PostgreSQL) | Install PostgreSQL client libraries or switch to SQLite |

---

## File layout after extraction

```
RaceTimingSystem/
├── RaceTimingSystem          ← executable (macOS/Linux)
├── RaceTimingSystem.exe      ← executable (Windows)
├── .env.example              ← configuration template
├── data/                     ← created on first run
│   ├── race_timing.db        ← SQLite database
│   └── race_timing.log       ← application log
├── templates/                ← Flask HTML templates (bundled)
├── static/                   ← CSS / JS / images (bundled)
└── _internal/                ← PyInstaller runtime (do not modify)