"""
FitTrack Pro - Flask REST API
api/__init__.py — Application factory

Adapters layer: Flask REST API adapter
Architecture: Layered + Ports-and-Adapters (Hexagonal)
"""

from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_migrate import Migrate

db = SQLAlchemy()
jwt = JWTManager()
migrate = Migrate()


def create_app(config_name: str = "development") -> Flask:
    from .config import config_by_name

    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    # ── Extensions ────────────────────────────────────────────────────────────
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # ── JWT error handlers ────────────────────────────────────────────────────
    @jwt.unauthorized_loader
    def missing_token(reason):
        return jsonify({"error": "Authorization token required", "detail": reason}), 401

    @jwt.invalid_token_loader
    def invalid_token(reason):
        return jsonify({"error": "Invalid token", "detail": reason}), 401

    @jwt.expired_token_loader
    def expired_token(jwt_header, jwt_data):
        return jsonify({"error": "Token has expired"}), 401

    # ── Global error handlers ─────────────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"error": "Method not allowed"}), 405

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"error": "Internal server error"}), 500

    # ── Register blueprints ───────────────────────────────────────────────────
    from .routes.auth import auth_bp
    from .routes.workouts import workouts_bp
    from .routes.nutrition import nutrition_bp
    from .routes.goals import goals_bp
    from .routes.measurements import measurements_bp
    from .routes.progress import progress_bp
    from .routes.coach import coach_bp
    from .routes.notifications import notifications_bp

    app.register_blueprint(auth_bp,          url_prefix="/api/auth")
    app.register_blueprint(workouts_bp,      url_prefix="/api/workouts")
    app.register_blueprint(nutrition_bp,     url_prefix="/api/nutrition")
    app.register_blueprint(goals_bp,         url_prefix="/api/goals")
    app.register_blueprint(measurements_bp,  url_prefix="/api/measurements")
    app.register_blueprint(progress_bp,      url_prefix="/api/progress")
    app.register_blueprint(coach_bp,         url_prefix="/api/coach")
    app.register_blueprint(notifications_bp, url_prefix="/api/notifications")

    # ── Health check ──────────────────────────────────────────────────────────
    @app.route("/api/health")
    def health():
        try:
            db.session.execute(db.text("SELECT 1"))
            db_status = "ok"
        except Exception:
            db_status = "error"
        return jsonify({
            "status": "ok",
            "service": "FitTrack Pro API",
            "database": db_status,
            "version": "1.0.0",
        })

    return app
