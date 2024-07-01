from STORE import create_app, db
from STORE.models import User, Product
from flask_migrate import Migrate

app = create_app()

if __name__ == '__main__':
    # Initialize Flask-Migrate
    migrate = Migrate(app, db)
    
    # Create all database tables if they don't exist
    with app.app_context():
        db.create_all()

    # Start the Flask development server
    app.run(debug=True)
