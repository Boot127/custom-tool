# Yong jun, 252176E, group4 
# Thylis, 251684J, group4
# Ishaani, 252956P, group4
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from functools import wraps
import os
import uuid
import random
import time
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask_wtf import CSRFProtect
from datetime import datetime
import threading
import sqlite3

from Forms import RegistrationForm, LoginForm, ProfileForm, ChangePasswordForm, ContactForm
from database import DatabaseHelper
from admin_routes import admin_bp
from product_routes import product_bp  # Thylis's part - Product Management

app = Flask(__name__)
app.secret_key = os.urandom(24).hex()
app.register_blueprint(admin_bp)
app.register_blueprint(product_bp)  # Thylis's part - Register product blueprint

# CSRF Protection
csrf = CSRFProtect(app)

# Extend CSRF token lifetime for customization pages
app.config['WTF_CSRF_TIME_LIMIT'] = 7200  # 2 hours instead of default 1 hour

# Make csrf_token available in all templates
@app.context_processor
def inject_csrf_token():
    from flask_wtf.csrf import generate_csrf
    return dict(csrf_token=lambda: generate_csrf())

# Endpoint to get fresh CSRF token
@app.route('/api/csrf-token')
def get_csrf_token():
    from flask_wtf.csrf import generate_csrf
    return jsonify({'csrf_token': generate_csrf()})

db_helper = DatabaseHelper()

# OTP storage
otp_storage = {}

# Email configuration - UPDATE THESE WITH YOUR ACTUAL EMAIL SETTINGS
EMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',  # For Gmail. For Outlook: 'smtp.office365.com'
    'smtp_port': 587,
    'sender_email': 'teeyongjun6@gmail.com',  # CHANGE THIS
    'sender_password': 'kvrsmmrndqpglwef',  # CHANGE THIS - use App Password for Gmail
    'use_tls': True,
    'use_ssl': False
}

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/favicon.ico')
def favicon():
    """Prevent 404 for browser favicon requests"""
    return '', 204

# ===================== CART ROUTES - Thylis, 251684J, group 4 =====================
@app.route('/cart')
def cart():
    """Cart page - accessible without login but shows empty cart if not logged in"""
    if 'user_id' not in session:
        # Show empty cart for non-logged in users
        return render_template('cart.html', cart_items=[], total=0, logged_in=False)
    
    try:
        user_id = session.get('user_id')
        if not user_id:
            return render_template('cart.html', cart_items=[], total=0, logged_in=False)
        
        # Get cart items for the current user ONLY
        conn = sqlite3.connect('custom_design.db')
        cursor = conn.cursor()
        
        # Verify user exists
        cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
        if not cursor.fetchone():
            conn.close()
            return render_template('cart.html', cart_items=[], total=0, logged_in=False)
        
        # Get cart items ONLY for this specific user
        # Double-check: Also verify user_id in the WHERE clause
        cursor.execute('''
            SELECT ci.id, p.product_id, p.name, p.price, ci.quantity, p.image_url, 
                   ci.size, ci.color, ci.design_data, p.category
            FROM cart_items ci
            JOIN products p ON ci.product_id = p.product_id
            WHERE ci.user_id = ? AND ci.user_id = ?
            ORDER BY ci.created_at DESC
        ''', (user_id, user_id))  # Redundant but ensures safety
        cart_items = cursor.fetchall()
        
        # Clean up duplicates - merge items with identical design_data
        seen_designs = {}
        items_to_remove = []
        items_to_update = []
        
        for item in cart_items:
            item_id = item[0]
            design_data = item[8]
            product_id = item[1]
            size = item[6]
            color = item[7]
            quantity = item[4]
            
            # Create a key for comparison
            if design_data:
                try:
                    parsed = json.loads(design_data)
                    elements = parsed.get('elements', [])
                    # Normalize elements
                    normalized_elements = []
                    for elem in elements:
                        if isinstance(elem, dict):
                            elem_copy = {k: v for k, v in elem.items() 
                                       if k not in ['id', 'submission_id', 'timestamp']}
                            normalized_elements.append(elem_copy)
                    normalized_elements.sort(key=lambda x: (x.get('type', ''), str(sorted(x.items()))))
                    design_key = json.dumps(normalized_elements, sort_keys=True)
                except:
                    design_key = design_data.strip() if design_data else None
            else:
                design_key = None
            
            comparison_key = f"{product_id}_{size}_{color}_{design_key}"
            
            if comparison_key in seen_designs:
                # Merge with existing item
                existing_id, existing_qty = seen_designs[comparison_key]
                items_to_update.append((existing_id, existing_qty + quantity))
                items_to_remove.append(item_id)
            else:
                seen_designs[comparison_key] = (item_id, quantity)
        
        # Update quantities for merged items
        for item_id, new_quantity in items_to_update:
            cursor.execute('''
                UPDATE cart_items SET quantity = ? WHERE id = ?
            ''', (new_quantity, item_id))
        
        # Remove duplicate items
        if items_to_remove:
            placeholders = ','.join(['?'] * len(items_to_remove))
            cursor.execute(f'''
                DELETE FROM cart_items WHERE id IN ({placeholders})
            ''', items_to_remove)
        
        conn.commit()
        
        # Fetch updated cart items - ensure we only get items for this user
        user_id = session.get('user_id')
        cursor.execute('''
            SELECT ci.id, p.product_id, p.name, p.price, ci.quantity, p.image_url, 
                   ci.size, ci.color, ci.design_data, p.category
            FROM cart_items ci
            JOIN products p ON ci.product_id = p.product_id
            WHERE ci.user_id = ?
            ORDER BY ci.created_at DESC
        ''', (user_id,))
        cart_items = cursor.fetchall()
        conn.close()
        
        # Process cart items to set default images for mugs and specific t-shirts
        processed_cart_items = []
        for item in cart_items:
            item_list = list(item)
            image_url = item_list[5]
            product_name = (item_list[2] or '').lower() if len(item_list) > 2 else ''
            category = (item_list[9] or '').lower() if len(item_list) > 9 else ''
            is_mug = category == 'mugs' or category == 'mug'
            
            # Check for specific product names/categories to use default images
            is_crewneck = 'crew neck' in product_name or 'crewneck' in product_name
            is_classic_cotton = 'classic cotton' in product_name or ('classic' in product_name and 't-shirt' in product_name)
            is_hoodie = category in ('hoodies', 'hoodie') or 'hoodie' in product_name
            is_long_sleeve = category in ('long-sleeves', 'long sleeves') or 'long sleeve' in product_name or 'longsleeve' in product_name
            
            # If no image URL, use default images based on product type
            if not image_url or image_url == '' or image_url == 'null' or image_url == 'undefined':
                if is_mug:
                    item_list[5] = '/static/images/default-mug.png'
                elif is_hoodie:
                    item_list[5] = '/static/images/default-hoodie.png'
                elif is_long_sleeve:
                    item_list[5] = '/static/images/default-longsleeve.png'
                elif is_crewneck:
                    item_list[5] = '/static/images/default-crewneck-tshirt.png'
                elif is_classic_cotton:
                    item_list[5] = '/static/images/default-classic-tshirt.png'
            elif image_url and not (image_url.startswith('http://') or image_url.startswith('https://')):
                # Format relative paths
                if not image_url.startswith('/'):
                    item_list[5] = '/static/' + image_url
            processed_cart_items.append(tuple(item_list))
        
        cart_items = processed_cart_items
        
        # Calculate total
        total = sum(item[3] * item[4] for item in cart_items)  # price * quantity
        
        # Debug: Log cart items count for troubleshooting
        print(f"Cart loaded for user_id {user_id}: {len(cart_items)} items")
        
        # If user just logged in and has items, they might be old items
        # You can uncomment the next line to clear cart on every cart view (not recommended)
        # cursor.execute('DELETE FROM cart_items WHERE user_id = ?', (user_id,))
        # conn.commit()
        
        return render_template('cart.html', cart_items=cart_items, total=total, logged_in=True)
    except Exception as e:
        print(f"Cart error: {e}")
        import traceback
        traceback.print_exc()
        return render_template('cart.html', cart_items=[], total=0, logged_in=True)

@app.route('/products')
def products_redirect():
    """Redirect to the products listing page"""
    return redirect(url_for('products.browse_products'))

@app.route('/customize/<int:product_id>')
def design_tool(product_id):
    """Load the design tool for a specific product"""
    # Get product from database
    product = db_helper.get_product_by_id(product_id)
    
    if not product:
        flash('Product not found. Add products in the Manager panel (Manager → Products) so you can customize them.', 'warning')
        return redirect(url_for('products.browse_products'))
    
    # Get size from query parameter
    size = request.args.get('size', 'M')
    
    # Format product data for template
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
    
    # Provide both `product` and `productData` to the template because
    # some templates/scripts refer to `productData` (client JS expects it).
    return render_template('customize.html', 
                         product=product_data,
                         productData=product_data,
                         size=size)

@app.route('/cart/add/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    """Add item to cart (supports customized products)"""
    try:
        quantity = int(request.form.get('quantity', 1))
        size = request.form.get('size', 'M')
        color = request.form.get('color', 'White')
        design_data = request.form.get('design_data')
        
        # Normalize design_data for comparison (parse and re-stringify to handle formatting differences)
        normalized_design_data = None
        if design_data and design_data.strip():
            try:
                # Parse and re-stringify to normalize JSON formatting
                parsed = json.loads(design_data)
                normalized_design_data = json.dumps(parsed, sort_keys=True)
            except:
                normalized_design_data = design_data.strip()
        
        # Use a transaction to prevent race conditions
        conn = sqlite3.connect('custom_design.db')
        cursor = conn.cursor()
        
        # Start immediate transaction to lock the table
        cursor.execute('BEGIN IMMEDIATE')
        
        try:
            # For customized items, we need to check if same design exists
            # Get all items for this user/product/size/color combination WITHIN TRANSACTION
            cursor.execute('''
                SELECT id, quantity, design_data FROM cart_items 
                WHERE user_id = ? AND product_id = ? AND size = ? AND color = ?
            ''', (session['user_id'], product_id, size, color))
            
            existing_items = cursor.fetchall()
            existing_item = None
            
            if normalized_design_data:
                # For customized items, compare normalized design_data
                # Extract and normalize elements array for better matching
                def normalize_elements_for_comparison(elements):
                    """Normalize elements array by removing IDs and sorting"""
                    if not elements:
                        return None
                    normalized = []
                    for elem in elements:
                        if isinstance(elem, dict):
                            # Remove ID and timestamp fields that change
                            elem_copy = {k: v for k, v in elem.items() 
                                       if k not in ['id', 'submission_id', 'timestamp']}
                            normalized.append(elem_copy)
                    # Sort by type and content for consistent comparison
                    normalized.sort(key=lambda x: (x.get('type', ''), str(sorted(x.items()))))
                    return json.dumps(normalized, sort_keys=True)
                
                try:
                    parsed = json.loads(normalized_design_data)
                    design_elements = parsed.get('elements', [])
                    normalized_elements_str = normalize_elements_for_comparison(design_elements)
                except:
                    normalized_elements_str = None
                
                for item in existing_items:
                    item_design_data = item[2]
                    if item_design_data:
                        try:
                            item_parsed = json.loads(item_design_data)
                            item_normalized = json.dumps(item_parsed, sort_keys=True)
                            
                            # Compare full normalized data first
                            if item_normalized == normalized_design_data:
                                existing_item = item
                                break
                            
                            # Compare elements if available (more reliable)
                            if normalized_elements_str:
                                item_elements = item_parsed.get('elements', [])
                                item_elements_str = normalize_elements_for_comparison(item_elements)
                                if item_elements_str and item_elements_str == normalized_elements_str:
                                    existing_item = item
                                    break
                        except Exception as e:
                            # Fallback to string comparison
                            if item_design_data.strip() == normalized_design_data.strip():
                                existing_item = item
                                break
            else:
                # For regular products, find item with NULL design_data
                for item in existing_items:
                    if not item[2] or item[2].strip() == '':
                        existing_item = item
                        break
            
            if existing_item:
                # Update quantity (don't add duplicate)
                new_quantity = existing_item[1] + quantity
                cursor.execute('''
                    UPDATE cart_items SET quantity = ? 
                    WHERE id = ?
                ''', (new_quantity, existing_item[0]))
                message = 'Item quantity updated in cart!'
            else:
                # Add new item with customization data
                cursor.execute('''
                    INSERT INTO cart_items (user_id, product_id, quantity, size, color, design_data, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (session['user_id'], product_id, quantity, size, color, normalized_design_data, datetime.now()))
                message = 'Customized item added to cart!'
            
            # Commit transaction
            conn.commit()
            conn.close()
            
        except Exception as e:
            # Rollback on error
            conn.rollback()
            conn.close()
            raise e
        
        flash(message, 'success')
        return redirect(url_for('cart'))
        
    except Exception as e:
        flash(f'Error adding to cart: {str(e)}', 'danger')
        return redirect(request.referrer or url_for('home'))

@app.route('/cart/update/<int:item_id>', methods=['POST'])
@login_required
def update_cart_item(item_id):
    """Update cart item quantity"""
    try:
        quantity = int(request.form.get('quantity', 1))
        
        if quantity <= 0:
            # Remove item
            conn = sqlite3.connect('custom_design.db')
            cursor = conn.cursor()
            cursor.execute('DELETE FROM cart_items WHERE id = ? AND user_id = ?', 
                         (item_id, session['user_id']))
            conn.commit()
            conn.close()
            flash('Item removed from cart', 'info')
        else:
            # Update quantity
            conn = sqlite3.connect('custom_design.db')
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE cart_items SET quantity = ? 
                WHERE id = ? AND user_id = ?
            ''', (quantity, item_id, session['user_id']))
            conn.commit()
            conn.close()
            flash('Cart updated', 'success')
        
        return redirect(url_for('cart'))
    except Exception as e:
        flash(f'Error updating cart: {str(e)}', 'danger')
        return redirect(url_for('cart'))

@app.route('/cart/remove/<int:item_id>', methods=['POST'])
@login_required
def remove_cart_item(item_id):
    """Remove item from cart"""
    try:
        conn = sqlite3.connect('custom_design.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM cart_items WHERE id = ? AND user_id = ?', 
                     (item_id, session['user_id']))
        conn.commit()
        conn.close()
        flash('Item removed from cart', 'info')
        return redirect(url_for('cart'))
    except Exception as e:
        flash(f'Error removing item: {str(e)}', 'danger')
        return redirect(url_for('cart'))

@app.route('/cart/clear', methods=['POST'])
@login_required
def clear_cart():
    """Clear entire cart"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            flash('Please log in to clear your cart', 'warning')
            return redirect(url_for('cart'))
        
        conn = sqlite3.connect('custom_design.db')
        cursor = conn.cursor()
        # Double-check: only delete items for this specific user
        cursor.execute('DELETE FROM cart_items WHERE user_id = ?', (user_id,))
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        flash(f'Cart cleared successfully. Removed {deleted_count} item(s).', 'success')
        return redirect(url_for('cart'))
    except Exception as e:
        flash(f'Error clearing cart: {str(e)}', 'danger')
        return redirect(url_for('cart'))

# Cart count API (for navbar cart badge)
@app.route('/api/cart/count')
def cart_count():
    if 'user_id' not in session:
        return jsonify({'count': 0})

    try:
        conn = sqlite3.connect('custom_design.db')
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM cart_items WHERE user_id = ?', (session['user_id'],))
        count = cursor.fetchone()[0]
        conn.close()
        return jsonify({'count': count})
    except:
        return jsonify({'count': 0})

# Cart data API (return cart items as JSON for client-side rendering)
@app.route('/api/cart/data')
def cart_data():
    """Get cart data as JSON - no Jinja2 template needed"""
    if 'user_id' not in session:
        return jsonify({'logged_in': False, 'cart_items': []})

    try:
        user_id = session.get('user_id')
        conn = sqlite3.connect('custom_design.db')
        cursor = conn.cursor()
        
        # Get cart items for the current user
        cursor.execute('''
            SELECT ci.id, p.product_id, p.name, p.price, ci.quantity, p.image_url, 
                   ci.size, ci.color, ci.design_data, p.category
            FROM cart_items ci
            JOIN products p ON ci.product_id = p.product_id
            WHERE ci.user_id = ?
            ORDER BY ci.created_at DESC
        ''', (user_id,))
        cart_items = cursor.fetchall()
        conn.close()
        
        # Convert tuples to lists for JSON serialization and format image URLs
        cart_items_list = []
        for item in cart_items:
            item_list = list(item)
            # Format image URL (index 5), product name (index 2), and category (index 9)
            image_url = item_list[5]
            product_name = (item_list[2] or '').lower() if len(item_list) > 2 else ''
            category = (item_list[9] or '').lower() if len(item_list) > 9 else ''
            is_mug = category == 'mugs' or category == 'mug'
            
            # Check for specific product names/categories to use default images
            is_crewneck = 'crew neck' in product_name or 'crewneck' in product_name
            is_classic_cotton = 'classic cotton' in product_name or ('classic' in product_name and 't-shirt' in product_name)
            is_hoodie = category in ('hoodies', 'hoodie') or 'hoodie' in product_name
            is_long_sleeve = category in ('long-sleeves', 'long sleeves') or 'long sleeve' in product_name or 'longsleeve' in product_name
            
            # If no image URL, use default images based on product type
            if not image_url or image_url == '' or image_url == 'null' or image_url == 'undefined':
                if is_mug:
                    item_list[5] = '/static/images/default-mug.png'
                elif is_hoodie:
                    item_list[5] = '/static/images/default-hoodie.png'
                elif is_long_sleeve:
                    item_list[5] = '/static/images/default-longsleeve.png'
                elif is_crewneck:
                    item_list[5] = '/static/images/default-crewneck-tshirt.png'
                elif is_classic_cotton:
                    item_list[5] = '/static/images/default-classic-tshirt.png'
                else:
                    item_list[5] = None
            elif image_url:
                # If it's already a full URL, keep it
                if not (image_url.startswith('http://') or image_url.startswith('https://')):
                    # If it starts with /, keep it
                    if not image_url.startswith('/'):
                        # Prepend /static/ for relative paths
                        item_list[5] = '/static/' + image_url
            cart_items_list.append(item_list)
        
        return jsonify({'logged_in': True, 'cart_items': cart_items_list})
    except Exception as e:
        print(f"Cart data API error: {e}")
        return jsonify({'logged_in': False, 'cart_items': []})

# API to sync localStorage cart to database when user logs in
@csrf.exempt
@app.route('/api/cart/sync', methods=['POST'])
@login_required
def sync_cart():
    """Sync localStorage cart items to database for logged-in user"""
    try:
        data = request.get_json() or {}
        items = data.get('items', data.get('cart_items', []))

        if not items:
            return jsonify({'success': True, 'synced': 0})

        conn = sqlite3.connect('custom_design.db')
        cursor = conn.cursor()
        synced_count = 0

        for item in items:
            try:
                product_id = int(item.get('id', item.get('product_id', 0)))
            except (TypeError, ValueError):
                continue
            quantity = int(item.get('quantity', 1))
            if quantity < 1:
                continue

            # Check if product exists (products table uses product_id column)
            cursor.execute('SELECT product_id FROM products WHERE product_id = ?', (product_id,))
            if not cursor.fetchone():
                continue  # Skip invalid products

            # Check if already in cart
            cursor.execute('''
                SELECT id, quantity FROM cart_items
                WHERE user_id = ? AND product_id = ?
            ''', (session['user_id'], product_id))
            existing = cursor.fetchone()

            if existing:
                # Update quantity
                new_qty = existing[1] + quantity
                cursor.execute('UPDATE cart_items SET quantity = ? WHERE id = ?',
                             (new_qty, existing[0]))
            else:
                # Insert new item
                cursor.execute('''
                    INSERT INTO cart_items (user_id, product_id, quantity, created_at)
                    VALUES (?, ?, ?, ?)
                ''', (session['user_id'], product_id, quantity, datetime.now()))

            synced_count += 1

        conn.commit()
        conn.close()

        # Store cart in session for checkout when items couldn't sync (e.g. string IDs from products page)
        session['checkout_cart'] = [
            (item.get('id', item.get('product_id')), item.get('name', 'Item'),
            float(item.get('price', 0)), int(item.get('quantity', 1)))
            for item in items
        ]

        return jsonify({'success': True, 'synced': synced_count})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

# ===================== CHECKOUT ROUTES - Ishaani, 252956P group 4 =====================
@app.route('/checkout')
@login_required
def checkout():
    """Checkout page - requires login"""
    try:
        # Get cart items
        conn = sqlite3.connect('custom_design.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.product_id, p.name, p.price, ci.quantity
            FROM cart_items ci
            JOIN products p ON ci.product_id = p.product_id
            WHERE ci.user_id = ?
        ''', (session['user_id'],))
        cart_items = cursor.fetchall()

        # Get user info
        cursor.execute('SELECT email, username FROM users WHERE user_id = ?',
                      (session['user_id'],))
        user_info = cursor.fetchone()
        conn.close()

        # Use session cart if database cart is empty (e.g. items from products page with string IDs)
        if not cart_items and session.get('checkout_cart'):
            cart_items = session['checkout_cart']
        elif not cart_items:
            flash('Your cart is empty. Add items before checkout.', 'warning')
            return redirect(url_for('products.browse_products'))

        # Calculate totals
        subtotal = sum(item[2] * item[3] for item in cart_items)
        shipping = 0 if subtotal >= 75 else 5.99
        total = subtotal + shipping

        return render_template('checkout.html',
                             cart_items=cart_items,
                             subtotal=subtotal,
                             shipping=shipping,
                             total=total,
                             user_email=user_info[0] if user_info else '',
                             username=user_info[1] if user_info else '')
    except Exception as e:
        flash(f'Error loading checkout: {str(e)}', 'danger')
        return redirect(url_for('cart'))
#===================== PLACE ORDER ROUTE - ISHAANI 252956P, group 4 =====================
@csrf.exempt
@app.route('/place-order', methods=['POST'])
@login_required
def place_order():
    """Place an order and send email receipt"""
    try:
        # Get form data
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        address = request.form.get('address')
        city = request.form.get('city')
        zip_code = request.form.get('zip_code')
        card_number = request.form.get('card_number', '')
        delivery_option = request.form.get('delivery_option', 'standard')

        # Validate required fields
        if not all([full_name, email, address, city, zip_code]):
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('checkout'))

        # Get cart items from database or session
        conn = sqlite3.connect('custom_design.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.product_id, p.name, p.price, ci.quantity
            FROM cart_items ci
            JOIN products p ON ci.product_id = p.product_id
            WHERE ci.user_id = ?
        ''', (session['user_id'],))
        cart_items = cursor.fetchall()

        # Use session cart if database cart is empty
        if not cart_items and session.get('checkout_cart'):
            cart_items = session['checkout_cart']
            conn.close()
            conn = sqlite3.connect('custom_design.db')
            cursor = conn.cursor()
        elif not cart_items:
            flash('Your cart is empty.', 'warning')
            conn.close()
            return redirect(url_for('products.browse_products'))

        # Calculate totals
        subtotal = sum(item[2] * item[3] for item in cart_items)
        shipping = 0 if subtotal >= 75 else 5.99
        total = subtotal + shipping

        # Create order
        shipping_address = f"{address}, {city}, {zip_code}"
        card_last_four = card_number[-4:] if card_number else 'N/A'

        cursor.execute('''
            INSERT INTO orders (user_id, full_name, card_last_four, delivery_option,
                              shipping_address, total, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
        ''', (session['user_id'], full_name, card_last_four, delivery_option,
              shipping_address, total, datetime.now()))
        order_id = cursor.lastrowid

        # Store order items for confirmation page
        for item in cart_items:
            cursor.execute('''
                INSERT INTO order_items (order_id, product_name, price, quantity)
                VALUES (?, ?, ?, ?)
            ''', (order_id, item[1], item[2], item[3]))

        # Clear cart from database and session
        cursor.execute('DELETE FROM cart_items WHERE user_id = ?', (session['user_id'],))
        conn.commit()
        conn.close()
        session.pop('checkout_cart', None)

        # Send email receipt in background
        threading.Thread(target=send_order_receipt_async,
                        args=(email, order_id, full_name, cart_items, subtotal, shipping, total, shipping_address)).start()

        flash('Order placed successfully! Check your email for the receipt.', 'success')
        return redirect(url_for('order_confirmation', order_id=order_id))

    except Exception as e:
        flash(f'Error placing order: {str(e)}', 'danger')
        return redirect(url_for('checkout'))
##===================== order confirmation - ISHAANI 252956P, group 4 =====================
@app.route('/order-confirmation/<int:order_id>')
@login_required
def order_confirmation(order_id):
    """Order confirmation page"""
    try:
        conn = sqlite3.connect('custom_design.db')
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT order_id, full_name, total, shipping_address, created_at, status,
                       delivery_option
                FROM orders
                WHERE order_id = ? AND user_id = ?
            ''', (order_id, session['user_id']))
        except sqlite3.OperationalError:
            cursor.execute('''
                SELECT order_id, full_name, total, shipping_address, created_at, status
                FROM orders
                WHERE order_id = ? AND user_id = ?
            ''', (order_id, session['user_id']))
        row = cursor.fetchone()
        if not row:
            conn.close()
            flash('Order not found.', 'danger')
            return redirect(url_for('home'))

        # Fetch order items (product_name, price, quantity) - format as (id, name, price, qty)
        try:
            cursor.execute('''
                SELECT id, product_name, price, quantity FROM order_items
                WHERE order_id = ?
            ''', (order_id,))
            order_items = [(r[0], r[1], r[2], r[3]) for r in cursor.fetchall()]
        except sqlite3.OperationalError:
            order_items = []

        # Fetch user email
        cursor.execute('SELECT email FROM users WHERE user_id = ?', (session['user_id'],))
        user_row = cursor.fetchone()
        user_email = user_row[0] if user_row else ''

        conn.close()

        # Parse shipping_address: "address, city, zip_code"
        parts = row[3].rsplit(', ', 2) if row[3] else ['', '', '']
        address = parts[0] if len(parts) > 0 else ''
        city = parts[1] if len(parts) > 1 else ''
        zip_code = parts[2] if len(parts) > 2 else ''

        # Derive subtotal and shipping from total
        total = float(row[2])
        shipping = 5.99 if total < 75 else 0
        subtotal = total - shipping

        # Build order dict for template (expects attribute access)
        delivery_opt = row[6] if len(row) > 6 else 'standard'
        order = type('Order', (), {
            'id': row[0],
            'full_name': row[1],
            'total': total,
            'email': user_email,
            'address': address,
            'city': city,
            'zip_code': zip_code,
            'subtotal': subtotal,
            'shipping': shipping,
            'delivery_option': delivery_opt
        })()

        return render_template('order_confirmation.html', order=order, order_items=order_items)
    except Exception as e:
        flash(f'Error loading order: {str(e)}', 'danger')
        return redirect(url_for('home'))
# ===================== order receipt - ISHAANI 252956P, group 4 =====================
def send_order_receipt_async(email, order_id, customer_name, items, subtotal, shipping, total, address):
    """Send order receipt email asynchronously"""
    try:
        # Build items HTML
        items_html = ""
        for item in items:
            item_total = item[2] * item[3]  # price * quantity
            items_html += f"""
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #eee;">{item[1]}</td>
                <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: center;">{item[3]}</td>
                <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: right;">${item[2]:.2f}</td>
                <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: right;">${item_total:.2f}</td>
            </tr>
            """

        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f5f5f5;">
                <div style="background-color: #A68A64; padding: 20px; text-align: center;">
                    <h1 style="color: white; margin: 0;">DesignCraft Studio</h1>
                    <p style="color: #E3D5C6; margin: 5px 0;">Order Receipt</p>
                </div>

                <div style="background-color: white; padding: 30px; margin-top: 20px;">
                    <h2 style="color: #A68A64;">Thank You for Your Order!</h2>
                    <p>Dear {customer_name},</p>
                    <p>Your order has been confirmed and is being processed. Here are the details:</p>

                    <div style="background-color: #f9f9f9; padding: 15px; margin: 20px 0; border-left: 4px solid #9CAF88;">
                        <p style="margin: 5px 0;"><strong>Order ID:</strong> #{order_id}</p>
                        <p style="margin: 5px 0;"><strong>Shipping Address:</strong> {address}</p>
                    </div>

                    <h3 style="color: #A68A64; margin-top: 30px;">Order Summary</h3>
                    <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                        <thead>
                            <tr style="background-color: #f0f0f0;">
                                <th style="padding: 10px; text-align: left;">Product</th>
                                <th style="padding: 10px; text-align: center;">Quantity</th>
                                <th style="padding: 10px; text-align: right;">Price</th>
                                <th style="padding: 10px; text-align: right;">Total</th>
                            </tr>
                        </thead>
                        <tbody>
                            {items_html}
                        </tbody>
                    </table>

                    <div style="text-align: right; margin-top: 20px; padding-top: 20px; border-top: 2px solid #eee;">
                        <p style="margin: 5px 0;"><strong>Subtotal:</strong> ${subtotal:.2f}</p>
                        <p style="margin: 5px 0;"><strong>Shipping:</strong> {'FREE' if shipping == 0 else f'${shipping:.2f}'}</p>
                        <p style="margin: 10px 0; font-size: 1.2em; color: #A68A64;"><strong>Total: ${total:.2f}</strong></p>
                    </div>

                    <div style="background-color: #E3D5C6; padding: 15px; margin-top: 30px; text-align: center;">
                        <p style="margin: 0;">Questions? Contact us at support@designcraftstudio.com</p>
                    </div>
                </div>

                <div style="text-align: center; padding: 20px; color: #666; font-size: 12px;">
                    <p>© 2024 DesignCraft Studio. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        msg = MIMEMultipart()
        msg['From'] = EMAIL_CONFIG['sender_email']
        msg['To'] = email
        msg['Subject'] = f'Order Confirmation - Order #{order_id} - DesignCraft Studio'

        msg.attach(MIMEText(body, 'html'))

        server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
        server.starttls()
        server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
        server.send_message(msg)
        server.quit()

        print(f"✅ Order receipt sent to {email} for order #{order_id}")
        return True
    except Exception as e:
        print(f"❌ Failed to send receipt email: {str(e)}")
        return False

# ===================== YONG JUN'S PART - USER MANAGEMENT =====================
def send_otp_email_async(email, otp):
    try:
        print("📧 Connecting to SMTP server...")

        msg = MIMEMultipart()
        msg['From'] = EMAIL_CONFIG['sender_email']
        msg['To'] = email
        msg['Subject'] = 'DesignCraft Studio - Email Verification Code'

        body = f"""
        <h2>Email Verification</h2>
        <p>Your OTP code is:</p>
        <h1 style="letter-spacing:5px;">{otp}</h1>
        <p>This code expires in 10 minutes.</p>
        """

        msg.attach(MIMEText(body, 'html'))

        server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
        server.starttls()
        server.login(
            EMAIL_CONFIG['sender_email'],
            EMAIL_CONFIG['sender_password']
        )
        server.send_message(msg)
        server.quit()

        print(f"✅ OTP email sent to {email}")
        return True

    except Exception as e:
        print("❌ Email sending failed:", str(e))
        return False

@csrf.exempt
@app.route('/send-otp', methods=['POST'])
def send_otp():
    data = request.json
    email = data.get('email')
    
    if not email:
        return jsonify({'success': False, 'message': 'Email is required'})
    
    # Simple email validation
    if '@' not in email or '.' not in email:
        return jsonify({'success': False, 'message': 'Please enter a valid email address'})
    
    # Check if email is already registered
    try:
        conn = sqlite3.connect('custom_design.db')
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users WHERE email = ?', (email,))
        if cursor.fetchone()[0] > 0:
            conn.close()
            return jsonify({'success': False, 'message': 'Email is already registered'})
        conn.close()
    except:
        pass
    
    # Generate 6-digit OTP
    otp = str(random.randint(100000, 999999))
    
    # Store OTP with timestamp
    otp_storage[email] = {
        'otp': otp,
        'timestamp': time.time(),
        'verified': False,
        'attempts': 0
    }
    
    print(f"OTP for {email}: {otp}")  # Always print to console for testing
    
    # Try to send email in background thread
    try:
        if EMAIL_CONFIG['sender_email'] and EMAIL_CONFIG['sender_password']:
            # Start email sending in background thread
            email_thread = threading.Thread(
                target=send_otp_email_async,
                args=(email, otp)
            )
            email_thread.daemon = True
            email_thread.start()
            return jsonify({'success': True, 'message': 'OTP sent successfully!'})
        else:
            # Email not configured, show OTP in console
            return jsonify({
                'success': True, 
                'message': f'OTP sent! (For testing: {otp})'
            })
    except Exception as e:
        print(f"Error sending email: {e}")
        return jsonify({
            'success': True, 
            'message': f'OTP generated! (For testing: {otp})'
        })

@app.route('/profile/send-email-otp', methods=['POST'])
@login_required
def send_profile_email_otp():
    """Send OTP for profile email change - allows email if it's the current user's email"""
    data = request.json
    email = data.get('email')
    
    if not email:
        return jsonify({'success': False, 'message': 'Email is required'})
    
    # Simple email validation
    if '@' not in email or '.' not in email:
        return jsonify({'success': False, 'message': 'Please enter a valid email address'})
    
    # Check if email is already registered by another user
    try:
        conn = sqlite3.connect('custom_design.db')
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users WHERE email = ?', (email,))
        existing_user = cursor.fetchone()
        conn.close()
        
        if existing_user and existing_user[0] != session.get('user_id'):
            return jsonify({'success': False, 'message': 'Email is already registered by another user'})
    except:
        pass
    
    # Generate 6-digit OTP
    otp = str(random.randint(100000, 999999))
    
    # Store OTP with timestamp
    otp_storage[email.lower()] = {
        'otp': otp,
        'timestamp': time.time(),
        'verified': False,
        'attempts': 0
    }
    
    print(f"OTP for profile email change {email}: {otp}")  # Always print to console for testing
    
    # Try to send email in background thread
    try:
        if EMAIL_CONFIG['sender_email'] and EMAIL_CONFIG['sender_password']:
            # Start email sending in background thread
            email_thread = threading.Thread(
                target=send_otp_email_async,
                args=(email, otp)
            )
            email_thread.daemon = True
            email_thread.start()
            return jsonify({'success': True, 'message': 'OTP sent successfully!'})
        else:
            # Email not configured, show OTP in console
            return jsonify({
                'success': True, 
                'message': f'OTP sent! (For testing: {otp})'
            })
    except Exception as e:
        print(f"Error sending email: {e}")
        return jsonify({
            'success': True, 
            'message': f'OTP generated! (For testing: {otp})'
        })

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('home'))
    
    form = RegistrationForm()
    
    if form.validate_on_submit():
        print(f"DEBUG: Form submitted for email: {form.email.data}")
        print(f"DEBUG: OTP entered: {form.email_otp.data}")
        print(f"DEBUG: OTP storage keys: {list(otp_storage.keys())}")
        # Verify OTP
        email = form.email.data
        user_otp = form.email_otp.data
        
        # Check if OTP was requested for this email
        if email not in otp_storage:
            flash('Please request an OTP first.', 'danger')
            return render_template('register.html', form=form)
        
        stored_data = otp_storage[email]
        
        # Check if OTP is expired (10 minutes)
        if time.time() - stored_data['timestamp'] > 600:
            flash('OTP has expired. Please request a new one.', 'danger')
            # Remove expired OTP
            del otp_storage[email]
            return render_template('register.html', form=form)
        
        # Check OTP attempts
        if stored_data.get('attempts', 0) >= 3:
            flash('Too many OTP attempts. Please request a new OTP.', 'danger')
            del otp_storage[email]
            return render_template('register.html', form=form)
        
        # Verify OTP (only if not already verified)
        if not stored_data.get('verified', False):
            if stored_data['otp'] != user_otp:
                stored_data['attempts'] = stored_data.get('attempts', 0) + 1
                flash(f'Invalid OTP. {3 - stored_data["attempts"]} attempts remaining.', 'danger')
                return render_template('register.html', form=form)
            
            # Mark OTP as verified
            stored_data['verified'] = True
        
        # If we reach here, OTP is correct and verified
        try:
            # Format date of birth
            date_of_birth = None
            if form.date_of_birth.data:
                date_of_birth = form.date_of_birth.data.strftime('%Y-%m-%d')
            
            user_id = db_helper.insert_user(
                username=form.username.data,
                email=form.email.data,
                password=form.password.data,
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                date_of_birth=date_of_birth,
                phone=form.phone.data,
            
                role='customer'
            )
            
            session['user_id'] = user_id
            session['username'] = form.username.data
            session['role'] = 'customer'
            session['session_id'] = str(uuid.uuid4())
            
            flash(f'Welcome {form.first_name.data}! Registration successful.', 'success')
            
            # Clear OTP after successful registration
            if email in otp_storage:
                del otp_storage[email]
            
            return redirect(url_for('profile'))
            
        except ValueError as e:
            # This catches "Username already exists" or "Email already exists"
            flash(str(e), 'danger')
        except Exception as e:
            flash(f'An error occurred during registration: {str(e)}', 'danger')
    
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('home'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        user_data = db_helper.authenticate_user(form.username.data, form.password.data)
        
        if user_data:
            user_id = user_data[0]
            session['user_id'] = user_id
            session['username'] = user_data[1] if len(user_data) > 1 else form.username.data
            session['role'] = user_data[8] if len(user_data) > 8 else 'customer'
            
            # Optional: Clear old cart items on login (uncomment if you want fresh cart on each login)
            # conn = sqlite3.connect('custom_design.db')
            # cursor = conn.cursor()
            # cursor.execute('DELETE FROM cart_items WHERE user_id = ?', (user_id,))
            # conn.commit()
            # conn.close()
            session['username'] = user_data[1]
            session['role'] = user_data[6]
            session['session_id'] = str(uuid.uuid4())
            
            # Handle Remember Me functionality
            if form.remember_me.data:
                session.permanent = True
                app.permanent_session_lifetime = 2592000  # 30 days
            else:
                session.permanent = False
            
            db_helper.create_session(
                session_id=session['session_id'],
                user_id=user_data[0],
                ip_address=request.remote_addr
            )
            
            flash(f'Welcome back, {user_data[1]}!', 'success')
            
            if user_data[6] == 'admin':
                return redirect(url_for('admin.dashboard'))
            else:
                return redirect(url_for('profile'))
        else:
            flash('Invalid username or password.', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    if 'session_id' in session:
        db_helper.delete_session(session['session_id'])
    
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/profile')
@login_required
def profile():
    if session.get('role') == 'admin':
        return redirect(url_for('admin.dashboard'))
    
    user_data = db_helper.get_user_by_id(session['user_id'])
    
    if not user_data:
        flash('User not found. Please login again.', 'danger')
        session.clear()
        return redirect(url_for('login'))
    
    sessions = db_helper.get_user_sessions(session['user_id'])

    # Fetch user's orders for My Purchases section
    orders = []
    try:
        conn = sqlite3.connect('custom_design.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT order_id, full_name, total, shipping_address, created_at, status
            FROM orders
            WHERE user_id = ?
            ORDER BY created_at DESC
        ''', (session['user_id'],))
        orders = cursor.fetchall()
        conn.close()
    except sqlite3.OperationalError:
        pass

    return render_template('profile.html', 
                          user_data=user_data, 
                          user=user_data,
                          sessions=sessions, 
                          session_id=session.get('session_id'),
                          orders=orders)

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    user_data = db_helper.get_user_by_id(session['user_id'])
    if not user_data:
        flash('User not found.', 'danger')
        return redirect(url_for('profile'))
    
    form = ProfileForm()
    original_email = user_data[2]  # Store original email for comparison
    
    if request.method == 'GET':
        form.username.data = user_data[1]  # username is at index 1
        form.first_name.data = user_data[3]
        form.last_name.data = user_data[4]
        form.email.data = user_data[2]
        if user_data[5]:  # date_of_birth
            try:
                form.date_of_birth.data = datetime.strptime(user_data[5], '%Y-%m-%d')
            except ValueError:
                form.date_of_birth.data = None
        form.phone.data = user_data[6] if user_data[6] else ''
        form.address.data = user_data[7] if user_data[7] else ''
    
    if form.validate_on_submit():
        # Check if email changed
        email_changed = form.email.data.lower() != original_email.lower()
        
        # If email changed, verify OTP
        if email_changed:
            if not form.email_otp.data or not form.email_otp.data.strip():
                flash('Please verify your new email address with the OTP code sent to your email.', 'danger')
                return render_template('edit_profile.html', form=form, user_data=user_data, email_changed=True, original_email=original_email)
            
            # Verify OTP
            email = form.email.data.lower()
            if email not in otp_storage:
                flash('Please request an OTP first by clicking "Send OTP" button.', 'danger')
                return render_template('edit_profile.html', form=form, user_data=user_data, email_changed=True, original_email=original_email)
            
            stored_data = otp_storage[email]
            
            # Check if OTP is expired (10 minutes)
            if time.time() - stored_data['timestamp'] > 600:
                flash('OTP has expired. Please request a new one.', 'danger')
                del otp_storage[email]
                return render_template('edit_profile.html', form=form, user_data=user_data, email_changed=True, original_email=original_email)
            
            # Check OTP attempts
            if stored_data['attempts'] >= 3:
                flash('Too many OTP attempts. Please request a new OTP.', 'danger')
                del otp_storage[email]
                return render_template('edit_profile.html', form=form, user_data=user_data, email_changed=True, original_email=original_email)
            
            # Verify OTP
            if stored_data['otp'] != form.email_otp.data:
                stored_data['attempts'] += 1
                flash(f'Invalid OTP. {3 - stored_data["attempts"]} attempts remaining.', 'danger')
                return render_template('edit_profile.html', form=form, user_data=user_data, email_changed=True, original_email=original_email)
            
            # OTP verified - mark as verified
            stored_data['verified'] = True
            # Clear OTP after successful verification
            del otp_storage[email]
        
        # Format date of birth
        date_of_birth = None
        if form.date_of_birth.data:
            date_of_birth = form.date_of_birth.data.strftime('%Y-%m-%d')
        
        # Clean phone number - remove non-numeric characters except +, -, spaces, parentheses
        phone_cleaned = form.phone.data.strip() if form.phone.data else ''
        
        # Update user profile
        success = db_helper.update_user(
            user_id=user_data[0],
            username=form.username.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data,
            date_of_birth=date_of_birth,
            phone=phone_cleaned,
            address=form.address.data
        )
        
        if success:
            # Update session username if username changed
            if form.username.data != user_data[1]:
                session['username'] = form.username.data
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('profile'))
        else:
            flash('Failed to update profile. Username or email may already be taken.', 'danger')
    
    return render_template('edit_profile.html', form=form, user_data=user_data, email_changed=False, original_email=original_email)

@app.route('/profile/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    from Forms import ChangePasswordForm
    form = ChangePasswordForm()
    
    if form.validate_on_submit():
        # Get the user's current password hash from database
        user_data = db_helper.get_user_by_id(session['user_id'])
        if not user_data:
            flash('User not found. Please login again.', 'danger')
            session.clear()
            return redirect(url_for('login'))
        
        # Get the stored password hash
        stored_hash = db_helper.get_password_hash(session['user_id'])
        if not stored_hash:
            flash('Unable to retrieve user data. Please try again.', 'danger')
            return redirect(url_for('profile'))
        
        # Verify current password
        if db_helper.verify_password(stored_hash, form.current_password.data):
            # Update to new password
            success = db_helper.update_password(session['user_id'], form.new_password.data)
            if success:
                flash('Password changed successfully!', 'success')
                return redirect(url_for('profile'))
            else:
                flash('Failed to update password. Please try again.', 'danger')
        else:
            flash('Current password is incorrect.', 'danger')
    
    return render_template('change_password.html', form=form)

@app.route('/session/terminate/<session_id>', methods=['POST'])
@login_required
def terminate_session(session_id):
    if session_id == session.get('session_id'):
        flash('You cannot terminate your current session.', 'warning')
        return redirect(url_for('profile'))
    
    db_helper.delete_session(session_id)
    flash('Session terminated successfully.', 'success')
    return redirect(url_for('profile'))

# Account deletion route
@app.route('/account/delete', methods=['POST'])
@login_required
def delete_account():
    user_id = session['user_id']
    
    # First delete user sessions
    db_helper.delete_user_sessions(user_id)
    
    # Then delete the user
    success = db_helper.delete_user(user_id)
    
    if success:
        session.clear()
        flash('Your account has been permanently deleted.', 'info')
        return redirect(url_for('home'))
    else:
        flash('Failed to delete account. Please try again.', 'danger')
        return redirect(url_for('profile'))

# ===================== THYLIS'S,251684J,group 4 =====================


# Quick View API endpoint for products - Thylis, 251684J, group 4
@app.route('/products/<int:product_id>/quick-view')
def product_quick_view(product_id):
    product = db_helper.get_product_by_id(product_id)
    if not product:
        return '<div class="alert alert-danger">Product not found</div>'
    
    return f'''
    <div class="row">
        <div class="col-md-6">
            <div class="product-image" style="height: 300px;">
                {f'<img src="{url_for("static", filename=product[8])}" alt="{product[1]}" style="width: 100%; height: 100%; object-fit: contain;">' if product[8] else f'<i class="fas fa-box fa-5x" style="color: var(--sage-green);"></i>'}
            </div>
        </div>
        <div class="col-md-6">
            <h5>{product[1]}</h5>
            <div class="product-price mb-3">
                <span class="current-price">${"{:.2f}".format(product[4])}</span>
            </div>
            <p class="text-muted">{product[2][:100]}...</p>
            
            <div class="product-meta mb-3">
                <div class="meta-item">
                    <span>Category:</span>
                    <span>{product[3]}</span>
                </div>
                <div class="meta-item">
                    <span>Stock:</span>
                    <span class="{'text-success' if product[5] > 10 else 'text-warning' if product[5] > 0 else 'text-danger'}">
                        {product[5]} units
                    </span>
                </div>
            </div>
            
            <div class="d-grid gap-2">
                <a href="{url_for('products.product_detail', product_id=product[0])}" class="btn btn-primary">
                    <i class="fas fa-eye me-2"></i> View Details
                </a>
                <form action="{url_for('add_to_cart', product_id=product[0])}" method="POST" style="display: inline;">
                    <button type="submit" class="btn btn-outline-primary">
                        <i class="fas fa-shopping-cart me-2"></i> Add to Cart
                    </button>
                </form>
            </div>
        </div>
    </div>
    '''

# Compare products functionality - Thylis, 251684J, group 4
@app.route('/api/compare/add/<int:product_id>', methods=['POST'])
def add_to_compare(product_id):
    # Initialize compare list in session if not exists
    if 'compare_list' not in session:
        session['compare_list'] = []
    
    # Add product to compare list (max 4 products)
    if product_id not in session['compare_list']:
        if len(session['compare_list']) >= 4:
            session['compare_list'].pop(0)
        session['compare_list'].append(product_id)
        session.modified = True
    
    return jsonify({'success': True, 'count': len(session['compare_list'])})

# ===================== YONG JUN'S PART - FAQ & CONTACT =====================
# FAQ page route
@app.route('/faq')
def faq():
    # Sample FAQ data
    faq_categories = [
        {'id': 'orders', 'name': 'Orders', 'icon': 'fas fa-shopping-bag'},
        {'id': 'shipping', 'name': 'Shipping', 'icon': 'fas fa-shipping-fast'},
        {'id': 'returns', 'name': 'Returns', 'icon': 'fas fa-undo'},
        {'id': 'payments', 'name': 'Payments', 'icon': 'fas fa-credit-card'},
        {'id': 'sizing', 'name': 'Sizing', 'icon': 'fas fa-ruler'},
        {'id': 'customisation', 'name': 'Customisation', 'icon': 'fas fa-paint-brush'},
        {'id': 'account', 'name': 'Account', 'icon': 'fas fa-user'}
    ]
    
    hot_faqs = [
        {'id': 1, 'question': 'Where is my order?', 'answer': 'You can track your order by logging into your account and visiting the "My Orders" section. Orders typically take 5-7 business days to process and ship.', 'category': 'orders', 'helpful': 95, 'views': 1250},
        {'id': 2, 'question': 'How long does shipping take?', 'answer': 'Standard shipping takes 5-7 business days. Express shipping is available and delivers within 2-3 business days. International shipping takes 7-14 business days.', 'category': 'shipping', 'helpful': 92, 'views': 980},
        {'id': 3, 'question': 'How do I return an item?', 'answer': 'You can initiate a return within 30 days of delivery. Log into your account, go to "My Orders", select the item, and click "Return Item". We\'ll provide a prepaid return label.', 'category': 'returns', 'helpful': 88, 'views': 750},
        {'id': 4, 'question': 'How to upload designs?', 'answer': 'You can upload designs in JPG, PNG, PDF, or AI format (max 50MB). Use our design tool to position your design, adjust colors, and preview before ordering.', 'category': 'customisation', 'helpful': 96, 'views': 1100},
        {'id': 5, 'question': 'How to read the size guide?', 'answer': 'Our size guide includes detailed measurements. Measure yourself using a soft tape measure and compare with our size chart. For custom fits, we recommend adding 2-3 inches to body measurements.', 'category': 'sizing', 'helpful': 90, 'views': 850},
        {'id': 6, 'question': 'Can I change my order?', 'answer': 'You can modify your order within 2 hours of placement. After that, changes may not be possible as production begins. Contact our support team immediately if you need changes.', 'category': 'orders', 'helpful': 85, 'views': 650}
    ]
    
    all_faqs = [
        # Orders FAQs
        {'id': 101, 'question': 'What is your order cancellation policy?', 'answer': 'You can cancel your order within 2 hours of placement free of charge. After 2 hours, a cancellation fee may apply if production has started.', 'category': 'orders'},
        {'id': 102, 'question': 'Do you offer bulk discounts?', 'answer': 'Yes, we offer volume discounts for orders of 50+ units. Contact our sales team at bulk@designcraftstudio.com for a custom quote.', 'category': 'orders'},
        
        # Shipping FAQs
        {'id': 201, 'question': 'Do you ship internationally?', 'answer': 'Yes, we ship to over 50 countries worldwide. International shipping takes 7-14 business days and may be subject to customs fees.', 'category': 'shipping'},
        {'id': 202, 'question': 'How can I track my order?', 'answer': 'Once your order ships, you\'ll receive a tracking number via email. You can also track it in your account under "My Orders".', 'category': 'shipping'},
        
        # Returns FAQs
        {'id': 301, 'question': 'What is your return window?', 'answer': 'We accept returns within 30 days of delivery for unworn, unwashed items with original tags attached. Customized items cannot be returned unless defective.', 'category': 'returns'},
        {'id': 302, 'question': 'Who pays for return shipping?', 'answer': 'We provide prepaid return labels for defective or incorrect items. For other returns, return shipping is the customer\'s responsibility.', 'category': 'returns'},
        
        # Customization FAQs
        {'id': 401, 'question': 'How to request monogram?', 'answer': 'Select the "Add Monogram" option in the design tool. Choose font, thread color, and position. Preview your design before finalizing.', 'category': 'customisation'},
        {'id': 402, 'question': 'What file formats do you accept?', 'answer': 'We accept JPG, PNG, PDF, AI, EPS, and SVG files. For best quality, vector files (AI, EPS, SVG) are recommended.', 'category': 'customisation'},
        
        # Sizing FAQs
        {'id': 501, 'question': 'How do I measure chest size?', 'answer': 'Measure around the fullest part of your chest, under your arms and over your shoulder blades. Keep the tape measure horizontal.', 'category': 'sizing'},
        {'id': 502, 'question': 'Do your sizes run true to size?', 'answer': 'Our sizes follow standard sizing charts. We recommend checking our size guide and measuring yourself for the best fit.', 'category': 'sizing'},
        
        # Account FAQs
        {'id': 601, 'question': 'How do I reset my password?', 'answer': 'Click "Forgot Password" on the login page. Enter your email and follow the instructions sent to your inbox.', 'category': 'account'},
        {'id': 602, 'question': 'Can I change my email address?', 'answer': 'Yes, you can update your email in your account settings under "Personal Information".', 'category': 'account'}
    ]
    
    return render_template('faq.html', 
                         categories=faq_categories,
                         hot_faqs=hot_faqs,
                         all_faqs=all_faqs)

# Contact Us route
@app.route('/contact', methods=['GET', 'POST'])
def contact_us():
    form = ContactForm()
    
    # Pre-fill if user is logged in
    if 'user_id' in session:
        user_data = db_helper.get_user_by_id(session['user_id'])
        if user_data:
            form.name.data = f"{user_data[3]} {user_data[4]}"
            form.email.data = user_data[2]
    
    if form.validate_on_submit():
        # Generate ticket ID
        ticket_id = f"DC-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
        
        # In production, save to database
        flash(f'Ticket #{ticket_id} created successfully! We\'ll respond within 24 hours.', 'success')
        return redirect(url_for('contact_us'))
    
    # Suggested articles based on common issues
    suggested_articles = [
        {'title': 'How to track your order', 'category': 'orders'},
        {'title': 'Return policy and instructions', 'category': 'returns'},
        {'title': 'Size guide and measurements', 'category': 'sizing'},
        {'title': 'Custom design upload guide', 'category': 'customisation'}
    ]
    
    return render_template('contact.html', 
                         form=form,
                         suggested_articles=suggested_articles)

# API endpoint for FAQ helpfulness
@app.route('/api/faq/helpful', methods=['POST'])
@csrf.exempt
def faq_helpful():
    data = request.json
    faq_id = data.get('faq_id')
    helpful = data.get('helpful')  # True or False
    
    # In production: Update database with feedback
    print(f"FAQ {faq_id} marked as {'helpful' if helpful else 'not helpful'}")
    
    return jsonify({'success': True})

# ===================== SHARED FUNCTIONALITY =====================
# Health check route
@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

# ===================== INVOICE DATABASE ISHAANI 252956P =====================
@app.route('/invoices')
@login_required
def invoices():
    """Invoice database page: see who bought what (admin/manager only)."""
    if session.get('role') not in ['admin', 'manager']:
        flash('Access denied. Admin or Manager privileges required.', 'danger')
        return redirect(url_for('home'))
    orders = db_helper.get_all_orders_with_items()
    return render_template('invoices.html', orders=orders)


# ===================== MANAGER DASHBOARD ROUTES =====================
@app.route('/manager')
@login_required
def manager_dashboard():
    """Manager dashboard for product management"""
    # Check if user is manager or admin
    if session.get('role') not in ['admin', 'manager']:
        flash('Access denied. Manager privileges required.', 'danger')
        return redirect(url_for('home'))
    
    # Get manager info
    user_data = db_helper.get_user_by_id(session['user_id'])
    
    # Get product stats
    conn = sqlite3.connect('custom_design.db')
    cursor = conn.cursor()
    
    # Total products
    cursor.execute('SELECT COUNT(*) FROM products')
    total_products = cursor.fetchone()[0]
    
    # Total categories
    cursor.execute('SELECT COUNT(DISTINCT category) FROM products')
    total_categories = cursor.fetchone()[0]
    
    # Get all products for the table
    cursor.execute('SELECT * FROM products ORDER BY created_at DESC')
    products = cursor.fetchall()
    
    conn.close()
    
    return render_template('manager.html', 
                         user_data=user_data,
                         total_products=total_products,
                         total_categories=total_categories,
                         products=products)

#===================== MANAGER DASHBOARD THYLIS 251684J =====================
# API endpoint for manager to add products
@app.route('/api/manager/products', methods=['POST'])
@login_required
@csrf.exempt
def manager_add_product():
    """Add new product (manager only)"""
    if session.get('role') not in ['admin', 'manager']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['name', 'description', 'category', 'price', 'stock']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'success': False, 'message': f'{field} is required'}), 400
        
        # Add product to database
        product_id = db_helper.create_product(
            name=data['name'],
            description=data['description'],
            category=data['category'],
            price=float(data['price']),
            stock=int(data['stock']),
            colors=data.get('colors', ['White']),
            sizes=data.get('sizes', ['M']),
            image_url=data.get('image_url'),
            created_by=session['user_id']
        )
        
        return jsonify({
            'success': True, 
            'message': 'Product added successfully',
            'product_id': product_id
        })
        
    except Exception as e:
        print(f"Error adding product: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    
# API endpoint for manager to update products
@app.route('/api/manager/products/<int:product_id>', methods=['PUT'])
@login_required
@csrf.exempt
def manager_update_product(product_id):
    """Update product (manager only)"""
    if session.get('role') not in ['admin', 'manager']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        data = request.json
        
        # Handle colors - convert string to list if needed
        colors = data.get('colors', ['white'])
        if isinstance(colors, str):
            colors = [c.strip() for c in colors.split(',')]
        
        # Handle sizes - convert string to list if needed
        sizes = data.get('sizes', ['M'])
        if isinstance(sizes, str):
            sizes = [s.strip() for s in sizes.split(',')]
        
        # Update product in database
        success = db_helper.update_product(
            product_id=product_id,
            name=data['name'],
            description=data['description'],
            category=data['category'],
            price=float(data['price']),
            stock=int(data['stock']),
            colors=colors,
            sizes=sizes,
            image_url=data.get('image_url'),
            is_active=data.get('is_active', True)
        )
        
        if success:
            return jsonify({
                'success': True, 
                'message': 'Product updated successfully'
            })
        else:
            return jsonify({'success': False, 'message': 'Product not found'}), 404
        
    except Exception as e:
        print(f"Error updating product: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# API endpoint for manager to delete products
@app.route('/api/manager/products/<int:product_id>', methods=['DELETE'])
@login_required
@csrf.exempt
def manager_delete_product(product_id):
    """Delete product (manager only)"""
    if session.get('role') not in ['admin', 'manager']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        # Delete product from database
        success = db_helper.delete_product(product_id)
        
        if success:
            return jsonify({
                'success': True, 
                'message': 'Product deleted successfully'
            })
        else:
            return jsonify({'success': False, 'message': 'Product not found'}), 404
        
    except Exception as e:
        print(f"Error deleting product: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# API endpoint to get all products for manager
@app.route('/api/manager/products')
@login_required
def manager_get_products():
    """Get all products for manager dashboard"""
    if session.get('role') not in ['admin', 'manager']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        print("DEBUG: Fetching all products...")
        # Get all products from database
        products = db_helper.get_all_products()
        print(f"DEBUG: Got {len(products)} products")
        
        # Format products for JSON response
        formatted_products = []
        for product in products:
            formatted_products.append({
                'id': product[0],
                'name': product[1],
                'description': product[2],
                'category': product[3],
                'price': product[4],
                'stock': product[5],
                'colors': product[6].split(',') if product[6] else [],
                'sizes': product[7].split(',') if product[7] else [],
                'image_url': product[8],
                'is_active': bool(product[10]),
                'created_at': product[11]
            })
        
        return jsonify({
            'success': True,
            'products': formatted_products
        })
        
    except Exception as e:
        print(f"Error getting products: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    
# Add this route to app.py
@app.route('/api/products')
def get_products_api():
    """Get all products for customer display"""
    try:
        # Get all active products from database
        products = db_helper.get_all_products()
        
        # Format products for JSON response
        formatted_products = []
        for product in products:
            # Only include active products
            if product[10]:  # is_active field
                formatted_products.append({
                    'id': product[0],
                    'name': product[1],
                    'description': product[2],
                    'category': product[3],
                    'price': product[4],
                    'stock': product[5],
                    'colors': product[6].split(',') if product[6] else [],
                    'sizes': product[7].split(',') if product[7] else [],
                    'image_url': product[8],
                    'is_active': bool(product[10]),
                    'created_at': product[11]
                })
        
        return jsonify({
            'success': True,
            'products': formatted_products
        })
        
    except Exception as e:
        print(f"Error getting products: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
# ===================== CREATE MANAGER USER =====================
def create_manager_user():
    """Create a manager user if it doesn't exist"""
    try:
        # Import password hashing
        from werkzeug.security import generate_password_hash
        
        conn = sqlite3.connect('custom_design.db')
        cursor = conn.cursor()
        
        # Check if manager user exists
        cursor.execute('SELECT * FROM users WHERE username = ? OR email = ?', 
                      ('manager', 'manager@designcraft.com'))
        if not cursor.fetchone():
            # Create manager user with hashed password
            hashed_password = generate_password_hash('manager123')
            
            cursor.execute('''
                INSERT INTO users 
                (username, email, password, first_name, last_name, role, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', ('manager', 'manager@designcraft.com', hashed_password, 
                  'Manager', 'User', 'manager', datetime.now()))
            
            conn.commit()
            print("✅ Manager user created successfully!")
            print("   Username: manager")
            print("   Password: manager123")
            print("   Role: manager")
        else:
            print("ℹ️ Manager user already exists")
        
        conn.close()
    except Exception as e:
        print(f"❌ Error creating manager user: {e}")

# ===================== SHARED FUNCTIONALITY =====================
# Call this function when starting the app
create_manager_user()

def init_database():
    """Initialize/Update database tables"""
    try:
        conn = sqlite3.connect('custom_design.db')
        cursor = conn.cursor()
        
        # Check if cart_items table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cart_items'")
        if cursor.fetchone():
            # Get existing columns
            cursor.execute("PRAGMA table_info(cart_items)")
            columns = [column[1] for column in cursor.fetchall()]
            print(f"Cart items columns: {columns}")
            
            # Add missing columns
            if 'size' not in columns:
                cursor.execute("ALTER TABLE cart_items ADD COLUMN size TEXT DEFAULT 'M'")
                print("Added size column to cart_items")
            
            if 'color' not in columns:
                cursor.execute("ALTER TABLE cart_items ADD COLUMN color TEXT DEFAULT 'White'")
                print("Added color column to cart_items")
            
            if 'design_data' not in columns:
                cursor.execute("ALTER TABLE cart_items ADD COLUMN design_data TEXT")
                print("Added design_data column to cart_items")
            
            conn.commit()
            print("✅ Database schema updated")
        
        conn.close()
    except Exception as e:
        print(f"Database update error: {e}")

if __name__ == '__main__':
    init_database()
    # Ensure upload directories exist
    os.makedirs('static/uploads/products', exist_ok=True)
    os.makedirs('static/uploads/profile', exist_ok=True)
    
    # Ensure cart_items table exists
    conn = sqlite3.connect('custom_design.db')
    cursor = conn.cursor()
    
    # Create cart_items table if not exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cart_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER DEFAULT 1,
            size TEXT,
            color TEXT,
            design_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            FOREIGN KEY (product_id) REFERENCES products (product_id)
        )
    ''')
    
    # Add columns if they don't exist (for existing tables)
    try:
        cursor.execute('ALTER TABLE cart_items ADD COLUMN size TEXT')
    except sqlite3.OperationalError:
        pass  # Column already exists
    try:
        cursor.execute('ALTER TABLE cart_items ADD COLUMN color TEXT')
    except sqlite3.OperationalError:
        pass  # Column already exists
    try:
        cursor.execute('ALTER TABLE cart_items ADD COLUMN design_data TEXT')
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    conn.commit()

    # Create order_items table - recreate if it has product_id (old schema)
    try:
        cursor.execute('PRAGMA table_info(order_items)')
        cols = [r[1] for r in cursor.fetchall()]
        if cols and 'product_id' in cols:
            cursor.execute('DROP TABLE order_items')
    except sqlite3.OperationalError:
        pass  # Table may not exist yet
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            price REAL NOT NULL,
            quantity INTEGER NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(order_id)
        )
    ''')

    conn.commit()
    conn.close()
    
    # Ensure at least one product exists so "Customize" / "Start Creating" work
    def ensure_default_product():
        products = db_helper.get_all_products()
        if not products:
            try:
                db_helper.create_product(
                    name='Classic Cotton T-Shirt',
                    description='Premium 100% cotton t-shirt, soft and comfortable. Perfect for everyday wear and custom designs.',
                    category='t-shirts',
                    price=24.99,
                    stock=100,
                    colors=['White', 'Black', 'Navy', 'Gray'],
                    sizes=['S', 'M', 'L', 'XL', 'XXL'],
                    image_url=None,
                    created_by=None,
                    is_active=True
                )
                print("  Created default product so Customize page works.")
            except Exception as e:
                print(f"  Could not create default product: {e}")
    ensure_default_product()
    
    print("=" * 50)
    print("DesignCraft Studio - All Navigation Fixed")
    print("=" * 50)
    print("Available routes:")
    print("  Home: /")
    print("  Products: /products/")
    print("  Cart: /cart (accessible without login)")
    print("  Login: /login")
    print("  Register: /register")
    print("  FAQ: /faq")
    print("  Contact: /contact")
    print("  Manager: /manager (for managers only)")
    print("=" * 50)
    
    app.run(debug=True, port=5000)