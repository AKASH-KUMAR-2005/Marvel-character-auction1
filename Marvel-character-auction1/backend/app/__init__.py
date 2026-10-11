import logging
import os
from flask import Flask, jsonify
from flask_cors import CORS
from sqlalchemy import event
from .models import db
from .seed import seed_catalog


def create_app(test_config=None):
    app = Flask(__name__)
    from config import Config
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    db.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": [app.config.get("FRONTEND_ORIGIN", "http://localhost:5173"), "http://127.0.0.1:5173"]}})

    from .routes.api import api
    app.register_blueprint(api)

    @app.get("/")
    def index():
        return jsonify({"name": "Marvel Character Auction Battle API", "health": "/api/health"})

    with app.app_context():
        if app.config.get("SQLALCHEMY_DATABASE_URI", "").startswith("sqlite"):
            @event.listens_for(db.engine, "connect")
            def _enable_sqlite_foreign_keys(connection, _record):
                cursor = connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()
        db.create_all()
        seed_catalog()

    return app
