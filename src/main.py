"""App FastAPI y endpoints de la API de to-do list."""
import sqlite3
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query

from src.database import get_db, init_db
from src.models import TodoCreate, TodoOut, TodoStatus, TodoUpdate


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Todo API", lifespan=lifespan)


def _row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row)


def _get_todo_or_404(conn: sqlite3.Connection, todo_id: int) -> dict:
    row = conn.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Todo {todo_id} not found")
    return _row_to_dict(row)


@app.get("/api/todos", response_model=list[TodoOut])
def list_todos(status: Optional[TodoStatus] = Query(default=None)):
    with get_db() as conn:
        if status is not None:
            rows = conn.execute(
                "SELECT * FROM todos WHERE status = ? ORDER BY id", (status.value,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM todos ORDER BY id").fetchall()
        return [_row_to_dict(r) for r in rows]


@app.get("/api/todos/{todo_id}", response_model=TodoOut)
def get_todo(todo_id: int):
    with get_db() as conn:
        return _get_todo_or_404(conn, todo_id)


@app.post("/api/todos", response_model=TodoOut, status_code=201)
def create_todo(todo: TodoCreate):
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO todos (title, description) VALUES (?, ?)",
            (todo.title, todo.description),
        )
        return _get_todo_or_404(conn, cursor.lastrowid)


@app.patch("/api/todos/{todo_id}", response_model=TodoOut)
def update_todo(todo_id: int, todo: TodoUpdate):
    with get_db() as conn:
        # Aseguramos que la tarea existe antes de actualizar.
        _get_todo_or_404(conn, todo_id)

        fields = todo.model_dump(exclude_unset=True)
        if not fields:
            raise HTTPException(status_code=400, detail="No fields provided to update")

        set_clauses = []
        values = []
        for key, value in fields.items():
            set_clauses.append(f"{key} = ?")
            values.append(value.value if isinstance(value, TodoStatus) else value)
        set_clauses.append("updated_at = datetime('now')")
        values.append(todo_id)

        conn.execute(
            f"UPDATE todos SET {', '.join(set_clauses)} WHERE id = ?",
            values,
        )
        return _get_todo_or_404(conn, todo_id)


@app.delete("/api/todos/{todo_id}", status_code=204)
def delete_todo(todo_id: int):
    with get_db() as conn:
        _get_todo_or_404(conn, todo_id)
        conn.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
    return None
