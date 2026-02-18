# Yong jun , 252176E, group4 
# Thylis, 251684J, group4
# Ishaani, 252956P, group4
import sqlite3
import hashlib
import os
import time

class DatabaseHelper:
    def __init__(self, db_name='custom_design.db'):
        self.db_name = db_name
        self.init_database()

    def init_database(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        # ================= USERS TABLE =================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash BLOB NOT NULL,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                date_of_birth TEXT,
                phone TEXT,
                address TEXT,
                role TEXT DEFAULT 'customer',
                profile_image TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        ''')

        # ================= SESSIONS TABLE =================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_sessions (
                session_id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address TEXT,
                user_agent TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')

        # ================= PRODUCTS TABLE =================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                product_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                category TEXT NOT NULL,
                price REAL NOT NULL,
                stock INTEGER DEFAULT 0,
                colors TEXT,
                sizes TEXT,
                image_url TEXT,
                created_by INTEGER,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES users(user_id)
            )
        ''')

        # ================= CREATE DEFAULT ADMIN =================
        cursor.execute('SELECT COUNT(*) FROM users WHERE username = "admin"')
        if cursor.fetchone()[0] == 0:
            admin_password = self.hash_password('Admin@123')
            cursor.execute('''
                INSERT INTO users (username, email, password_hash, first_name, last_name, role)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', ('admin', 'admin@customdesign.com', admin_password, 'System', 'Administrator', 'admin'))

        # ================= CREATE DEFAULT MANAGER =================
        # Thylis, 251684J, group 4 - Add default manager user
        cursor.execute('SELECT COUNT(*) FROM users WHERE username = "manager"')
        if cursor.fetchone()[0] == 0:
            manager_password = self.hash_password('Manager@123')
            cursor.execute('''
                INSERT INTO users (username, email, password_hash, first_name, last_name, role)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', ('manager', 'manager@customdesign.com', manager_password, 'Manager', 'Manager', 'manager'))

        # ================= ORDERS TABLE =================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                full_name TEXT,
                card_last_four TEXT,
                delivery_option TEXT,
                shipping_address TEXT,
                total REAL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
            )
        ''')

        # ================= ORDER ITEMS TABLE =================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                product_name TEXT,
                price REAL,
                quantity INTEGER,
                FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE
            )
        ''')

        # ================= AUDIT LOG TABLE =================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER NOT NULL,
                action_type TEXT NOT NULL,
                target_id INTEGER,
                target_type TEXT,
                details TEXT,
                ip_address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (admin_id) REFERENCES users(user_id)
            )
        ''')

        conn.commit()
        conn.close()

    # ================= PASSWORD HELPERS =================
    @staticmethod
    def hash_password(password):
        salt = os.urandom(32)
        key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        return salt + key

    @staticmethod
    def verify_password(stored_password, provided_password):
        salt = stored_password[:32]
        stored_key = stored_password[32:]
        key = hashlib.pbkdf2_hmac('sha256', provided_password.encode(), salt, 100000)
        return key == stored_key

    # ================= USER METHODS =================
    def insert_user(self, username, email, password, first_name, last_name,
                    date_of_birth=None, phone='', address='', role='customer'):
        password_hash = self.hash_password(password)
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO users (username, email, password_hash, first_name, last_name,
                                   date_of_birth, phone, address, role)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (username, email, password_hash, first_name, last_name,
                  date_of_birth, phone, address, role))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def authenticate_user(self, username, password):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id, username, email, password_hash, first_name, last_name, role
            FROM users WHERE username = ? OR email = ?
        ''', (username, username))
        user = cursor.fetchone()
        conn.close()
        if user and self.verify_password(user[3], password):
            return user
        return None

    def get_user_by_id(self, user_id):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id, username, email, first_name, last_name,
                   date_of_birth, phone, address, role, profile_image
            FROM users WHERE user_id = ?
        ''', (user_id,))
        user = cursor.fetchone()
        conn.close()
        return user

    def delete_user_sessions(self, user_id):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM user_sessions WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()

    def log_audit_action(self, admin_id, action_type, target_id=None, target_type=None, details=None, ip_address=None):
        """Log an admin action (e.g. delete user) for audit trail."""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO audit_log (admin_id, action_type, target_id, target_type, details, ip_address)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (admin_id, action_type, target_id, target_type, details, ip_address))
            conn.commit()
        except Exception:
            pass  # Don't fail the main action if logging fails
        finally:
            conn.close()

    # ================= SESSION METHODS =================
    # Thylis, 251684J, group 4 - Add missing session methods
    def create_session(self, session_id, user_id, ip_address, user_agent=None):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO user_sessions (session_id, user_id, ip_address, user_agent)
            VALUES (?, ?, ?, ?)
        ''', (session_id, user_id, ip_address, user_agent))
        conn.commit()
        conn.close()

    def get_user_sessions(self, user_id):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT session_id, login_time, last_activity, ip_address, user_agent
            FROM user_sessions WHERE user_id = ? ORDER BY last_activity DESC
        ''', (user_id,))
        sessions = cursor.fetchall()
        conn.close()
        return sessions

    def delete_session(self, session_id):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM user_sessions WHERE session_id = ?', (session_id,))
        conn.commit()
        conn.close()

    def update_user(self, user_id, username=None, first_name=None, last_name=None, email=None, date_of_birth=None, phone=None, address=None):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Build dynamic UPDATE query based on provided fields
        updates = []
        values = []
        
        if username is not None:
            # Check if username is already taken by another user
            cursor.execute('SELECT user_id FROM users WHERE username = ? AND user_id != ?', (username, user_id))
            if cursor.fetchone():
                conn.close()
                return False  # Username already taken
            updates.append('username = ?')
            values.append(username)
        
        if first_name is not None:
            updates.append('first_name = ?')
            values.append(first_name)
        if last_name is not None:
            updates.append('last_name = ?')
            values.append(last_name)
        if email is not None:
            # Check if email is already taken by another user
            cursor.execute('SELECT user_id FROM users WHERE email = ? AND user_id != ?', (email, user_id))
            if cursor.fetchone():
                conn.close()
                return False  # Email already taken
            updates.append('email = ?')
            values.append(email)
        if date_of_birth is not None:
            updates.append('date_of_birth = ?')
            values.append(date_of_birth)
        if phone is not None:
            updates.append('phone = ?')
            values.append(phone)
        if address is not None:
            updates.append('address = ?')
            values.append(address)
        
        if not updates:
            conn.close()
            return False  # No fields to update
        
        values.append(user_id)
        query = f'UPDATE users SET {", ".join(updates)} WHERE user_id = ?'
        cursor.execute(query, values)
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success

    def get_password_hash(self, user_id):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('SELECT password_hash FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None

    def update_password(self, user_id, new_password):
        password_hash = self.hash_password(new_password)
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET password_hash = ? WHERE user_id = ?', (password_hash, user_id))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success

    def delete_user(self, user_id):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success

    def get_all_users(self, exclude_admin=True):
        """Return list of users. Optionally exclude admins."""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        if exclude_admin:
            cursor.execute('''
                SELECT user_id, username, email, first_name, last_name,
                       phone, address, role, profile_image, created_at, last_login, is_active
                FROM users
                WHERE role != ?
                ORDER BY created_at DESC
            ''', ('admin',))
        else:
            cursor.execute('''
                SELECT user_id, username, email, first_name, last_name,
                       phone, address, role, profile_image, created_at, last_login, is_active
                FROM users
                ORDER BY created_at DESC
            ''')
        users = cursor.fetchall()
        conn.close()
        return users

    # ======================================================
    # === thylis, 251684J, group4 — PRODUCT METHODS  ===
    # ======================================================

    def create_product(self, name, description, category, price, stock, colors, sizes, 
                   image_url=None, created_by=None, is_active=True):  # ← Add is_active parameter
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO products (name, description, category, price, stock,
                                  colors, sizes, image_url, created_by, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''',    (name, description, category, price, stock,
          ','.join(colors), ','.join(sizes), image_url, created_by, int(is_active)))  # ← Add is_active value

        product_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return product_id

    def get_products(self, category=None, sort_by='newest', page=1, per_page=12):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        query = 'SELECT * FROM products WHERE is_active = 1'
        params = []

        if category:
            query += ' AND category = ?'
            params.append(category)

        sort_options = {
            'newest': 'created_at DESC',
            'price_low': 'price ASC',
            'price_high': 'price DESC',
            'name': 'name ASC'
        }

        query += f' ORDER BY {sort_options.get(sort_by, "created_at DESC")}'

        offset = (page - 1) * per_page
        query += ' LIMIT ? OFFSET ?'
        params.extend([per_page, offset])

        cursor.execute(query, params)
        products = cursor.fetchall()
        conn.close()
        return products

    def get_product_count(self, category=None):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        query = 'SELECT COUNT(*) FROM products WHERE is_active = 1'
        params = []
        
        if category:
            query += ' AND category = ?'
            params.append(category)
        
        cursor.execute(query, params)
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def get_product_categories(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT category FROM products WHERE is_active = 1 ORDER BY category')
        categories = [row[0] for row in cursor.fetchall()]
        conn.close()
        return categories

    def get_product_by_id(self, product_id):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM products WHERE product_id = ?', (product_id,))
        product = cursor.fetchone()
        conn.close()
        return product

    def get_related_products(self, product_id, category, limit=4):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM products 
            WHERE category = ? AND product_id != ? AND is_active = 1
            ORDER BY RANDOM()
            LIMIT ?
        ''', (category, product_id, limit))
        products = cursor.fetchall()
        conn.close()
        return products

    def get_product_reviews(self, product_id):
        # Returns empty list for now - you can implement reviews table later
        return []

    def get_product_average_rating(self, product_id):
        # Returns 0 for now - you can implement ratings later
        return 0

    def get_all_products(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT * FROM products ORDER BY created_at DESC')
            products = cursor.fetchall()
        except sqlite3.Error as e:
            print(f"SQLite error: {e}")
            products = []
        finally:
            conn.close()
        return products

    def update_product(self, product_id, name, description, category, price, stock, 
                      colors, sizes, image_url, is_active):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE products 
            SET name = ?, description = ?, category = ?, price = ?, stock = ?,
                colors = ?, sizes = ?, image_url = ?, is_active = ?, 
                updated_at = CURRENT_TIMESTAMP
            WHERE product_id = ?
        ''', (name, description, category, price, stock,
              ','.join(colors), ','.join(sizes), image_url, int(is_active), product_id))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success

    def delete_product(self, product_id):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM products WHERE product_id = ?', (product_id,))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success

    def toggle_product_status(self, product_id, is_active):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('UPDATE products SET is_active = ? WHERE product_id = ?', 
                      (int(is_active), product_id))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success

    def get_product_statistics(self, product_id):
        # Returns basic stats - you can expand this later
        return {
            'total_views': 0,
            'total_sales': 0,
            'total_reviews': 0,
            'avg_rating': 0
        }

    def add_product_review(self, product_id, user_id, rating, comment):
        # Placeholder - implement reviews table later
        return True

    def add_to_cart(self, user_id, product_id, quantity, size, color):
        # Placeholder - implement cart table later
        return True


    def search_products(self, query):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM products 
            WHERE (name LIKE ? OR description LIKE ?) AND is_active = 1
            LIMIT 10
        ''', (f'%{query}%', f'%{query}%'))
        products = cursor.fetchall()
        conn.close()
        return products
    
    # ================= INVOICE / ORDERS ISHAANI 252956P =================
    def get_all_orders_with_items(self):
        """Return all orders with their line items and customer info for invoice database."""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT o.order_id, o.user_id, o.full_name, o.shipping_address, o.total, o.status, o.created_at,
                   o.delivery_option, u.email, u.username
            FROM orders o
            LEFT JOIN users u ON o.user_id = u.user_id
            ORDER BY o.created_at DESC
        ''')
        order_rows = cursor.fetchall()
        orders = []
        for row in order_rows:
            order_id, user_id, full_name, shipping_address, total, status, created_at, delivery_option, email, username = row
            cursor.execute('''
                SELECT product_name, price, quantity FROM order_items WHERE order_id = ?
            ''', (order_id,))
            items = [{'product_name': r[0], 'price': float(r[1]), 'quantity': r[2]} for r in cursor.fetchall()]
            orders.append({
                'order_id': order_id,
                'user_id': user_id,
                'full_name': full_name or 'Guest',
                'email': email or '',
                'username': username or '',
                'shipping_address': shipping_address or '',
                'total': float(total) if total else 0,
                'status': status or 'pending',
                'created_at': created_at,
                'delivery_option': delivery_option or 'standard',
                'items': items
            })
        conn.close()
        return orders
    # ================= ORDER METHODS ISHAANI 252956P =================
    def get_all_orders(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT o.order_id, o.user_id, u.username, u.email, o.full_name,
                       o.total, o.status, o.created_at
                FROM orders o
                LEFT JOIN users u ON o.user_id = u.user_id
                ORDER BY o.created_at DESC
            ''')
            orders = cursor.fetchall()
        except sqlite3.Error as e:
            print(f"SQLite error fetching orders: {e}")
            orders = []
        finally:
            conn.close()
        return orders

    def get_order_by_id(self, order_id):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT o.order_id, o.user_id, u.username, u.email, o.full_name,
                   o.card_last_four, o.delivery_option, o.shipping_address,
                   o.total, o.status, o.created_at
            FROM orders o
            LEFT JOIN users u ON o.user_id = u.user_id
            WHERE o.order_id = ?
        ''', (order_id,))
        order = cursor.fetchone()
        conn.close()
        return order

    def get_order_items(self, order_id):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, product_name, price, quantity
            FROM order_items WHERE order_id = ?
        ''', (order_id,))
        items = cursor.fetchall()
        conn.close()
        return items

    def update_order_status(self, order_id, status):
        """Update the status of an order"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE orders SET status = ? WHERE order_id = ?
            ''', (status, order_id))
            conn.commit()
            success = cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"SQLite error updating order status: {e}")
            success = False
        finally:
            conn.close()
        return success
