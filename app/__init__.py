from flask import Flask
from config import Config
from app import db


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_db(app)

    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)

    return app
