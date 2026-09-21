from flask import Flask, g, render_template, request

from config import get_config
from .extensions import csrf, db, migrate
from .services.device import detect_device


def create_app(config_object=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_object or get_config())

    app.config["CACHE_DIR"].mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    from .routes.api import api_bp
    from .routes.auth import auth_bp
    from .routes.main import main_bp

    csrf.exempt(api_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    @app.before_request
    def identify_device():
        g.device = detect_device(request.headers)

    @app.context_processor
    def inject_device_context():
        return {"device": getattr(g, "device", {"tipo": "desktop"})}

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("Accept-CH", "Sec-CH-UA-Mobile, Sec-CH-UA-Platform")
        response.headers.setdefault("Vary", "User-Agent, Sec-CH-UA-Mobile, Sec-CH-UA-Platform")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy", "geolocation=(self), camera=(), microphone=()"
        )
        return response

    @app.errorhandler(404)
    def not_found(error):
        if "/api/" in getattr(error, "description", ""):
            return {"sucesso": False, "dados": None, "erro": "Recurso não encontrado"}, 404
        return render_template("erro.html", status=404, mensagem="Página não encontrada"), 404

    @app.errorhandler(500)
    def server_error(error):
        return render_template("erro.html", status=500, mensagem="Erro interno"), 500

    with app.app_context():
        db.create_all()

    return app
