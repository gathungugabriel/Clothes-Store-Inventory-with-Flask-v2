from STORE import db
from STORE.models import Product, ProductVariant
import csv

def add_products_from_csv(csv_file):
    try:
        with open(csv_file, 'r', newline='') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                # Validate required fields
                if not all(key in row for key in ['code', 'item', 'category', 'type_material', 'size', 'color', 'description', 'buying_price', 'selling_price']):
                    raise ValueError('Required fields missing in CSV row')
                
                existing_product = Product.query.filter_by(code=row['code']).first()
                if existing_product:
                    print(f"Product with code {row['code']} already exists. Skipping insertion.")
                    continue  # Skip insertion if product already exists
                
                # Begin a new transaction
                db.session.begin()
                
                try:
                    # Insert new product if it doesn't exist
                    product = Product(
                        code=row['code'],
                        item=row['item'],
                        category=row['category'],  # Adjust field name to match CSV header
                        type_material=row['type_material'],
                        description=row['description']
                    )
                    db.session.add(product)
                    db.session.commit()  # Commit product before creating variants
                    
                    # Create ProductVariant instance for each product variant
                    variant = ProductVariant(
                        product_id=product.id,
                        size=row['size'],
                        color=row['color'],
                        quantity=int(row['quantity']),  # Ensure quantity is converted to int
                        buying_price=float(row['buying_price']),
                        selling_price=float(row['selling_price'])
                    )
                    db.session.add(variant)
                    db.session.commit()  # Commit variant
                    
                    # Commit the entire transaction
                    db.session.commit()
                    
                    print(f"Successfully added Product {product.code} and Variant {variant.id}")
                
                except Exception as e:
                    db.session.rollback()  # Rollback transaction on error
                    print(f"Error adding product from CSV: {str(e)}")
                    continue  # Continue to the next row
                
    except Exception as e:
        print(f"Error processing CSV file: {str(e)}")
