"""Driver para lanzar y comprobar la app (API FastAPI + UI Streamlit).

Uso:
    venv/Scripts/python.exe .claude/skills/run-proyecto-2/driver.py smoke
        -> ejercita la API completa (create/list/patch/delete) via HTTP.

    venv/Scripts/python.exe .claude/skills/run-proyecto-2/driver.py screenshot [ruta.png]
        -> abre la UI de Streamlit con Playwright (Chromium headless) y
           guarda una captura real de la página renderizada.

Requiere que la API (puerto 8000) y la UI de Streamlit (puerto 8501) ya
estén corriendo -- ver SKILL.md para cómo arrancarlas en segundo plano.
"""
import json
import sys
import time
import urllib.error
import urllib.request

API_URL = "http://localhost:8000/api/todos"
UI_URL = "http://localhost:8501"


def _req(method: str, path: str = "", body: dict | None = None):
    url = API_URL + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                  headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as exc:
        return exc.code, None


def smoke():
    print("== create ==")
    status, todo = _req("POST", body={"title": "Smoke test task", "description": "created by driver"})
    assert status == 201, f"create failed: {status}"
    todo_id = todo["id"]
    print(f"created id={todo_id} status={status}")

    print("== list (contains new id) ==")
    status, todos = _req("GET")
    assert status == 200
    assert any(t["id"] == todo_id for t in todos), "new todo missing from list"
    print(f"list ok, {len(todos)} todos total")

    print("== mark done ==")
    status, todo = _req("PATCH", f"/{todo_id}", {"status": "done"})
    assert status == 200 and todo["status"] == "done"
    print("patch ok, status=done")

    print("== delete ==")
    status, _ = _req("DELETE", f"/{todo_id}")
    assert status == 204
    print("delete ok")

    print("== verify 404 after delete ==")
    status, _ = _req("GET", f"/{todo_id}")
    assert status == 404
    print("verify ok")

    print("SMOKE OK")


def screenshot(out_path: str = "ui_screenshot.png"):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        page.goto(UI_URL, wait_until="networkidle")
        # Streamlit renders via websocket after the initial shell loads;
        # wait for a known heading to appear before capturing.
        page.wait_for_selector("text=Panel de control de tareas", timeout=15000)
        time.sleep(1)  # let the todo table finish painting
        page.screenshot(path=out_path, full_page=True)
        browser.close()
    print(f"screenshot saved to {out_path}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "smoke"
    if cmd == "smoke":
        smoke()
    elif cmd == "screenshot":
        screenshot(sys.argv[2] if len(sys.argv) > 2 else "ui_screenshot.png")
    else:
        print(f"unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)
