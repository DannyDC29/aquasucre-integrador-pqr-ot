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
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

@app.route("/")
def index():
    tickets = []
    error = None
    headers = {"Authorization": f"token {FRAPPE_API_KEY}:{FRAPPE_API_SECRET}"}
    
    # 1. Obtener PQRs de Frappe
    try:
        res = requests.get(
            f"{FRAPPE_URL}/api/resource/HD Ticket?fields=[\"name\",\"subject\",\"status\",\"priority\",\"creation\"]",
            headers=headers
        )
        if res.status_code == 200:
            tickets = res.json().get("data", [])
        else:
            error = f"Error al conectar con Frappe (Código: {res.status_code})"
    except Exception as e:
        error = f"Error de red con Frappe: {e}"

    # 2. Obtener Técnicos de Neon
    tecnicos = []
    try:
        if DATABASE_URL:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT id_tecnico, nombre, especialidad FROM tecnicos WHERE estado = 'ACTIVO';")
            tecnicos = cur.fetchall()
            cur.close()
            conn.close()
    except Exception as e:
        print("Error consultando Neon:", e)

    return render_template("index.html", tickets=tickets, tecnicos=tecnicos, error=error)

@app.route("/asignar", methods=["POST"])
def asignar_tecnico():
    id_pqr = request.form.get("id_pqr")
    id_tecnico = request.form.get("id_tecnico")
    tipo_servicio = request.form.get("tipo_servicio", "Atención PQR")
    descripcion = request.form.get("descripcion", "Revisión técnica de PQR")
    direccion = request.form.get("direccion", "Dirección registrada")

    try:
        if DATABASE_URL:
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
        print("Error al guardar en Neon:", e)

    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
