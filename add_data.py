import csv
from STORE.models import db, Product

def add_products_from_csv(file_path):
    with open(file_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            try:
                pre_value = row['pre']
                code_value = row['code']  # Read the code from the CSV
                print(f"Pre Value: {pre_value}")  # Debug statement
                print(f"Code Value: {code_value}")  # Debug statement

                product = Product(
                    pre=pre_value,
                    code=code_value,  # Use the code from the CSV
                    item=row['item'],
                    category=row['category'],
                    type_material=row['type_material'],
                    size=row['size'],
                    color=row['color'],
                    description=row['description'],
                    buying_price=float(row['buying_price']),
                    selling_price=float(row['selling_price']),
                    quantity=int(row['quantity'])
                )
                db.session.add(product)
                db.session.commit()
                print(f"Successfully added product: {product}")
            except Exception as e:
                db.session.rollback()
                print(f"Error adding product from CSV: {e}")
