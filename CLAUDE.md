# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A to-do list app: a FastAPI backend (`src/`) backed by SQLite, and a Streamlit dashboard (`app_ui.py`) that talks to it over HTTP. All comments/docstrings and UI copy are in Spanish; keep new code consistent with that.

## Commands

Windows venv at `venv/` (git-bash paths below; on native PowerShell use `venv\Scripts\python.exe`).

Run the API:
```bash
./venv/Scripts/python.exe -m uvicorn src.main:app --reload --port 8000
```

Run the UI (requires the API running; reads `TODO_API_URL`, default `http://localhost:8000/api/todos`):
```bash
./venv/Scripts/python.exe -m streamlit run app_ui.py
```

Run all tests:
```bash
./venv/Scripts/python.exe -m pytest
```

Run a single test:
```bash
./venv/Scripts/python.exe -m pytest tests/test_todos.py::test_create_todo
```

There is a `run-proyecto-2` skill that automates launching both processes in the background (handling the Windows/git-bash `nohup`/`disown` quirks) plus a `driver.py` for smoke-testing the API and screenshotting the UI — prefer it over manual launch commands when running/demoing the app.

## Architecture

- `src/database.py` — single source of the SQLite connection logic. `DB_PATH` is read from the `TODO_DB_PATH` env var at **import time**, which is how `tests/test_todos.py` swaps in a temp DB: it sets the env var before importing `src.main`. Each request gets its own short-lived connection via the `get_db()` context manager (opens, yields, commits, closes) — there is no persistent pool or shared connection.
- `src/models.py` — Pydantic schemas double as the API contract: `TodoCreate` (POST body), `TodoUpdate` (PATCH body, all fields optional via `exclude_unset`), `TodoOut` (response shape), and the `TodoStatus` enum (`pending`/`done`) that's also the DB's `CHECK` constraint.
- `src/main.py` — all routes live in this one module (no routers/blueprints). `update_todo` builds its `SET` clause dynamically from whichever fields were actually sent in the PATCH body, so adding a field to `TodoUpdate` is enough to make it PATCH-able — no route changes needed. `init_db()` runs once via the FastAPI `lifespan` context, not on every request.
- `app_ui.py` — a single-file Streamlit script (no multipage/component split). It is a pure HTTP client of the API — it never touches `src/` or the DB directly, so it can be pointed at any deployment via `TODO_API_URL`. Streamlit's execution model matters here: the whole script reruns top-to-bottom on every interaction (button click, form submit), which is why every mutating action (`create_todo`, `mark_done`, `delete_todo`, `update_description`) is followed by `st.rerun()` to refresh the table from the API rather than mutating local state. Timestamps from the API are UTC ISO strings; `parse_utc_to_local`/`utc_to_local_str` convert them to the machine's local timezone for display, and the monthly Excel report (`build_monthly_report`, via `openpyxl`) filters/groups on those localized dates.
- Tests (`tests/test_todos.py`) exercise the real FastAPI app through `TestClient` against a temp SQLite file (not mocked), with an autouse fixture that deletes all rows before each test for isolation. `pytest.ini` sets `pythonpath = .` so `from src...` imports resolve from the repo root.
