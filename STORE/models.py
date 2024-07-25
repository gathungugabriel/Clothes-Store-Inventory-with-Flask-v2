from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from . import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='attendant')  # 'admin' or 'attendant'

    def __repr__(self):
        return f'<User {self.username}>'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == 'admin'

    def has_permission(self, permission):
        permissions = {
            'add_product': self.is_admin(),
            'update_product': self.is_admin(),
            'delete_product': self.is_admin(),
            'upload_csv': self.is_admin(),
            'manage_users': self.is_admin(),
        }
        return permissions.get(permission, False)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pre = db.Column(db.String(10), nullable=False)
    code = db.Column(db.String(20), nullable=False, unique=True)
    item = db.Column(db.String(50), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    type_material = db.Column(db.String(50), nullable=False)
    size = db.Column(db.String(10), nullable=False)
    color = db.Column(db.String(20), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    buying_price = db.Column(db.Float, nullable=False)
    selling_price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

    @staticmethod
    def generate_code(pre, id):
        return f"{pre}{id:05d}"

    def save(self):
        if not self.code:
            db.session.flush()  # Ensure the id is generated
            self.code = self.generate_code(self.pre, self.id)
        db.session.add(self)
        db.session.commit()


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
    product_id = db.Column(db.Integer, nullable=False)  # Store the product ID for reference
    product_code = db.Column(db.String(20), nullable=False)
    item = db.Column(db.String(50), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    type_material = db.Column(db.String(50), nullable=False)
    size = db.Column(db.String(10), nullable=False)
    color = db.Column(db.String(20), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    buying_price = db.Column(db.Float, nullable=False)
    selling_price = db.Column(db.Float, nullable=False)
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
    product_id = db.Column(db.Integer, nullable=False)
    product_code = db.Column(db.String(20), nullable=False)
    item = db.Column(db.String(50), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    type_material = db.Column(db.String(50), nullable=False)
    size = db.Column(db.String(10), nullable=False)
    color = db.Column(db.String(20), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    buying_price = db.Column(db.Float, nullable=False)
    selling_price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
