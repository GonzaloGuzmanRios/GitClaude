"""Panel de control visual (Streamlit) para la API de tareas FastAPI."""
import io
import os
from datetime import datetime, timezone

import pandas as pd
import requests
import streamlit as st

API_URL = os.environ.get("TODO_API_URL", "http://localhost:8000/api/todos")

STATUS_COLORS = {"done": "#1e4620", "pending": "#4d3319"}
STATUS_LABELS = {"done": "✅ Completada", "pending": "🟠 Pendiente"}

MESES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
    7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}

st.set_page_config(page_title="Panel de tareas", page_icon="✅", layout="wide")
st.title("✅ Panel de control de tareas")


# --- Helpers de comunicación con la API -------------------------------------

def fetch_todos():
    try:
        response = requests.get(API_URL, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        st.error(f"No se pudo conectar con la API en {API_URL}: {exc}")
        return []


def create_todo(title: str, description: str | None):
    response = requests.post(
        API_URL, json={"title": title, "description": description or None}, timeout=5
    )
    response.raise_for_status()


def mark_done(todo_id: int):
    response = requests.patch(f"{API_URL}/{todo_id}", json={"status": "done"}, timeout=5)
    response.raise_for_status()


def delete_todo(todo_id: int):
    response = requests.delete(f"{API_URL}/{todo_id}", timeout=5)
    response.raise_for_status()


def update_description(todo_id: int, description: str | None):
    response = requests.patch(
        f"{API_URL}/{todo_id}", json={"description": description or None}, timeout=5
    )
    response.raise_for_status()


def description_box_height(description: str | None, words_per_line: int = 6) -> int:
    """Calcula el alto del cuadro de descripción según su cantidad de palabras
    (máx. 3 líneas visibles; el exceso de texto se corta con scroll interno)."""
    word_count = len((description or "").split())
    lines = max(1, -(-word_count // words_per_line))  # ceil sin usar math
    lines = min(lines, 3)
    return max(68, 34 + lines * 22)


def parse_utc_to_local(utc_str: str | None) -> datetime | None:
    """Convierte un timestamp UTC devuelto por la API (ISO 8601, p. ej. '2026-08-28T19:06:19')
    a un datetime con la hora local del PC."""
    if not utc_str:
        return None
    try:
        dt_utc = datetime.fromisoformat(utc_str)
        if dt_utc.tzinfo is None:
            dt_utc = dt_utc.replace(tzinfo=timezone.utc)
        return dt_utc.astimezone()  # usa la zona horaria del sistema
    except (ValueError, TypeError):
        return None


def utc_to_local_str(utc_str: str) -> str:
    """Versión en texto (dd/mm/aaaa hh:mm:ss) de parse_utc_to_local, para mostrar en la tabla."""
    dt_local = parse_utc_to_local(utc_str)
    return dt_local.strftime("%d/%m/%Y %H:%M:%S") if dt_local else (utc_str or "-")


def build_monthly_report(todos: list[dict], year: int, month: int) -> bytes:
    """Genera un archivo Excel (.xlsx) en memoria con las tareas creadas en el mes/año dados."""
    rows = []
    for todo in todos:
        local_dt = parse_utc_to_local(todo.get("created_at"))
        if local_dt is not None and local_dt.year == year and local_dt.month == month:
            rows.append(
                {
                    "ID": todo["id"],
                    "Título": todo["title"],
                    "Descripción": todo.get("description") or "-",
                    "Estado": STATUS_LABELS.get(todo["status"], todo["status"]),
                    "Creado": local_dt.strftime("%d/%m/%Y %H:%M:%S"),
                }
            )

    df = pd.DataFrame(rows, columns=["ID", "Título", "Descripción", "Estado", "Creado"])

    buffer = io.BytesIO()
    sheet_name = f"{MESES[month][:20]} {year}"
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return buffer.getvalue()


# --- Formulario de creación ---------------------------------------------------

with st.form("new_todo_form", clear_on_submit=True):
    st.subheader("Nueva tarea")
    col1, col2, col3 = st.columns([2, 2, 1.5])
    title = col1.text_input("Título")
    description = col2.text_input("Descripción (opcional)")
    # Fecha y hora tomadas del reloj del PC (informativo: la API registra la
    # fecha real de creación en el servidor al guardar la tarea).
    col3.text_input(
        "Fecha y hora (PC)",
        value=datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        disabled=True,
    )
    submitted = st.form_submit_button("Crear tarea")

    if submitted:
        if not title.strip():
            st.warning("El título es obligatorio.")
        else:
            try:
                create_todo(title.strip(), description.strip())
                st.success(f"Tarea '{title}' creada.")
                st.rerun()
            except requests.RequestException as exc:
                st.error(f"Error al crear la tarea: {exc}")

st.divider()

# --- Datos y contadores -------------------------------------------------------

todos = fetch_todos()
total = len(todos)
done_count = sum(1 for t in todos if t["status"] == "done")
pending_count = total - done_count

c1, c2, c3 = st.columns(3)
c1.metric("Total", total)
c2.metric("Pendientes", pending_count)
c3.metric("Completadas", done_count)

st.divider()

# --- Tabla de tareas con acciones ---------------------------------------------

st.subheader("Tareas")

if not todos:
    st.info("No hay tareas todavía. Crea una con el formulario de arriba.")
else:
    COLS = [1, 2.2, 3.0, 1.1, 1.8, 1.8, 1.3, 1.3]
    header = st.columns(COLS)
    for col, label in zip(
        header, ["ID", "Título", "Descripción", "", "Creado", "Estado", "", ""]
    ):
        col.markdown(f"**{label}**")

    for todo in todos:
        row = st.columns(COLS)
        bg = STATUS_COLORS.get(todo["status"], "#ffffff")

        row[0].markdown(
            f"<div style='background-color:{bg};padding:6px;border-radius:4px'>{todo['id']}</div>",
            unsafe_allow_html=True,
        )
        row[1].markdown(
            f"<div style='background-color:{bg};padding:6px;border-radius:4px'>{todo['title']}</div>",
            unsafe_allow_html=True,
        )
        # La descripción es editable independientemente del estado de la tarea.
        # El alto del cuadro crece según la cantidad de palabras (máx. 3 líneas;
        # el resto queda accesible con scroll interno del propio text_area).
        description_value = todo.get("description") or ""
        new_description = row[2].text_area(
            "Descripción",
            value=description_value,
            height=description_box_height(description_value),
            key=f"desc_{todo['id']}",
            label_visibility="collapsed",
        )
        if row[3].button("💾", key=f"save_desc_{todo['id']}", help="Guardar descripción"):
            try:
                update_description(todo["id"], new_description.strip())
                st.success("Descripción actualizada.")
                st.rerun()
            except requests.RequestException as exc:
                st.error(f"Error al actualizar la descripción: {exc}")
        row[4].markdown(
            f"<div style='background-color:{bg};padding:6px;border-radius:4px'>{utc_to_local_str(todo.get('created_at'))}</div>",
            unsafe_allow_html=True,
        )
        row[5].markdown(
            f"<div style='background-color:{bg};padding:6px;border-radius:4px'>{STATUS_LABELS.get(todo['status'], todo['status'])}</div>",
            unsafe_allow_html=True,
        )

        if todo["status"] != "done":
            if row[6].button("Completar", key=f"done_{todo['id']}"):
                try:
                    mark_done(todo["id"])
                    st.rerun()
                except requests.RequestException as exc:
                    st.error(f"Error al actualizar la tarea: {exc}")
        else:
            row[6].write("")

        if row[7].button("Eliminar", key=f"delete_{todo['id']}"):
            try:
                delete_todo(todo["id"])
                st.rerun()
            except requests.RequestException as exc:
                st.error(f"Error al eliminar la tarea: {exc}")

st.divider()

# --- Reporte mensual en Excel --------------------------------------------------

st.subheader("📊 Reporte mensual")

now = datetime.now()
rc1, rc2, rc3 = st.columns([1.5, 1, 2])
selected_month = rc1.selectbox(
    "Mes",
    options=list(MESES.keys()),
    format_func=lambda m: MESES[m],
    index=now.month - 1,
)
selected_year = rc2.selectbox(
    "Año",
    options=list(range(now.year - 5, now.year + 1)),
    index=5,
)

report_bytes = build_monthly_report(todos, selected_year, selected_month)
report_rows = sum(
    1
    for todo in todos
    if (dt := parse_utc_to_local(todo.get("created_at")))
    and dt.year == selected_year
    and dt.month == selected_month
)

with rc3:
    st.write("")
    st.download_button(
        label=f"⬇️ Descargar reporte de {MESES[selected_month]} {selected_year} (.xlsx)",
        data=report_bytes,
        file_name=f"reporte_tareas_{selected_year}_{selected_month:02d}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        disabled=report_rows == 0,
    )

if report_rows == 0:
    st.info(f"No hay tareas creadas en {MESES[selected_month]} {selected_year}.")
else:
    st.caption(f"{report_rows} tarea(s) en {MESES[selected_month]} {selected_year}.")
