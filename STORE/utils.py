# utils.py

import re

# Function to extract non-numeric characters from a product code
def extract_non_numeric(code):
    return re.sub(r'\d', '', code)

# Define category and subcategory prefixes
prefixes = {
    'shirt': {'casual': 'SC', 'official': 'SO'},
    'trouser': {'casual': 'TC', 'official': 'TO'},
    'tshirt': {'casual': 'TSC', 'official': 'TSO'},
    'sweater': {'casual': 'SWC', 'official': 'SWO'},
    'coat': {'casual': 'CC', 'official': 'CO'},
    'suit': {'casual': 'SUC', 'official': 'SUO'},
    'tie': 'TIE',
    'belt': 'BLT',
    'short': 'SHRT',
    'shoes': {'casual': 'SHC', 'official': 'SHO'},
    'boxers': 'BX',
    'vest': 'VST'
}

# Function to generate the tag
def generate_tag(category, subcategory=None, item_code=1):
    if category in prefixes:
        if isinstance(prefixes[category], dict):
            if subcategory and subcategory in prefixes[category]:
                return f"{prefixes[category][subcategory]}{item_code:04d}"
            else:
                raise ValueError(f"Invalid subcategory for {category}")
        else:
            return f"{prefixes[category]}{item_code:04d}"
    else:
        raise ValueError("Invalid category")
