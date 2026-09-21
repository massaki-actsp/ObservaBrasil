"""
Versão educacional para Google Colab.

Cole o conteúdo deste arquivo em uma célula do Colab. O túnel público é temporário
e existe apenas enquanto a célula estiver ativa.
"""

import os
import subprocess
import textwrap
from pathlib import Path

APP_DIR = Path("/content/observa_brasil")
APP_DIR.mkdir(exist_ok=True)

subprocess.run(
    [
        "pip",
        "install",
        "-q",
        "flask",
        "flask-sqlalchemy",
        "flask-wtf",
        "requests",
        "shapely",
        "numpy",
        "pyngrok",
    ],
    check=True,
)

(APP_DIR / "app_colab.py").write_text(
    textwrap.dedent(
        """
        from flask import Flask, jsonify
        import requests

        app = Flask(__name__)
        INPE = "https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/diario/Brasil/"
        BDC = "https://data.inpe.br/bdc/stac/v1/"

        @app.get("/")
        def home():
            return "<h1>Observa Brasil Colab</h1><p>Use /api/health e /api/fontes/status.</p>"

        @app.get("/api/health")
        def health():
            return jsonify({"sucesso": True, "dados": {"status": "ok"}, "erro": None})

        @app.get("/api/fontes/status")
        def fontes():
            inpe_status = requests.get(INPE, timeout=20).ok
            bdc = requests.get(BDC, timeout=20)
            return jsonify({
                "sucesso": True,
                "dados": {
                    "inpe_bdqueimadas": {"online": inpe_status, "url": INPE},
                    "brazil_data_cube": {"online": bdc.ok, "url": BDC},
                },
                "erro": None,
            })

        if __name__ == "__main__":
            app.run(port=5000)
        """
    ),
    encoding="utf-8",
)

from pyngrok import ngrok

public_url = ngrok.connect(5000).public_url
print(f"URL temporária: {public_url}")
print("Aviso: este endereço funciona apenas enquanto a célula estiver em execução.")
subprocess.Popen(["python", str(APP_DIR / "app_colab.py")])
