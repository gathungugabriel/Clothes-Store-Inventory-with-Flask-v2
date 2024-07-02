from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
import os
from . import db
from .models import User, Product, Stock, Sale, Invoice, InvoiceItem
from .forms import LoginForm, RegistrationForm, UpdateProductForm
from .utils import extract_non_numeric, generate_tag
from add_data import add_products_from_csv
from sqlalchemy.exc import IntegrityError
from .utils import prefixes
from datetime import datetime

# Create a Blueprint for routes
bp = Blueprint('routes', __name__)

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('routes.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', 'error')
            return redirect(url_for('routes.login'))
        login_user(user)
        return redirect(url_for('routes.index'))
    return render_template('login.html', form=form)

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('routes.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data, is_admin=form.is_admin.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!', 'success')
        return redirect(url_for('routes.login'))
    return render_template('register.html', form=form)

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('routes.index'))

@bp.route('/add_product', methods=['GET', 'POST'])
@login_required
def add_product():
    if request.method == 'POST':
        pre = request.form.get('pre')
        code = request.form.get('code')
        item = request.form.get('item')
        category = request.form.get('category')
        type_material = request.form.get('type_material')
        size = request.form.get('size')
        color = request.form.get('color')
        description = request.form.get('description')
        buying_price = request.form.get('buying_price')
        selling_price = request.form.get('selling_price')
        quantity = request.form.get('quantity')
        
        print(f"pre: {pre}, code: {code}, item: {item}, category: {category}, type_material: {type_material}, size: {size}, color: {color}, description: {description}, buying_price: {buying_price}, selling_price: {selling_price}, quantity: {quantity}")
        
        if not pre:
            return "Error: 'pre' field is required.", 400
        
        existing_product = Product.query.filter_by(code=code).first()
        if existing_product:
            flash('A product with this code already exists.', 'error')
            return redirect(url_for('routes.add_product_page'))
        
        new_product = Product(
            pre=pre, 
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
        try:
            db.session.commit()
            update_stock()
        except IntegrityError as e:
            db.session.rollback()
            flash(f"IntegrityError: {str(e)}", 'error')
            return redirect(url_for('routes.add_product_page'))

        flash('Product added successfully!', 'success')
        return redirect(url_for('routes.index'))

    # If GET request, render a template or return a response
    return render_template('add_product.html')

@bp.route('/upload_csv', methods=['GET', 'POST'])
@login_required
def upload_csv():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'error')
            return redirect(request.url)
        
        file = request.files['file']

        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)

        if file:
            try:
                filename = secure_filename(file.filename)
                uploads_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'uploads')
                
                if not os.path.exists(uploads_dir):
                    os.makedirs(uploads_dir)
                
                file_path = os.path.join(uploads_dir, filename)
                file.save(file_path)
                
                add_products_from_csv(file_path)
                update_stock()
                
                flash('CSV uploaded and processed successfully!', 'success')
                return redirect(url_for('routes.view_stock'))
            
            except Exception as e:
                flash(f'Failed to process CSV file: {str(e)}', 'error')
                return redirect(request.url)

    return render_template('upload_csv.html')

@bp.route('/view_stock')
def view_stock():
    stock = get_stock_items()

    grouped_stock = {}
    total_pieces_per_prefix = {}
    item_names = {}

    for item in stock:
        prefix = item['product_code'][:2]
        if prefix not in grouped_stock:
            grouped_stock[prefix] = []
            total_pieces_per_prefix[prefix] = 0
            item_names[prefix] = item['item_name']
        
        grouped_stock[prefix].append(item)
        total_pieces_per_prefix[prefix] += item['pieces']

    total_pieces = sum(total_pieces_per_prefix.values())
    total_bp_summation = sum(item['bp_summation'] for item in stock)
    total_sp_summation = sum(item['sp_summation'] for item in stock)
    total_profit_summation = sum(item['profit_summation'] for item in stock)

    return render_template('view_stocks.html',
                           grouped_stock=grouped_stock,
                           total_pieces_per_prefix=total_pieces_per_prefix,
                           item_names=item_names,
                           total_pieces=total_pieces,
                           total_bp_summation=total_bp_summation,
                           total_sp_summation=total_sp_summation,
                           total_profit_summation=total_profit_summation)

def get_stock_items():
    # Join Stock with Product to get item names
    stock_items = db.session.query(
        Stock.product_code,
        Stock.pieces,
        Stock.bp_summation,
        Stock.sp_summation,
        Stock.profit_summation,
        Product.item.label('item_name')
    ).join(Product, Stock.product_code == Product.code).all()

    stock_list = []
    for stock in stock_items:
        stock_list.append({
            'product_code': stock.product_code,
            'pieces': stock.pieces,
            'bp_summation': stock.bp_summation,
            'sp_summation': stock.sp_summation,
            'profit_summation': stock.profit_summation,
            'item_name': stock.item_name
        })
    return stock_list

@bp.route('/product_details/<string:code>')
def stock_details(code):
    products = Product.query.filter(Product.code.like(code + '%')).all()

    if not products:
        flash(f'No products found for product code {code}', 'danger')

    return render_template('product_details.html', products=products, product_code=code)

@bp.route('/search_product', methods=['POST'])
def search_product():
    search_term = request.form.get('searchInput')
    products = Product.query.filter(Product.item.ilike(f'%{search_term}%')).all()
    return render_template('search_results.html', products=products)

@bp.route('/generate_product_code/<string:prefix>', methods=['GET'])
def generate_product_code(prefix):
    highest_id = db.session.query(db.func.max(Product.id)).filter(Product.code.like(f"{prefix}%")).scalar()
    next_id = highest_id + 1 if highest_id else 1
    return jsonify({'code': f"{prefix}{next_id:04d}"})

@bp.route('/product/delete/<string:code>', methods=['POST'])
@login_required
def delete_product(code):
    product = Product.query.filter_by(code=code).first()
    if product:
        try:
            db.session.delete(product)
            db.session.commit()
            update_stock()
            flash('Product deleted successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while deleting the product: {str(e)}', 'danger')
    else:
        flash(f'Product with code {code} not found.', 'danger')

    return redirect(url_for('routes.view_stock'))

@bp.route('/product/update/<string:code>', methods=['GET', 'POST'])
@login_required
def update_product(code):
    product = Product.query.filter_by(code=code).first()
    if not product:
        flash(f'Product with code {code} not found.', 'danger')
        return redirect(url_for('routes.view_stock'))
        
    form = UpdateProductForm(obj=product)

    if form.validate_on_submit():
        try:
            form.populate_obj(product)
            db.session.commit()
            update_stock()
            flash('Product updated successfully!', 'success')
            return redirect(url_for('routes.view_stock'))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while updating the product: {str(e)}', 'danger')

    return render_template('update_product.html', form=form, product=product)

def update_stock():
    # Clear current stock
    Stock.query.delete()

    # Aggregate product data
    products = Product.query.all()
    stock_data = {}
    for product in products:
        if product.code not in stock_data:
            stock_data[product.code] = {
                'product_code': product.code,
                'pieces': 0,
                'bp_summation': 0,
                'sp_summation': 0,
                'profit_summation': 0,
            }
        stock_data[product.code]['pieces'] += product.quantity
        stock_data[product.code]['bp_summation'] += product.buying_price * product.quantity
        stock_data[product.code]['sp_summation'] += product.selling_price * product.quantity
        stock_data[product.code]['profit_summation'] += (product.selling_price - product.buying_price) * product.quantity

    # Add stock entries to the database
    for data in stock_data.values():
        stock = Stock(
            product_code=data['product_code'],
            pieces=data['pieces'],
            bp_summation=data['bp_summation'],
            sp_summation=data['sp_summation'],
            profit_summation=data['profit_summation']
        )
        db.session.add(stock)
    db.session.commit()

@bp.route('/get_product_details/<string:code>')
def get_product_details(code):
    product = Product.query.filter_by(code=code).first()
    if product:
        return jsonify({'price': product.selling_price})
    else:
        return jsonify({'error': 'Product not found'}), 404

@bp.route('/sales')
def sales():
    query = db.session.query(Sale, Product).join(Product, Sale.product_id == Product.id)

    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    product_codes = request.args.getlist('product')
    entered_product_code = request.args.get('product_code')

    filtering_criteria_present = any([start_date, end_date, product_codes, entered_product_code])

    if start_date:
        query = query.filter(Sale.sale_date >= start_date)
    if end_date:
        query = query.filter(Sale.sale_date <= end_date)
    if product_codes:
        query = query.filter(Product.code.in_(product_codes))
    if entered_product_code:
        query = query.filter(Product.code.like(f'%{entered_product_code}%'))

    sales_data = query.all()

    # Calculate total sales amount
    total_sales_amount = sum(sale.quantity_sold * product.selling_price for sale, product in sales_data)

    # Fetch all products for the filter dropdown
    all_products = Product.query.all()

    return render_template(
        'sales.html',
        sales_data=sales_data,
        total_sales_amount=total_sales_amount,
        products=all_products,
        start_date=start_date,
        end_date=end_date,
        product_codes=product_codes,
        entered_product_code=entered_product_code,
        filtering_criteria_present=filtering_criteria_present
    )

@bp.route('/make_sale', methods=['GET', 'POST'])
@login_required
def make_sale():
    if request.method == 'POST':
        customer_name = request.form.get('customer_name')
        customer_email = request.form.get('customer_email')
        product_codes = request.form.getlist('product_code[]')

        print(f"Customer Name: {customer_name}")
        print(f"Customer Email: {customer_email}")
        print(f"Product Codes: {product_codes}")

        total_sale_amount = 0

        try:
            # Create a new invoice
            invoice = Invoice(
                customer_name=customer_name,
                customer_email=customer_email,
                total_amount=0,  # Will be updated later
                date_created=datetime.now()
            )
            db.session.add(invoice)
            db.session.flush()  # Get the invoice ID before committing

            # Process each product
            for product_code in product_codes:
                product = Product.query.filter_by(code=product_code).first()
                if not product:
                    flash(f'Product with code {product_code} not found.', 'danger')
                    return redirect(url_for('routes.make_sale'))

                if product.quantity <= 0:
                    flash(f'Product {product.item} is out of stock.', 'danger')
                    return redirect(url_for('routes.make_sale'))

                # Add sale record
                sale = Sale(product_id=product.id, quantity_sold=1, sale_date=datetime.now())
                db.session.add(sale)

                # Add invoice item
                invoice_item = InvoiceItem(product_id=product.id, quantity=1, invoice_id=invoice.id)
                db.session.add(invoice_item)

                # Update product quantity and total sale amount
                product.quantity -= 1
                total_sale_amount += product.selling_price

            # Update invoice total amount
            invoice.total_amount = total_sale_amount
            db.session.commit()
            
            flash('Sale and invoice recorded successfully!', 'success')
            return redirect(url_for('routes.view_stock'))

        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while processing the sale: {str(e)}', 'danger')
            print(f"Error: {str(e)}")

    return render_template('make_sales.html')


@bp.route('/invoices', methods=['GET'])
@login_required
def invoices():
    invoices_query = Invoice.query.join(User)
    invoice_number = request.args.get('invoice_number')
    entered_product_code = request.args.get('product_code')

    # Check if any filtering criteria are present
    filtering_criteria_present = invoice_number or entered_product_code

    if invoice_number:
        invoices_query = invoices_query.filter(Invoice.id == invoice_number)
    if entered_product_code:
        invoices_query = invoices_query.join(InvoiceItem).join(Product).filter(Product.code == entered_product_code)

    invoices = invoices_query.all()

    return render_template('invoices.html', invoices=invoices, filtering_criteria_present=filtering_criteria_present)

def generate_invoice_pdf(invoice):
    # Implement the logic to generate a PDF for the invoice
    pass
