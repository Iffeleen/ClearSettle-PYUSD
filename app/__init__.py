from flask import Flask
from config import Config
from app import db
from app.utils.money import cents_to_dollars


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_db(app)
    app.jinja_env.filters["money"] = cents_to_dollars

    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.orders import orders_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(orders_bp)

    @app.errorhandler(413)
    def too_large(error):
        return "File too large. The maximum upload size is 5 MB.", 413

    return app
