# Thylis, 251684J, group 4
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from functools import wraps
from database import DatabaseHelper
import os
from werkzeug.utils import secure_filename
from datetime import datetime

product_bp = Blueprint('products', __name__, url_prefix='/products')
db_helper = DatabaseHelper()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            flash('Admin privileges required.', 'danger')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

def get_categories_with_defaults():
    """Get product categories from database and merge with default categories."""
    default_categories = ['t-shirts', 'mugs', 'hoodies', 'long-sleeves']
    db_categories = db_helper.get_product_categories()
    # Merge and remove duplicates, preserving order
    all_categories = list(dict.fromkeys(default_categories + [c.lower() for c in db_categories]))
    return sorted(all_categories)

# ===================== PRODUCT LISTING =====================
@product_bp.route('/')
def browse_products():
    # Get filter parameters
    category = request.args.get('category', 'all')
    sort_by = request.args.get('sort', 'newest')
    page = int(request.args.get('page', 1))
    per_page = 12
    
    # Get products from database
    products = db_helper.get_products(
        category=category if category != 'all' else None,
        sort_by=sort_by,
        page=page,
        per_page=per_page
    )
    
    # Get total count for pagination
    total_products = db_helper.get_product_count(category if category != 'all' else None)
    
    # Get categories for filter
    categories = get_categories_with_defaults()
    
    # Calculate pagination
    total_pages = (total_products + per_page - 1) // per_page
    
    return render_template('products.html',
                         products=products,
                         categories=categories,
                         current_category=category,
                         current_sort=sort_by,
                         current_page=page,
                         total_pages=total_pages,
                         total_products=total_products)

# ===================== PRODUCT DETAILS =====================
@product_bp.route('/<int:product_id>')
def product_detail(product_id):
    product = db_helper.get_product_by_id(product_id)
    if not product:
        flash('Product not found.', 'danger')
        return redirect(url_for('products.browse_products'))
    
    # Get related products (product tuple: 0=id, 1=name, 2=desc, 3=category, 4=price, 5=stock, ...)
    related_products = db_helper.get_related_products(product_id, product[3])  # category
    
    # Get product reviews
    reviews = db_helper.get_product_reviews(product_id)
    
    # Get average rating
    avg_rating = db_helper.get_product_average_rating(product_id)
    
    return render_template('product_detail.html',
                         product=product,
                         related_products=related_products,
                         reviews=reviews,
                         avg_rating=avg_rating)

# ===================== ADMIN PRODUCT MANAGEMENT =====================
@product_bp.route('/admin')
@admin_required
def admin_products():
    products = db_helper.get_all_products()
    categories = get_categories_with_defaults()
    # product tuple: 0=id, 1=name, ..., 5=stock, 10=is_active
    active_count = sum(1 for p in products if len(p) > 10 and p[10] == 1)
    out_of_stock_count = sum(1 for p in products if len(p) > 5 and p[5] == 0)
    return render_template('admin_products.html',
                         products=products,
                         categories=categories,
                         active_count=active_count,
                         out_of_stock_count=out_of_stock_count)

# ===================== CREATE PRODUCT (C) =====================
@product_bp.route('/admin/create', methods=['GET', 'POST'])
@admin_required
def create_product():
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form.get('name')
            description = request.form.get('description')
            category = request.form.get('category')
            price = float(request.form.get('price'))
            stock = int(request.form.get('stock'))
            colors = request.form.get('colors', '').split(',')
            sizes = request.form.get('sizes', '').split(',')
            
            # Handle image upload or URL
            image_url = None
            # First check for uploaded file
            if 'image' in request.files:
                image = request.files['image']
                if image and image.filename != '':
                    try:
                        filename = secure_filename(image.filename)
                        # Add timestamp to avoid conflicts
                        from datetime import datetime
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                        filename = timestamp + filename
                        image_path = os.path.join('static/uploads/products', filename)
                        os.makedirs(os.path.dirname(image_path), exist_ok=True)
                        image.save(image_path)
                        image_url = f'uploads/products/{filename}'
                    except Exception as e:
                        flash(f'Error saving image: {str(e)}', 'warning')
            # If no file uploaded, check for image URL
            if not image_url:
                image_url_input = request.form.get('image_url', '').strip()
                if image_url_input:
                    # If it's a full URL, store as-is; if relative, store as-is
                    image_url = image_url_input
            
            # Create product in database
            product_id = db_helper.create_product(
                name=name,
                description=description,
                category=category,
                price=price,
                stock=stock,
                colors=colors,
                sizes=sizes,
                image_url=image_url,
                created_by=session['user_id']
            )
            
            flash('Product created successfully!', 'success')
            return redirect(url_for('products.admin_products'))
            
        except Exception as e:
            flash(f'Error creating product: {str(e)}', 'danger')
    
    categories = get_categories_with_defaults()
    return render_template('product_form.html',
                         action='create',
                         categories=categories)

# ===================== READ PRODUCT DETAILS (R) =====================
@product_bp.route('/admin/<int:product_id>')
@admin_required
def view_product(product_id):
    product = db_helper.get_product_by_id(product_id)
    if not product:
        flash('Product not found.', 'danger')
        return redirect(url_for('products.admin_products'))
    
    # Get product statistics
    stats = db_helper.get_product_statistics(product_id)
    
    return render_template('product_view.html',
                         product=product,
                         stats=stats)

# ===================== UPDATE PRODUCT (U) =====================
@product_bp.route('/admin/<int:product_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_product(product_id):
    product = db_helper.get_product_by_id(product_id)
    if not product:
        flash('Product not found.', 'danger')
        return redirect(url_for('products.admin_products'))
    
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form.get('name')
            description = request.form.get('description')
            category = request.form.get('category')
            price = float(request.form.get('price'))
            stock = int(request.form.get('stock'))
            colors = request.form.get('colors', '').split(',')
            sizes = request.form.get('sizes', '').split(',')
            is_active = 'is_active' in request.form
            
            # Handle image upload or URL
            image_url = product[8]  # current image (keep existing by default)
            file_uploaded = False
            
            # First check for uploaded file (takes precedence)
            if 'image' in request.files:
                image = request.files['image']
                if image and image.filename != '':
                    try:
                        # Delete old image if exists (only if it's a local file)
                        if image_url and not (image_url.startswith('http://') or image_url.startswith('https://')):
                            old_path = os.path.join('static', image_url)
                            if os.path.exists(old_path):
                                os.remove(old_path)
                        
                        # Save new image
                        filename = secure_filename(image.filename)
                        # Add timestamp to avoid conflicts
                        from datetime import datetime
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                        filename = timestamp + filename
                        image_path = os.path.join('static/uploads/products', filename)
                        os.makedirs(os.path.dirname(image_path), exist_ok=True)
                        image.save(image_path)
                        image_url = f'uploads/products/{filename}'
                        file_uploaded = True
                    except Exception as e:
                        flash(f'Error saving image: {str(e)}', 'warning')
            
            # If no file uploaded, check for image URL
            if not file_uploaded:
                image_url_input = request.form.get('image_url', '').strip()
                if image_url_input:
                    # Update to new URL if provided
                    image_url = image_url_input
                # Otherwise, image_url remains as product[8] (existing image)
            
            # Update product in database
            success = db_helper.update_product(
                product_id=product_id,
                name=name,
                description=description,
                category=category,
                price=price,
                stock=stock,
                colors=colors,
                sizes=sizes,
                image_url=image_url,
                is_active=is_active
            )
            
            if success:
                flash('Product updated successfully!', 'success')
                return redirect(url_for('products.admin_products'))
            else:
                flash('Failed to update product.', 'danger')
                
        except Exception as e:
            flash(f'Error updating product: {str(e)}', 'danger')
    
    categories = get_categories_with_defaults()
    return render_template('product_form.html',
                         action='edit',
                         product=product,
                         categories=categories)

# ===================== DELETE PRODUCT (D) =====================
@product_bp.route('/admin/<int:product_id>/delete', methods=['POST'])
@admin_required
def delete_product(product_id):
    try:
        # Get product info before deletion
        product = db_helper.get_product_by_id(product_id)
        if not product:
            flash('Product not found.', 'danger')
            return redirect(url_for('products.admin_products'))
        
        # Delete product image if exists
        if product[8] and os.path.exists(os.path.join('static', product[8])):
            os.remove(os.path.join('static', product[8]))
        
        # Delete product from database
        success = db_helper.delete_product(product_id)
        
        if success:
            flash(f'Product "{product[1]}" deleted successfully!', 'success')
        else:
            flash('Failed to delete product.', 'danger')
            
    except Exception as e:
        flash(f'Error deleting product: {str(e)}', 'danger')
    
    return redirect(url_for('products.admin_products'))

# ===================== TOGGLE PRODUCT STATUS =====================
@product_bp.route('/admin/<int:product_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_product_status(product_id):
    """Toggle a single product's active/inactive status."""
    product = db_helper.get_product_by_id(product_id)
    if not product:
        flash('Product not found.', 'danger')
        return redirect(url_for('products.admin_products'))
    current = bool(product[10])  # is_active is index 10
    success = db_helper.toggle_product_status(product_id, not current)
    if success:
        flash(f'Product {"activated" if not current else "deactivated"} successfully.', 'success')
    else:
        flash('Failed to update product status.', 'danger')
    return redirect(url_for('products.admin_products'))


# ===================== BULK ACTIONS =====================
@product_bp.route('/admin/bulk-actions', methods=['POST'])
@admin_required
def bulk_product_actions():
    action = request.form.get('bulk_action')
    selected_products = request.form.getlist('selected_products')
    
    if not selected_products:
        flash('No products selected.', 'warning')
        return redirect(url_for('products.admin_products'))
    
    success_count = 0
    for product_id in selected_products:
        product_id = int(product_id)
        
        if action == 'activate':
            success = db_helper.toggle_product_status(product_id, True)
        elif action == 'deactivate':
            success = db_helper.toggle_product_status(product_id, False)
        elif action == 'delete':
            success = db_helper.delete_product(product_id)
        else:
            continue
        
        if success:
            success_count += 1
    
    flash(f'Successfully processed {success_count} product(s).', 'success')
    return redirect(url_for('products.admin_products'))

# ===================== PRODUCT REVIEWS =====================
@product_bp.route('/<int:product_id>/reviews', methods=['POST'])
@login_required
def add_review(product_id):
    if request.method == 'POST':
        rating = int(request.form.get('rating'))
        comment = request.form.get('comment')
        
        # Add review to database
        success = db_helper.add_product_review(
            product_id=product_id,
            user_id=session['user_id'],
            rating=rating,
            comment=comment
        )
        
        if success:
            flash('Review submitted successfully!', 'success')
        else:
            flash('Failed to submit review.', 'danger')
    
    return redirect(url_for('products.product_detail', product_id=product_id))

# ===================== ADD TO CART =====================
@product_bp.route('/<int:product_id>/add-to-cart', methods=['POST'])
@login_required
def add_to_cart(product_id):
    quantity = int(request.form.get('quantity', 1))
    size = request.form.get('size')
    color = request.form.get('color')
    
    # Add item to cart
    cart_id = db_helper.add_to_cart(
        user_id=session['user_id'],
        product_id=product_id,
        quantity=quantity,
        size=size,
        color=color
    )
    
    if cart_id:
        flash('Product added to cart!', 'success')
    else:
        flash('Failed to add product to cart.', 'danger')
    
    # Redirect to cart page
    return redirect(url_for('cart'))

# ===================== API ENDPOINTS =====================
@product_bp.route('/api/search')
def search_products():
    query = request.args.get('q', '')
    if not query:
        return jsonify({'products': []})
    
    products = db_helper.search_products(query)
    return jsonify({'products': products})

@product_bp.route('/api/categories')
def get_categories_api():
    categories = get_categories_with_defaults()
    return jsonify({'categories': categories})

@product_bp.route('/api/<int:product_id>/stats')
@admin_required
def get_product_stats(product_id):
    stats = db_helper.get_product_statistics(product_id)
    return jsonify({'stats': stats})

# Add this to product_routes.py - Customize Route

# we allow both numeric ids and string slugs here; the blueprint prefix is '/products',
# so URLs like /products/customize/123 or /products/customize/classic-tshirt will work.
@product_bp.route('/customize/<product_identifier>')
def customize_product(product_identifier):
    """Load the design tool for a specific product.

    The identifier may be the numeric product_id or a slug string.  We first try
    to look up a real database record.  If that fails we fall back to a small
    hard‑coded dictionary matching the static products used by
    ``products.html`` so that the client‑side sample catalogue still works
    even if the database is empty.
    """
    # helper to convert a name into a slug comparable with our static ids
    import re
    def slugify(name: str) -> str:
        return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')

    # default size parameter
    size = request.args.get('size', 'M')

    product = None

    # 1. numeric id?
    if product_identifier.isdigit():
        product = db_helper.get_product_by_id(int(product_identifier))
    else:
        # 2. look through database products by slugified name
        for row in db_helper.get_all_products():
            name = row[1] or ''
            if slugify(name) == product_identifier:
                product = row
                break

    # 3. fallback to static catalogue (matches the JavaScript data in products.html)
    if not product and not product_identifier.isdigit():
        static_products = {
            'classic-tshirt': {
                'id': 'classic-tshirt',
                'name': 'Classic T-Shirt',
                'description': '100% premium cotton, soft and comfortable. Perfect for everyday wear and custom designs. Pre-shrunk fabric maintains shape wash after wash.<br><br>This classic crewneck t-shirt features a comfortable fit, ribbed neckband, and double-stitched seams for durability. Available in a wide range of colors and sizes.',
                'sizes': ['S', 'M', 'L', 'XL', 'XXL'],
                'badges': ['Best Seller', 'In Stock'],
                'category': 't-shirts',
                'colors': ['White', 'Black', 'Gray'],
                'price': 24.99,
                'stock': None,
                'image_url': 'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80'
            },
            'ceramic-mug': {
                'id': 'ceramic-mug',
                'name': 'Ceramic Mug',
                'description': 'High-quality ceramic mug, 11oz capacity, dishwasher and microwave safe. Perfect for hot and cold beverages. Comfortable handle and classic shape.<br><br>Made from premium ceramic material that maintains temperature well. Perfect for coffee, tea, or any beverage. Easy to clean and durable for daily use.',
                'sizes': ['11oz', '15oz', '20oz'],
                'badges': ['New', 'In Stock'],
                'category': 'mugs',
                'colors': ['White', 'Black', 'Blue', 'Green'],
                'price': 16.99,
                'stock': None,
                'image_url': 'https://images.unsplash.com/photo-1544787219-7f47ccb76574?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80'
            },
            'premium-hoodie': {
                'id': 'premium-hoodie',
                'name': 'Premium Hoodie',
                'description': 'Soft 80% cotton / 20% polyester blend hoodie with fleece lining. Features a front kangaroo pocket, adjustable drawstring hood, and ribbed cuffs and hem for comfort and warmth.<br><br>Perfect for cooler weather and casual style. Available in multiple colors with excellent printability for custom designs.',
                'sizes': ['S', 'M', 'L', 'XL'],
                'badges': ['Trending', 'In Stock'],
                'category': 'hoodies',
                'colors': ['Black', 'Gray', 'Navy', 'Maroon'],
                'price': 49.99,
                'stock': None,
                'image_url': 'https://images.unsplash.com/photo-1556821840-3a63f95609a7?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80'
            },
            'travel-mug': {
                'id': 'travel-mug',
                'name': 'Travel Mug',
                'description': '16oz insulated travel mug, leak-proof lid, double-wall vacuum insulation keeps drinks hot or cold for hours. BPA-free materials.<br><br>Perfect for commuting, travel, or outdoor activities. Easy to clean and fits in most car cup holders.',
                'sizes': ['12oz', '16oz', '20oz'],
                'badges': ['New', 'Limited Stock'],
                'category': 'mugs',
                'colors': ['Black', 'Silver', 'Blue'],
                'price': 22.99,
                'stock': None,
                'image_url': 'https://images.unsplash.com/photo-1514228742587-6b1558fcf93a?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80'
            },
            'pullover-hoodie': {
                'id': 'pullover-hoodie',
                'name': 'Pullover Hoodie',
                'description': 'Classic pullover hoodie with front kangaroo pocket and adjustable drawstring hood. Made from soft cotton-polyester blend for ultimate comfort.<br><br>Features ribbed cuffs and hem for better fit. Perfect for layering or wearing on its own.',
                'sizes': ['S', 'M', 'L', 'XL'],
                'badges': ['Popular', 'In Stock'],
                'category': 'hoodies',
                'colors': ['Black', 'Gray', 'Navy', 'Maroon'],
                'price': 44.99,
                'stock': None,
                'image_url': 'https://images.unsplash.com/photo-1578768070128-6ef1356e9da8?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80'
            },
            'vneck-tshirt': {
                'id': 'vneck-tshirt',
                'name': 'V-Neck T-Shirt',
                'description': 'Modern v-neck t-shirt with relaxed fit. Made from 100% ring-spun cotton for softness and durability. Perfect for casual wear.<br><br>The v-neck design offers a contemporary look that pairs well with various outfits. Pre-shrunk fabric maintains shape after washing.',
                'sizes': ['S', 'M', 'L', 'XL'],
                'badges': ['Best Seller', 'In Stock'],
                'category': 't-shirts',
                'colors': ['White', 'Black', 'Gray', 'Navy'],
                'price': 26.99,
                'stock': None,
                'image_url': 'https://images.unsplash.com/photo-1529374255404-311a2a4f1fd9?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80'
            },
            'longsleeve-tshirt': {
                'id': 'longsleeve-tshirt',
                'name': 'Long Sleeve T-Shirt',
                'description': 'Premium long sleeve t-shirt made from 100% cotton. Features ribbed cuffs and hem for comfort and durability. Perfect for cooler weather or layering.<br><br>Soft, breathable fabric with excellent printability for custom designs. Pre-shrunk to maintain shape after washing.',
                'sizes': ['S', 'M', 'L', 'XL'],
                'badges': ['New', 'In Stock'],
                'category': 'long-sleeves',
                'colors': ['White', 'Black', 'Gray', 'Navy'],
                'price': 29.99,
                'stock': None,
                'image_url': 'https://images.unsplash.com/photo-1515365288665-345fde3b7e1a?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80'
            }
        }
        prod = static_products.get(product_identifier)
        if prod:
            product = prod

    if not product:
        flash('Product not found.', 'danger')
        return redirect(url_for('products.browse_products'))

    # convert database row to uniform dict if necessary
    if isinstance(product, tuple):
        product_data = {
            'id': product[0],
            'name': product[1],
            'description': product[2],
            'category': product[3],
            'price': product[4],
            'stock': product[5],
            'colors': product[6].split(',') if product[6] and product[6] != '' else ['White', 'Black', 'Gray'],
            'sizes': product[7].split(',') if product[7] and product[7] != '' else ['S', 'M', 'L', 'XL'],
            'image_url': product[8]
        }
    else:
        # product is already a dict from static_products
        product_data = product

    # Some templates expect `productData` variable name (client-side JS),
    # so provide both keys to keep templates robust.
    return render_template('customize.html', 
                         product=product_data,
                         productData=product_data,
                         size=size)
