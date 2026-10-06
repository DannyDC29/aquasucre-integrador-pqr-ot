import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template, request, redirect, url_for
import requests

app = Flask(__name__)

FRAPPE_URL = os.environ.get("FRAPPE_URL", "http://127.0.0.1:8000")
FRAPPE_API_KEY = os.environ.get("FRAPPE_API_KEY")
FRAPPE_API_SECRET = os.environ.get("FRAPPE_API_SECRET")
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    db_url = DATABASE_URL
    if db_url and "channel_binding=" in db_url:
        db_url = db_url.split("&channel_binding=")[0].split("?channel_binding=")[0]
    return psycopg2.connect(db_url, cursor_factory=RealDictCursor)

@app.route("/")
def index():
    tickets = []
    tecnicos = []
    error_msg = None

    # 1. Obtener PQRs desde Frappe
    headers = {"Authorization": f"token {FRAPPE_API_KEY}:{FRAPPE_API_SECRET}"}
    try:
        res = requests.get(
            f"{FRAPPE_URL}/api/resource/HD Ticket?fields=[\"name\",\"subject\",\"status\",\"priority\",\"creation\"]",
            headers=headers,
            timeout=8
        )
        if res.status_code == 200:
            tickets = res.json().get("data", [])
        else:
            error_msg = f"Error al conectar con Frappe (Código: {res.status_code})"
    except Exception as e:
        error_msg = f"Error de red con Frappe: {e}"

    # 2. Obtener Técnicos desde Neon
    if not DATABASE_URL:
        db_alert = "DATABASE_URL no está configurada en Render."
        error_msg = f"{error_msg} | {db_alert}" if error_msg else db_alert
    else:
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT id_tecnico, nombre, especialidad FROM tecnicos;")
            tecnicos = cur.fetchall()
            cur.close()
            conn.close()
        except Exception as e:
            db_alert = f"Error al consultar Neon PostgreSQL: {e}"
            error_msg = f"{error_msg} | {db_alert}" if error_msg else db_alert

    return render_template("index.html", tickets=tickets, tecnicos=tecnicos, error=error_msg)

@app.route("/asignar", methods=["POST"])
def asignar_tecnico():
    id_pqr = request.form.get("id_pqr")
    id_tecnico = request.form.get("id_tecnico")
    tipo_servicio = request.form.get("tipo_servicio", "Atención PQR")
    descripcion = request.form.get("descripcion", "Revisión técnica de PQR")
    direccion = request.form.get("direccion", "Dirección registrada")

    if DATABASE_URL and id_pqr and id_tecnico:
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO ordenes_trabajo (
                    id_pqr, id_tecnico, tipo_servicio, descripcion, direccion, prioridad, estado, fecha_asignacion
                ) VALUES (%s, %s, %s, %s, %s, 'MEDIA', 'ASIGNADA', CURRENT_TIMESTAMP);
            """, (id_pqr, id_tecnico, tipo_servicio, descripcion, direccion))
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print("Error al insertar OT en Neon:", e)

    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
