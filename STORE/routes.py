from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_file, abort
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
import os
from functools import wraps  
from . import db
from .models import User, Product, Stock, Sale, Invoice, InvoiceItem
from .forms import LoginForm, RegistrationForm, UpdateProductForm
from .utils import extract_non_numeric, generate_tag, prefixes
from add_data import add_products_from_csv
from sqlalchemy.exc import IntegrityError
from datetime import datetime
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy import or_
import csv
from flask import make_response

# Create a Blueprint for routes
bp = Blueprint('routes', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


# Create a Blueprint for routes
bp = Blueprint('routes', __name__)

@bp.route('/')
def initial():
    if current_user.is_authenticated:
        return redirect(url_for('routes.index'))
    return render_template('initial.html')

@bp.route('/index')
@login_required
def index():
    products = Product.query.all()

    grouped_stock = {}
    total_pieces_per_pre = {}
    total_bp_summation_per_pre = {}
    total_sp_summation_per_pre = {}
    total_profit_summation_per_pre = {}
    total_pieces = 0
    total_bp_summation = 0
    total_sp_summation = 0
    total_profit_summation = 0

    for product in products:
        pre = product.pre

        if pre not in grouped_stock:
            grouped_stock[pre] = []
            total_pieces_per_pre[pre] = 0
            total_bp_summation_per_pre[pre] = 0
            total_sp_summation_per_pre[pre] = 0
            total_profit_summation_per_pre[pre] = 0

        grouped_stock[pre].append({
            'product_code': product.code,
            'item_name': product.item,
            'category': product.category,
            'type_material': product.type_material,
            'size': product.size,
            'color': product.color,
            'description': product.description,
            'buying_price': product.buying_price,
            'selling_price': product.selling_price,
            'profit': product.selling_price - product.buying_price,
            'quantity': product.quantity
        })

        total_bp_summation_per_pre[pre] += product.buying_price * product.quantity
        total_sp_summation_per_pre[pre] += product.selling_price * product.quantity
        total_profit_summation_per_pre[pre] += (product.selling_price - product.buying_price) * product.quantity
        total_pieces_per_pre[pre] += product.quantity

    total_bp_summation = sum(total_bp_summation_per_pre.values())
    total_sp_summation = sum(total_sp_summation_per_pre.values())
    total_profit_summation = sum(total_profit_summation_per_pre.values())
    total_pieces = sum(total_pieces_per_pre.values())

    return render_template('index.html', grouped_stock=grouped_stock,
                           total_pieces_per_pre=total_pieces_per_pre, total_pieces=total_pieces,
                           total_bp_summation=total_bp_summation, total_sp_summation=total_sp_summation,
                           total_profit_summation=total_profit_summation,
                           total_bp_summation_per_pre=total_bp_summation_per_pre,
                           total_sp_summation_per_pre=total_sp_summation_per_pre,
                           total_profit_summation_per_pre=total_profit_summation_per_pre)

    
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('auth.index'))  # Replace with the correct endpoint name
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', 'error')
            return redirect(url_for('auth.login'))
        login_user(user)
        return redirect(url_for('routes.index'))
    return render_template('login.html', form=form)

@bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        user.role = 'admin' if form.is_admin.data else 'attendant'
        
        # Ensure username and email are unique
        if User.query.filter_by(username=form.username.data).first():
            flash('Username already exists. Please choose another.', 'danger')
        elif User.query.filter_by(email=form.email.data).first():
            flash('Email already exists. Please choose another.', 'danger')
        else:
            db.session.add(user)
            db.session.commit()
            flash('Congratulations, you are now a registered user!', 'success')
            return redirect(url_for('routes.login'))  # Use 'routes' as the blueprint name
    return render_template('register.html', title='Register', form=form)

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('routes.index'))

@bp.route('/users')
@login_required
def manage_users():
    print(f"Current user: {current_user.username}, Role: {current_user.role}")
    if not current_user.is_admin():
        flash('You do not have permission to view this page.', 'danger')
        return redirect(url_for('routes.index'))
    users = User.query.all()
    return render_template('manage_users.html', users=users)


@bp.route('/user/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_user():
    if not current_user.is_admin():
        flash('You do not have permission to perform this action.', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')

        # Validate the form data
        if not username or not email or not password or not role:
            flash('All fields are required.', 'danger')
            return redirect(url_for('create_user'))

        # Check if the username or email already exists
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash('Username or email already exists.', 'danger')
            return redirect(url_for('create_user'))

        # Create the new user
        new_user = User(username=username, email=email, role=role)
        new_user.set_password(password)

        # Add the user to the database
        db.session.add(new_user)
        db.session.commit()

        flash('User created successfully.', 'success')
        return redirect(url_for('manage_users'))

    return render_template('create_user.html')

@bp.route('/user/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    if not current_user.is_admin():
        flash('You do not have permission to perform this action.', 'danger')
        return redirect(url_for('index'))

    user = User.query.get(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
        flash('User deleted successfully.', 'success')
    else:
        flash('User not found.', 'danger')

    return redirect(url_for('manage_users'))

@bp.route('/add_product', methods=['GET', 'POST'])
@login_required
@admin_required
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
            return redirect(url_for('routes.add_product'))
        
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
            return redirect(url_for('routes.add_product'))

        flash('Product added successfully!', 'success')
        return redirect(url_for('routes.index'))

    # If GET request, render a template or return a response
    return render_template('add_product.html')

@bp.route('/upload_csv', methods=['GET', 'POST'])
@login_required
@admin_required
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

@bp.route('/view_stocks')
def view_stocks():
    # Query all products and group by 'pre'
    products = Product.query.all()

    # Initialize data structures for grouped stock information
    grouped_stock = {}
    total_pieces_per_pre = {}
    total_bp_summation_per_pre = {}
    total_sp_summation_per_pre = {}
    total_profit_summation_per_pre = {}
    total_pieces = 0
    total_bp_summation = 0
    total_sp_summation = 0
    total_profit_summation = 0

    # Process each product
    for product in products:
        pre = product.pre

        if pre not in grouped_stock:
            grouped_stock[pre] = []
            total_pieces_per_pre[pre] = 0
            total_bp_summation_per_pre[pre] = 0
            total_sp_summation_per_pre[pre] = 0
            total_profit_summation_per_pre[pre] = 0

        grouped_stock[pre].append({
            'product_code': product.code,
            'item_name': product.item,
            'category': product.category,
            'type_material': product.type_material,
            'size': product.size,
            'color': product.color,
            'description': product.description,
            'buying_price': product.buying_price,
            'selling_price': product.selling_price,
            'profit': product.selling_price - product.buying_price,
            'quantity': product.quantity
        })

        total_bp_summation_per_pre[pre] += product.buying_price * product.quantity
        total_sp_summation_per_pre[pre] += product.selling_price * product.quantity
        total_profit_summation_per_pre[pre] += (product.selling_price - product.buying_price) * product.quantity
        total_pieces_per_pre[pre] += product.quantity

    total_bp_summation = sum(total_bp_summation_per_pre.values())
    total_sp_summation = sum(total_sp_summation_per_pre.values())
    total_profit_summation = sum(total_profit_summation_per_pre.values())
    total_pieces = sum(total_pieces_per_pre.values())

    return render_template('view_stocks.html', grouped_stock=grouped_stock,
                           total_pieces_per_pre=total_pieces_per_pre, total_pieces=total_pieces,
                           total_bp_summation=total_bp_summation, total_sp_summation=total_sp_summation,
                           total_profit_summation=total_profit_summation,
                           total_bp_summation_per_pre=total_bp_summation_per_pre,
                           total_sp_summation_per_pre=total_sp_summation_per_pre,
                           total_profit_summation_per_pre=total_profit_summation_per_pre)


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

from sqlalchemy import or_

@bp.route('/search_product', methods=['POST'])
def search_product():
    search_query = request.form.get('search')
    if search_query:
        search_filter = f"%{search_query}%"
        products = Product.query.filter(
            or_(
                Product.code.ilike(search_filter),
                Product.item.ilike(search_filter),
                Product.category.ilike(search_filter),
                Product.type_material.ilike(search_filter),
                Product.size.ilike(search_filter),
                Product.color.ilike(search_filter),
                Product.description.ilike(search_filter)
            )
        ).all()

        if products:
            results = []
            for product in products:
                status = 'In Stock'
                if Sale.query.filter_by(product_id=product.id).first():
                    status = 'Sold'
                results.append({
                    'product': product,
                    'status': status
                })
            return render_template('search_results.html', results=results)

    flash('No product found matching the search criteria.', 'danger')
    return redirect(url_for('routes.view_stock'))



@bp.route('/filter_products', methods=['POST'])
def filter_products():
    data = request.get_json()
    search_term = data.get('search_term', '').lower()

    search_filter = f"%{search_term}%"
    products = Product.query.filter(
        or_(
            Product.code.ilike(search_filter),
            Product.item.ilike(search_filter),
            Product.category.ilike(search_filter),
            Product.type_material.ilike(search_filter),
            Product.size.ilike(search_filter),
            Product.color.ilike(search_filter),
            Product.description.ilike(search_filter)
        )
    ).all()

    products_list = [{
        'code': product.code,
        'item': product.item,
        'category': product.category,
        'buying_price': product.buying_price,
        'selling_price': product.selling_price,
        'quantity': product.quantity
    } for product in products]

    return jsonify({'products': products_list})


@bp.route('/_product_code/<string:prefix>')
def _product_code(prefix):
    if prefix in prefixes:
        try:
            new_code = generate_tag(prefix)
            return jsonify({'code': new_code})
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
    return jsonify({'error': 'Invalid prefix'}), 400


@bp.route('/stock_report', methods=['GET', 'POST'])
@login_required
def stock_report():
    filtered_stock = get_stock_items()

    if request.method == 'POST':
        search_term = request.form.get('search_term')
        if search_term:
            filtered_stock = [item for item in filtered_stock if search_term.lower() in item['product_code'].lower() or search_term.lower() in item['item_name'].lower()]

    return render_template('stock_report.html', stock=filtered_stock)

@bp.route('/download_stock_pdf')
@login_required
def download_stock_pdf():
    stock = get_stock_items()

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.setTitle("Stock Report")

    pdf.drawString(30, 750, 'Stock Report')
    y = 720

    total_buying_price = 0
    total_selling_price = 0
    total_quantity = 0

    pdf.drawString(30, y, 'ID | PRE | Code | Item | Category | Type Material | Size | Color | Description | Buying Price | Selling Price | Quantity')
    y -= 20

    for item in stock:
        pdf.drawString(30, y, f"{item['id']} | {item['pre']} | {item['product_code']} | {item['item_name']} | {item['category']} | {item['type_material']} | {item['size']} | {item['color']} | {item['description']} | {item['buying_price']} | {item['selling_price']} | {item['quantity']}")
        total_buying_price += item['buying_price']
        total_selling_price += item['selling_price']
        total_quantity += item['quantity']
        y -= 20

    y -= 20
    pdf.drawString(30, y, f"Totals: | | | | | | | | | {total_buying_price} | {total_selling_price} | {total_quantity}")

    pdf.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name='stock_report.pdf', mimetype='application/pdf')

@bp.route('/download_stock_csv')
@login_required
def download_stock_csv():
    stock = get_stock_items()

    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['ID', 'PRE', 'Code', 'Item', 'Category', 'Type Material', 'Size', 'Color', 'Description', 'Buying Price', 'Selling Price', 'Quantity'])

    total_buying_price = 0
    total_selling_price = 0
    total_quantity = 0

    for item in stock:
        cw.writerow([item['id'], item['pre'], item['product_code'], item['item_name'], item['category'], item['type_material'], item['size'], item['color'], item['description'], item['buying_price'], item['selling_price'], item['quantity']])
        total_buying_price += item['buying_price']
        total_selling_price += item['selling_price']
        total_quantity += item['quantity']

    cw.writerow(['Totals', '', '', '', '', '', '', '', '', total_buying_price, total_selling_price, total_quantity])

    response = make_response(si.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=stock_report.csv'
    response.headers['Content-type'] = 'text/csv'
    return response

def get_stock_items():
    stock_items = db.session.query(
        Stock.id,
        Product.pre,
        Stock.product_code,
        Stock.pieces.label('quantity'),
        Stock.bp_summation.label('buying_price'),
        Stock.sp_summation.label('selling_price'),
        Product.item.label('item_name'),
        Product.category,
        Product.type_material,
        Product.size,
        Product.color,
        Product.description
    ).join(Product, Stock.product_code == Product.code).all()

    stock_list = []
    for stock in stock_items:
        stock_list.append({
            'id': stock.id,
            'pre': stock.pre,
            'product_code': stock.product_code,
            'quantity': stock.quantity,
            'buying_price': stock.buying_price,
            'selling_price': stock.selling_price,
            'item_name': stock.item_name,
            'category': stock.category,
            'type_material': stock.type_material,
            'size': stock.size,
            'color': stock.color,
            'description': stock.description
        })
    return stock_list

@bp.route('/generate_product_code/<string:prefix>', methods=['GET'])
def generate_product_code(prefix):
    highest_id = db.session.query(db.func.max(Product.id)).filter(Product.code.like(f"{prefix}%")).scalar()
    next_id = highest_id + 1 if highest_id else 1
    return jsonify({'code': f"{prefix}{next_id:04d}"})

@bp.route('/product/delete/<string:code>', methods=['POST'])
@login_required
@admin_required
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
@admin_required
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

@bp.route('/sales', methods=['GET', 'POST'])
@login_required
def sales():
    query = db.session.query(Sale)

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
        query = query.filter(Sale.product_code.in_(product_codes))
    if entered_product_code:
        query = query.filter(Sale.product_code.like(f'%{entered_product_code}%'))

    sales_data = query.all()

    # Calculate total sales amount
    total_sales_amount = sum(sale.quantity_sold * sale.selling_price for sale in sales_data)

    return render_template(
        'sales.html',
        sales_data=sales_data,
        total_sales_amount=total_sales_amount,
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
        phone_number = request.form.get('phone_number')
        product_codes = request.form.getlist('product_code[]')

        print(f"Customer Name: {customer_name}")
        print(f"Customer Email: {customer_email}")
        print(f"Phone Number: {phone_number}")
        print(f"Product Codes: {product_codes}")

        total_sale_amount = 0

        try:
            # Create a new invoice
            invoice = Invoice(
                customer_name=customer_name,
                customer_email=customer_email,
                phone_number=phone_number,
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
                sale = Sale(
                    product_id=product.id,
                    product_code=product.code,
                    item=product.item,
                    category=product.category,
                    type_material=product.type_material,
                    size=product.size,
                    color=product.color,
                    description=product.description,
                    buying_price=product.buying_price,
                    selling_price=product.selling_price,
                    quantity_sold=1,
                    sale_date=datetime.now()
                )
                db.session.add(sale)

                # Add invoice item
                invoice_item = InvoiceItem(
                    product_id=product.id,
                    product_code=product.code,
                    item=product.item,
                    category=product.category,
                    type_material=product.type_material,
                    size=product.size,
                    color=product.color,
                    description=product.description,
                    buying_price=product.buying_price,
                    selling_price=product.selling_price,
                    quantity=1,
                    invoice_id=invoice.id
                )
                db.session.add(invoice_item)

                # Update product quantity and total sale amount
                product.quantity -= 1
                total_sale_amount += product.selling_price

                # Remove product if quantity is zero
                if product.quantity == 0:
                    db.session.delete(product)
            
            # Update invoice total amount
            invoice.total_amount = total_sale_amount
            db.session.commit()
            
            flash('Sale and invoice recorded successfully!', 'success')
            return redirect(url_for('routes.print_invoice', invoice_id=invoice.id))

        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while processing the sale: {str(e)}', 'danger')
            print(f"Error: {str(e)}")

    return render_template('make_sales.html')


@bp.route('/invoices', methods=['GET'])
@login_required
def invoices():
    invoices_query = Invoice.query

    invoice_number = request.args.get('invoice_number')
    entered_product_code = request.args.get('product_code')

    # Check if any filtering criteria are present
    filtering_criteria_present = invoice_number or entered_product_code

    if invoice_number:
        invoices_query = invoices_query.filter(Invoice.id == invoice_number)
    if entered_product_code:
        invoices_query = invoices_query.join(InvoiceItem).filter(InvoiceItem.product_code == entered_product_code)

    invoices = invoices_query.all()

    return render_template('invoice.html', invoices=invoices, filtering_criteria_present=filtering_criteria_present)



@bp.route('/print_invoice/<int:invoice_id>', methods=['GET'])
@login_required
def print_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    buffer = io.BytesIO()

    # Create the PDF object, using the buffer as its "file."
    p = canvas.Canvas(buffer, pagesize=letter)
    p.drawString(100, 750, f"Invoice ID: {invoice.id}")
    p.drawString(100, 735, f"Customer Name: {invoice.customer_name}")
    p.drawString(100, 720, f"Customer Email: {invoice.customer_email}")
    p.drawString(100, 705, f"Phone Number: {invoice.phone_number}")
    p.drawString(100, 690, f"Date Created: {invoice.date_created}")
    p.drawString(100, 675, f"Total Amount: {invoice.total_amount}")

    y = 650
    for item in invoice.items:
        p.drawString(100, y, f"Product Code: {item.product_code}, Item: {item.item}, Quantity: {item.quantity}")
        y -= 15

    p.showPage()
    p.save()

    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f'invoice_{invoice.id}.pdf', mimetype='application/pdf')
