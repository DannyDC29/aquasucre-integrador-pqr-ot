import os
import requests
from flask import Flask, render_template

app = Flask(__name__)

FRAPPE_URL = os.getenv("FRAPPE_URL", "").rstrip("/")
API_KEY = os.getenv("FRAPPE_API_KEY")
API_SECRET = os.getenv("FRAPPE_API_SECRET")

@app.route("/")
def index():
    tickets = []
    error = None
    
    if not FRAPPE_URL or not API_KEY or not API_SECRET:
        error = "Faltan variables de entorno por configurar en Render."
    else:
        headers = {"Authorization": f"token {API_KEY}:{API_SECRET}"}
        url = f"{FRAPPE_URL}/api/resource/HD%20Ticket?fields=[\"name\",\"subject\",\"status\",\"priority\",\"creation\"]"
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                tickets = response.json().get("data", [])
            else:
                error = f"Error en la API de Frappe ({response.status_code}): {response.text}"
        except Exception as e:
            error = f"Error al conectar con la API de Frappe: {str(e)}"

    return render_template("index.html", tickets=tickets, error=error)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
