from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
import os

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)

    app.config['SECRET_KEY'] = 'your_secret_key_here'
    app.config['SQLALCHEMY_DATABASE_URI'] = r'sqlite:///C:\Users\Gabriel\Desktop\Coding\New folder\Clothes-Store-Inventory-with-Flask\instance\your_database.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'routes.login'

    migrate = Migrate(app, db)

    from STORE.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from STORE.routes import bp as routes_bp
    app.register_blueprint(routes_bp)

    # Debugging statements
    print("Current Working Directory:", os.getcwd())
    print("Database URI:", app.config['SQLALCHEMY_DATABASE_URI'])

    # Ensure the instance folder exists
    instance_folder = os.path.dirname(app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', ''))
    if not os.path.exists(instance_folder):
        os.makedirs(instance_folder)
        print(f"Created directory: {instance_folder}")

    return app
