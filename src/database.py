"""Conexión SQLite e inicialización de tablas."""
import os
import sqlite3
from contextlib import contextmanager

# Permite sobreescribir la ruta de la BD (útil para tests).
DB_PATH = os.environ.get("TODO_DB_PATH", os.path.join(os.path.dirname(__file__), "..", "todos.db"))


def get_connection() -> sqlite3.Connection:
    """Crea una nueva conexión a la base de datos con row_factory configurado."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_db():
    """Context manager que entrega una conexión y la cierra al finalizar."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Crea la tabla `todos` si no existe."""
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'done')),
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
