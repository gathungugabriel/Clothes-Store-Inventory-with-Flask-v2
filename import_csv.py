from STORE import create_app
from add_data import add_products_from_csv

app = create_app()
with app.app_context():
    add_products_from_csv('products.csv')
