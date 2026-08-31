---
name: run-proyecto-2
description: Build, run, and drive the proyecto_2 to-do app (FastAPI API + Streamlit UI) on this Windows machine. Use when asked to run, start, launch, test, smoke-test, or screenshot proyecto_2 / app_ui.py / the todo API or panel.
---

Two processes make up this app, and both must be running:

- **API** (`src/main.py`, FastAPI + SQLite `todos.db`) on `http://localhost:8000`
- **UI** (`app_ui.py`, Streamlit) on `http://localhost:8501`, which talks to the
  API over HTTP (`TODO_API_URL`, default `http://localhost:8000/api/todos`)

All paths below are relative to the repo root (`proyecto_2/`). The venv at
`venv/` already has all of `requirements.txt` plus Playwright + Chromium
installed (see Prerequisites if starting from a fresh venv).

## Prerequisites

Already installed in `venv/`. If setting up fresh:

```
venv/Scripts/python.exe -m pip install -r requirements.txt
venv/Scripts/python.exe -m pip install playwright
venv/Scripts/python.exe -m playwright install chromium
```

## Run (agent path)

**Important (Windows/git-bash):** a plain `cmd &` background job dies as
soon as its Bash tool call returns. Launch with `nohup ... < /dev/null &`
followed by `disown -a` in the *same* tool call so the process detaches
and survives across tool calls:

```bash
nohup ./venv/Scripts/python.exe -m uvicorn src.main:app --host 0.0.0.0 --port 8000 > uvicorn.log 2>&1 < /dev/null &
disown -a
```

```bash
nohup ./venv/Scripts/python.exe -m streamlit run app_ui.py --server.headless true --server.port 8501 > streamlit.log 2>&1 < /dev/null &
disown -a
```

Wait ~3-5s, then confirm both are up:

```bash
curl -s http://localhost:8000/api/todos
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8501
```

### Drive it: `driver.py`

`.claude/skills/run-proyecto-2/driver.py` has two commands.

**`smoke`** — exercises the full API CRUD cycle over HTTP (this is what
`app_ui.py` itself calls under the hood, and what most PRs touch):

```bash
./venv/Scripts/python.exe .claude/skills/run-proyecto-2/driver.py smoke
```

Does create -> list (asserts new id present) -> PATCH to `done` -> DELETE
-> GET returns 404. Prints `SMOKE OK` on success, raises `AssertionError`
on the first mismatch.

**`screenshot [path]`** — launches headless Chromium via Playwright, opens
the running Streamlit UI, waits for the page heading to render (Streamlit
paints over a websocket after the initial HTML shell, so a raw `curl` of
`/` only shows the empty React shell — this is why a browser driver is
needed here, not `curl`), and saves a full-page PNG (default
`ui_screenshot.png`):

```bash
./venv/Scripts/python.exe .claude/skills/run-proyecto-2/driver.py screenshot ui_screenshot.png
```

Requires both the API and the UI to already be running.

## Run (human path)

Same two commands as above but without `nohup`/`disown`/`> log` — run each
in its own terminal, `Ctrl-C` to stop. Streamlit opens a browser tab
automatically; drop `--server.headless true` for that.

## Test

```bash
./venv/Scripts/python.exe -m pytest
```

(`pytest.ini` sets `testpaths = tests`; `tests/test_todos.py` hits the API
via `httpx`/FastAPI's TestClient, not the running server.)

## Gotchas

- **Background jobs die silently without `disown -a`.** A `cmd > log 2>&1 &`
  launched via the Bash tool looks like it started (you get a PID), but the
  process is a child of that tool call's shell and is reaped the moment the
  call returns — the next `curl` gets `exit code 7` (connection refused)
  even though `uvicorn.log`/`streamlit.log` show a clean startup. Always
  pair the `&` with `disown -a` in the same tool call, and always redirect
  stdin from `/dev/null` too, or the child can still block on tty.
- **`curl` on the Streamlit UI only ever shows the static shell.** The
  actual todo table, counters, and buttons are painted client-side after a
  websocket connects, so `curl http://localhost:8501/` proves the server
  is alive but proves nothing about what's rendered. Use
  `driver.py screenshot` to see real content, not the HTML fetch.
- **Streamlit's `wait_for_selector` needs a specific string**, not just
  `networkidle` — Playwright's `networkidle` fires on the shell load, well
  before Streamlit's websocket has pushed the actual page content, so a
  screenshot taken right after `goto()` is a blank dark page. Wait for a
  known heading (`text=Panel de control de tareas`) first.
- **`todos.db` is shared, real state** — the smoke test's created todo is
  deleted at the end of the run, but if it's interrupted mid-way a
  `Smoke test task` row can be left behind; check `GET /api/todos` if the
  UI shows an unexpected extra row after a failed smoke run.

## Troubleshooting

- `curl: (7) Failed to connect` right after launching -> the background
  process was reaped (see Gotchas above); relaunch with `nohup ... &
  disown -a`.
- `ModuleNotFoundError: No module named 'playwright'` -> the venv doesn't
  have it yet; run the Prerequisites `pip install playwright` +
  `playwright install chromium` lines.
- Screenshot comes back a blank/near-empty dark rectangle -> the page was
  captured before Streamlit's websocket painted content; this is what the
  `wait_for_selector` + 1s sleep in `driver.py` are for — don't remove them.
