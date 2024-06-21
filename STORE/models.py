from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from . import db  # Assuming 'db' is your SQLAlchemy instance

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)  # Changed self.password to self.password_hash


class Product(db.Model):
    __tablename__ = 'products'

    code = db.Column(db.String(20), primary_key=True)  # Using 'code' as primary key
    item = db.Column(db.String(50), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    type_material = db.Column(db.String(50))
    size = db.Column(db.String(20))
    color = db.Column(db.String(20))
    description = db.Column(db.Text)
    buying_price = db.Column(db.Float, nullable=False)
    selling_price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)  # Default value set to 1

    @property
    def profit(self):
        return self.selling_price - self.buying_price

    def __repr__(self):
        return f'<Product {self.code} - {self.item}>'

class Stock(db.Model):
    __tablename__ = 'stocks'

    id = db.Column(db.Integer, primary_key=True)
    product_code = db.Column(db.String(20), nullable=False)
    bp_summation = db.Column(db.Float, nullable=False, default=0.0)
    sp_summation = db.Column(db.Float, nullable=False, default=0.0)
    profit_summation = db.Column(db.Float, nullable=False, default=0.0)
    pieces = db.Column(db.Integer, nullable=False, default=0)

    def update_pieces(self):
        # Query associated Product and update pieces based on its quantity
        products = Product.query.filter(Product.code.like(f"{self.product_code}%")).all()
        self.pieces = sum(product.quantity for product in products)

    def update_summations(self):
        # Calculate summations based on associated Product's variants
        products = Product.query.filter(Product.code.like(f"{self.product_code}%")).all()
        self.bp_summation = sum(product.buying_price * product.quantity for product in products)
        self.sp_summation = sum(product.selling_price * product.quantity for product in products)
        self.profit_summation = sum((product.selling_price - product.buying_price) * product.quantity for product in products)
        self.pieces = sum(product.quantity for product in products)

    def __repr__(self):
        return f'<Stock {self.product_code}>'


class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.code'), nullable=False)  # Foreign key to products.code
    quantity_sold = db.Column(db.Integer, nullable=False)
    sale_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(128), nullable=False)
    customer_email = db.Column(db.String(128))
    phone_number = db.Column(db.String(20))
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    total_amount = db.Column(db.Float, nullable=False)
    items = db.relationship('InvoiceItem', backref='invoice', lazy=True)

class InvoiceItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.code'), nullable=False)  # Foreign key to products.code
    quantity = db.Column(db.Integer, nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    product = db.relationship('Product')
