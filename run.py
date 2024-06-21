from STORE import app, db
from STORE.models import User, Product  # Import models from STORE package
from flask_migrate import Migrate

if __name__ == '__main__':
    # Initialize Flask-Migrate
    migrate = Migrate(app, db)
    
    # Create all database tables if they don't exist
    with app.app_context():
        db.create_all()

    # Start the Flask development server
    app.run(debug=True)

