# Windows Setup Guide — Step by Step
## Fixes all known issues on Windows PowerShell + Python 3.14

---

## Prerequisites — install these first

### Check what you have
Open PowerShell and run:
```powershell
python --version
node --version
npm --version
```

### If Python is missing or below 3.10
Download Python 3.11 (recommended — best compatibility):
  https://www.python.org/downloads/release/python-3119/
  - Click: Windows installer (64-bit)
  - During install: CHECK "Add python.exe to PATH"
  - CHECK "pip" option

### If Node.js / npm is missing ("npm is not recognized")
Download Node.js LTS:
  https://nodejs.org/en/download
  - Click: Windows Installer (.msi) — LTS version
  - Install with defaults
  - Restart PowerShell after install

---

## Fix: PowerShell script execution blocked
If you see: "running scripts is disabled on this system"
Run this ONCE in PowerShell as Administrator:
```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force
```
Then close and reopen PowerShell.

---

## Full setup — copy and paste each block

### Block 1 — Navigate to project
```powershell
# Unzip the file first, then:
cd C:\Users\pavit\Downloads\hiring-agent-v2-fixed\hiring-agent-v2
```

### Block 2 — Copy env and set Groq key
```powershell
Copy-Item .env.example .env
python scripts/switch_provider.py poc
python scripts/switch_provider.py set-groq gsk_YOUR_GROQ_KEY_HERE
```
Get free Groq key at: https://console.groq.com

### Block 3 — Create venv and install backend
```powershell
cd backend
python -m venv venv
```

Activate venv (use one of these — whichever works):
```powershell
# Option A (PowerShell — needs execution policy fix above)
.\venv\Scripts\Activate.ps1

# Option B (always works — uses cmd.exe inside PowerShell)
cmd /c "venv\Scripts\activate.bat && pip install -r requirements.txt && exit"
```

If Option B worked, continue in the same window:
```powershell
venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Block 4 — Seed mock data
```powershell
# Still in backend folder, venv active:
cd ..
venv\Scripts\python.exe scripts/seed_mock.py
```

### Block 5 — Start backend
```powershell
cd backend
venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000
```
Test: open http://localhost:8000/docs in your browser

### Block 6 — Start frontend (open a NEW PowerShell window)
```powershell
cd C:\Users\pavit\Downloads\hiring-agent-v2-fixed\hiring-agent-v2\frontend
npm install
npm run dev
```
Open: http://localhost:5173

---

## Troubleshooting

| Error | Fix |
|---|---|
| `running scripts is disabled` | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` as Admin |
| `npm is not recognized` | Install Node.js from nodejs.org, restart PowerShell |
| `No module named sqlalchemy` | Pip install failed — use `venv\Scripts\python.exe -m pip install -r requirements.txt` |
| `uvicorn is not recognized` | Use `venv\Scripts\python.exe -m uvicorn` instead of just `uvicorn` |
| `langchain-chroma version error` | Updated requirements.txt fixes this |
| `can't open file scripts/seed_mock.py` | You're in the wrong folder — must be in `hiring-agent-v2/` not `backend/` |
| Python 3.14 package errors | Install Python 3.11 from python.org (3.14 is too new, packages lag) |

---

## Quick reference — all commands using full paths (most reliable on Windows)

```powershell
# From hiring-agent-v2 folder with venv created:

# Install packages
backend\venv\Scripts\python.exe -m pip install -r backend\requirements.txt

# Seed mock data
backend\venv\Scripts\python.exe scripts\seed_mock.py

# Start backend
backend\venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000
# (run this from the backend folder)

# Start frontend (separate window)
cd frontend && npm install && npm run dev
```
