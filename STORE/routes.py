import os
import csv
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from . import app, db
from .models import User, Product, Stock
from .forms import LoginForm, RegistrationForm, UpdateProductForm
from .utils import extract_non_numeric

app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', 'error')
            return redirect(url_for('login'))
        login_user(user)
        return redirect(url_for('index'))
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data, is_admin=form.is_admin.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/add_product', methods=['GET', 'POST'])
@login_required
def add_product():
    if request.method == 'POST':
        code = request.form['code']
        item = request.form['item']
        category = request.form['category']
        type_material = request.form['type_material']
        size = request.form['size']
        color = request.form['color']
        description = request.form['description']
        buying_price = float(request.form['buying_price'])
        selling_price = float(request.form['selling_price'])
        quantity = int(request.form['quantity'])

        new_product = Product(
            code=code,
            item=item,
            category=category,
            type_material=type_material,
            size=size,
            color=color,
            description=description,
            buying_price=buying_price,
            selling_price=selling_price,
            quantity=quantity
        )
        db.session.add(new_product)
        db.session.commit()
        update_stock()
        flash('Product added successfully!', 'success')
        return redirect(url_for('add_product'))

    return render_template('add_product.html')

@app.route('/upload_csv', methods=['GET', 'POST'])
@login_required
def upload_csv():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
        if file and file.filename.endswith('.csv'):
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)
            bulk_insert_from_csv(filepath)
            flash('CSV file uploaded and processed successfully!', 'success')
            return redirect(url_for('upload_csv'))

    return render_template('upload_csv.html')

@app.route('/view_stock')
def view_stock():
    stock = Stock.query.all()

    total_pieces = sum(item.pieces for item in stock)
    total_bp_summation = sum(item.bp_summation for item in stock)
    total_sp_summation = sum(item.sp_summation for item in stock)
    total_profit_summation = sum(item.profit_summation for item in stock)

    return render_template(
        'view_stocks.html',
        stock=stock,
        total_pieces=total_pieces,
        total_bp_summation=total_bp_summation,
        total_sp_summation=total_sp_summation,
        total_profit_summation=total_profit_summation
    )

@app.route('/product_details/<string:code>')
def stock_details(code):
    products = Product.query.filter(Product.code.like(code + '%')).all()

    if not products:
        flash(f'No products found for product code {code}', 'danger')

    return render_template('product_details.html', products=products, product_code=code)

def bulk_insert_from_csv(csv_file_path):
    with open(csv_file_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            new_product = Product(
                code=row['code'],
                item=row['item'],
                category=row['category'],
                type_material=row['type_material'],
                size=row['size'],
                color=row['color'],
                description=row['description'],
                buying_price=float(row['buying_price']),
                selling_price=float(row['selling_price']),
                quantity=int(float(row['quantity'].strip()))  # Convert float to int
            )
            db.session.add(new_product)
        db.session.commit()
    update_stock()

def update_stock():
    stock_entries = db.session.query(
        db.func.substr(Product.code, 1, 2).label('product_class'),
        db.func.sum(Product.buying_price * Product.quantity).label('bp_summation'),
        db.func.sum(Product.selling_price * Product.quantity).label('sp_summation'),
        db.func.sum((Product.selling_price - Product.buying_price) * Product.quantity).label('profit_summation'),
        db.func.sum(Product.quantity).label('pieces')
    ).group_by(db.func.substr(Product.code, 1, 2)).all()

    db.session.query(Stock).delete()  # Clear existing stock data
    db.session.commit()

    for entry in stock_entries:
        product_class = extract_non_numeric(entry.product_class)
        new_stock = Stock(
            product_code=product_class,
            bp_summation=entry.bp_summation,
            sp_summation=entry.sp_summation,
            profit_summation=entry.profit_summation,
            pieces=entry.pieces
        )
        db.session.add(new_stock)
    db.session.commit()

@app.route('/generate_product_code/<string:prefix>', methods=['GET'])
def generate_product_code(prefix):
    # Get the highest product ID with the same prefix
    highest_id = db.session.query(db.func.max(Product.id)).filter(Product.code.like(f"{prefix}%")).scalar()
    next_id = highest_id + 1 if highest_id else 1
    return jsonify({'code': f"{prefix}{next_id:04d}"})


@app.route('/product/delete/<string:code>', methods=['POST'])
@login_required
def delete_product(code):
    product = Product.query.get_or_404(code)

    try:
        db.session.delete(product)
        db.session.commit()
        update_stock()  # Update stock summations after deletion
        flash('Product deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting product: {str(e)}', 'danger')

    return redirect(url_for('view_stock'))

@app.route('/product_details/<string:code>')
def product_details(code):
    cleaned_code = code.strip().upper() + '%'  # Append '%' for pattern matching
    products = Product.query.filter(Product.code.like(cleaned_code)).all()  # Use 'like' for pattern matching
    
    # Print all products to debug the database content
    all_products = Product.query.all()
    print(f"All products in the database: {[p.code for p in all_products]}")
    
    if not products:
        flash(f'No products found for product code {code}', 'danger')
    print(f"Products for code {code}: {products}")  # Debugging line
    return render_template('product_details.html', products=products, product_code=code.strip().upper())

@app.route('/product/update/<string:code>', methods=['GET', 'POST'])
@login_required
def update_product(code):
    product = Product.query.get_or_404(code)
    form = UpdateProductForm(obj=product)  # Create the form with the product object

    if form.validate_on_submit():
        form.populate_obj(product)  # Update the product with form data

        try:
            db.session.commit()
            flash('Product updated successfully!', 'success')
            return redirect(url_for('product_details', code=product.code.split('000')[0]))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating product: {str(e)}', 'danger')

    return render_template('update_product.html', form=form, product=product)
