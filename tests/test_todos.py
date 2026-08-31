"""Tests de la API de to-do list."""
import os
import tempfile

import pytest

# La BD de test debe fijarse ANTES de importar la app, ya que database.py
# lee TODO_DB_PATH al cargarse el módulo.
_TMP_DB = os.path.join(tempfile.gettempdir(), "todos_test.db")
if os.path.exists(_TMP_DB):
    os.remove(_TMP_DB)
os.environ["TODO_DB_PATH"] = _TMP_DB

from fastapi.testclient import TestClient  # noqa: E402

from src.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def clean_db():
    """Limpia la tabla todos antes de cada test para aislarlos entre sí."""
    with TestClient(app) as client:
        # El evento startup crea la tabla; aquí solo vaciamos su contenido.
        from src.database import get_db

        with get_db() as conn:
            conn.execute("DELETE FROM todos")
        yield client


def test_create_todo(clean_db):
    response = clean_db.post(
        "/api/todos", json={"title": "Comprar leche", "description": "Ir al súper"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Comprar leche"
    assert data["description"] == "Ir al súper"
    assert data["status"] == "pending"
    assert "id" in data


def test_create_todo_without_description(clean_db):
    response = clean_db.post("/api/todos", json={"title": "Sin descripción"})
    assert response.status_code == 201
    assert response.json()["description"] is None


def test_create_todo_invalid_body(clean_db):
    response = clean_db.post("/api/todos", json={"description": "sin titulo"})
    assert response.status_code == 422


def test_list_todos(clean_db):
    clean_db.post("/api/todos", json={"title": "Tarea 1"})
    clean_db.post("/api/todos", json={"title": "Tarea 2"})

    response = clean_db.get("/api/todos")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_list_todos_filter_by_status(clean_db):
    created = clean_db.post("/api/todos", json={"title": "Tarea pendiente"}).json()
    done_todo = clean_db.post("/api/todos", json={"title": "Tarea hecha"}).json()
    clean_db.patch(f"/api/todos/{done_todo['id']}", json={"status": "done"})

    response = clean_db.get("/api/todos", params={"status": "pending"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == created["id"]

    response = clean_db.get("/api/todos", params={"status": "done"})
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == done_todo["id"]


def test_get_todo(clean_db):
    created = clean_db.post("/api/todos", json={"title": "Detalle"}).json()

    response = clean_db.get(f"/api/todos/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_todo_not_found(clean_db):
    response = clean_db.get("/api/todos/9999")
    assert response.status_code == 404


def test_update_todo(clean_db):
    created = clean_db.post("/api/todos", json={"title": "Original"}).json()

    response = clean_db.patch(
        f"/api/todos/{created['id']}",
        json={"title": "Actualizado", "status": "done"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Actualizado"
    assert data["status"] == "done"


def test_update_todo_not_found(clean_db):
    response = clean_db.patch("/api/todos/9999", json={"title": "No existe"})
    assert response.status_code == 404


def test_update_todo_empty_body(clean_db):
    created = clean_db.post("/api/todos", json={"title": "Tarea"}).json()

    response = clean_db.patch(f"/api/todos/{created['id']}", json={})
    assert response.status_code == 400


def test_delete_todo(clean_db):
    created = clean_db.post("/api/todos", json={"title": "A borrar"}).json()

    response = clean_db.delete(f"/api/todos/{created['id']}")
    assert response.status_code == 204

    response = clean_db.get(f"/api/todos/{created['id']}")
    assert response.status_code == 404


def test_delete_todo_not_found(clean_db):
    response = clean_db.delete("/api/todos/9999")
    assert response.status_code == 404
