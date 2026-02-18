# add_sample_products.py
from database import DatabaseHelper

db = DatabaseHelper()

# Sample products to add
sample_products = [
    {
        'name': 'Classic Cotton T-Shirt',
        'description': 'Premium 100% cotton t-shirt, soft and comfortable. Perfect for everyday wear and custom designs. Pre-shrunk fabric maintains shape wash after wash.',
        'category': 't-shirts',
        'price': 24.99,
        'stock': 100,
        'colors': ['White', 'Black', 'Navy', 'Red', 'Gray'],
        'sizes': ['S', 'M', 'L', 'XL', 'XXL'],
        'image_url': None
    },
    {
        'name': 'Ceramic Coffee Mug',
        'description': 'High-quality ceramic mug, 11oz capacity, dishwasher and microwave safe. Perfect for hot and cold beverages.',
        'category': 'mugs',
        'price': 16.99,
        'stock': 150,
        'colors': ['White', 'Black', 'Blue', 'Green'],
        'sizes': ['11oz', '15oz'],
        'image_url': None
    },
    {
        'name': 'Premium Hoodie',
        'description': 'Soft cotton-polyester blend hoodie with fleece lining. Features front kangaroo pocket and adjustable drawstring hood.',
        'category': 'hoodies',
        'price': 49.99,
        'stock': 75,
        'colors': ['Black', 'Gray', 'Navy', 'Maroon'],
        'sizes': ['S', 'M', 'L', 'XL'],
        'image_url': None
    },
    {
        'name': 'Travel Mug',
        'description': '16oz insulated travel mug, leak-proof lid, double-wall vacuum insulation keeps drinks hot or cold for hours.',
        'category': 'mugs',
        'price': 22.99,
        'stock': 80,
        'colors': ['Black', 'Silver', 'Blue'],
        'sizes': ['16oz'],
        'image_url': None
    },
    {
        'name': 'V-Neck T-Shirt',
        'description': 'Modern v-neck t-shirt with relaxed fit. Made from 100% ring-spun cotton for softness and durability.',
        'category': 't-shirts',
        'price': 26.99,
        'stock': 90,
        'colors': ['White', 'Black', 'Gray', 'Navy'],
        'sizes': ['S', 'M', 'L', 'XL'],
        'image_url': None
    },
    {
        'name': 'Long Sleeve T-Shirt',
        'description': 'Premium long sleeve t-shirt made from 100% cotton. Features ribbed cuffs and hem for comfort and durability.',
        'category': 'long-sleeves',
        'price': 29.99,
        'stock': 60,
        'colors': ['White', 'Black', 'Gray', 'Navy'],
        'sizes': ['S', 'M', 'L', 'XL'],
        'image_url': None
    }
]

# Add products to database
print("Adding sample products to database...")
for product in sample_products:
    product_id = db.create_product(
        name=product['name'],
        description=product['description'],
        category=product['category'],
        price=product['price'],
        stock=product['stock'],
        colors=product['colors'],
        sizes=product['sizes'],
        image_url=product['image_url'],
        created_by=1,  # Assuming admin user ID is 1
        is_active=True
    )
    print(f"✓ Added: {product['name']} (ID: {product_id})")

print("\n✅ Sample products added successfully!")