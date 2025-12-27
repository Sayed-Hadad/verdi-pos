from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from .config import Config
import os

# Extensions
bcrypt = Bcrypt()
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "الرجاء تسجيل الدخول"  # Arabic message


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)

    os.makedirs(app.instance_path, exist_ok=True)

    bcrypt.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)

    from .models import User, Setting  # noqa: F401

    # Register blueprints
    from .auth import auth_bp
    from .routes import main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    @app.context_processor
    def inject_logo():
        logo_setting = Setting.query.get("logo_path")
        return {"logo_path": logo_setting.value if logo_setting else ""}

    with app.app_context():
        db.create_all()

        # إنشاء مستخدم مدير افتراضي إذا لم يكن موجودًا
        if not User.query.first():
            admin = User(
                username="admin",
                role="admin",
                password_hash=bcrypt.generate_password_hash("admin123").decode("utf-8"),
            )
            db.session.add(admin)
            db.session.commit()
    return app
