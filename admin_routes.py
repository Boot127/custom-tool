#Yong jun,252176E,group4 
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from functools import wraps
from database import DatabaseHelper
from User import User
import uuid

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
db_helper = DatabaseHelper()

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('admin.admin_login'))
        if session.get('role') != 'admin':
            flash('Access denied. Admin privileges required.', 'danger')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/login', methods=['GET', 'POST'])
def admin_login():
    if 'user_id' in session and session.get('role') == 'admin':
        return redirect(url_for('admin.dashboard'))
    
    from Forms import LoginForm
    form = LoginForm(request.form)
    
    if request.method == 'POST' and form.validate():
        user_data = db_helper.authenticate_user(form.username.data, form.password.data)
        
        if user_data and user_data[6] == 'admin':
            session['user_id'] = user_data[0]
            session['username'] = user_data[1]
            session['role'] = user_data[6]
            session['session_id'] = str(uuid.uuid4())
            
            db_helper.create_session(
                session_id=session['session_id'],
                user_id=user_data[0],
                ip_address=request.remote_addr
            )
            
            flash(f'Welcome back, Admin {user_data[4]}!', 'success')
            return redirect(url_for('admin.dashboard'))
        else:
            flash('Invalid admin credentials.', 'danger')
    
    return render_template('admin_login.html', form=form)

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    all_users = db_helper.get_all_users(exclude_admin=False)
    customer_count = len([u for u in all_users if u[7] == 'customer'])
    admin_count = len([u for u in all_users if u[7] == 'admin'])
    
    users_list = [User.from_database_row(user) for user in all_users if user]
    
    return render_template('admin_dashboard.html',
                         users=users_list,
                         customer_count=customer_count,
                         admin_count=admin_count,
                         total_users=len(all_users))

@admin_bp.route('/users')
@admin_required
def admin_users():
    all_users = db_helper.get_all_users(exclude_admin=False)
    users_list = [User.from_database_row(user) for user in all_users if user]
    return render_template('admin_user.html', users_list=users_list)

@admin_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_user_status(user_id):
    if user_id == session.get('user_id'):
        flash('You cannot change your own status.', 'warning')
        return redirect(url_for('admin.admin_users'))
    
    success = db_helper.toggle_user_status(user_id)
    if success:
        flash('User status updated successfully.', 'success')
    else:
        flash('Failed to update user status.', 'danger')
    
    return redirect(url_for('admin.admin_users'))

@admin_bp.route('/users/<int:user_id>/details')
@admin_required
def user_details(user_id):
    user_data = db_helper.get_user_by_id(user_id)
    if not user_data:
        return jsonify({'error': 'User not found'}), 404
    
    user = User.from_database_row(user_data)
    sessions = db_helper.get_user_sessions(user_id)
    
    return jsonify({
        'success': True,
        'user': user.to_dict(),
        'sessions': [
            {
                'session_id': session[0],
                'login_time': session[1],
                'last_activity': session[2],
                'ip_address': session[3],
                'user_agent': session[4]
            }
            for session in sessions
        ]
    })

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    if user_id == session.get('user_id'):
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('admin.admin_users'))
    
    try:
        # Get user info before deletion
        user_data = db_helper.get_user_by_id(user_id)
        if not user_data:
            flash('User not found.', 'danger')
            return redirect(url_for('admin.admin_users'))
        
        username = user_data[1]
        fullname = f"{user_data[3]} {user_data[4]}"
        
        # Log the action
        db_helper.log_audit_action(
            admin_id=session['user_id'],
            action_type='DELETE_USER',
            target_id=user_id,
            target_type='user',
            details=f"Deleted user: {username} ({fullname})",
            ip_address=request.remote_addr
        )
        
        # First delete user sessions
        db_helper.delete_user_sessions(user_id)
        
        # Then delete the user
        success = db_helper.delete_user(user_id)
        
        if success:
            flash(f'User "{username}" has been permanently deleted.', 'success')
        else:
            flash('Failed to delete user.', 'danger')
    
    except Exception as e:
        flash(f'Error deleting user: {str(e)}', 'danger')
    
    return redirect(url_for('admin.admin_users'))

@admin_bp.route('/users/bulk-actions', methods=['POST'])
@admin_required
def bulk_actions():
    action = request.form.get('bulk_action')
    selected_users = request.form.getlist('selected_users')
    
    if not selected_users:
        flash('No users selected.', 'warning')
        return redirect(url_for('admin.admin_users'))
    
    try:
        success_count = 0
        total_count = len(selected_users)
        
        for user_id in selected_users:
            user_id = int(user_id)
            
            # Skip if trying to modify self
            if user_id == session.get('user_id'):
                continue
            
            if action == 'activate':
                success = db_helper.toggle_user_status(user_id)
                if db_helper.get_user_by_id(user_id)[11] == 1:  # Already active
                    success_count += 1
            elif action == 'deactivate':
                success = db_helper.toggle_user_status(user_id)
                if db_helper.get_user_by_id(user_id)[11] == 0:  # Now inactive
                    success_count += 1
            elif action == 'delete':
                # First delete sessions
                db_helper.delete_user_sessions(user_id)
                # Then delete user
                success = db_helper.delete_user(user_id)
                if success:
                    success_count += 1
                    # Log the action
                    db_helper.log_audit_action(
                        admin_id=session['user_id'],
                        action_type='BULK_DELETE_USER',
                        target_id=user_id,
                        target_type='user',
                        details=f"Deleted in bulk action",
                        ip_address=request.remote_addr
                    )
            else:
                continue
        
        action_text = {
            'activate': 'activated',
            'deactivate': 'deactivated',
            'delete': 'deleted'
        }.get(action, 'processed')
        
        flash(f'Successfully {action_text} {success_count} out of {total_count} selected user(s).', 'success')
    
    except Exception as e:
        flash(f'Error processing bulk action: {str(e)}', 'danger')
    
    return redirect(url_for('admin.admin_users'))


# ------------------ ORDER MANAGEMENT ------------------
@admin_bp.route('/orders')
@admin_required
def admin_orders():
    """List all orders for invoice management"""
    orders = db_helper.get_all_orders()
    return render_template('admin_orders.html', orders=orders)


@admin_bp.route('/orders/<int:order_id>')
@admin_required
def admin_order_detail(order_id):
    """Show detailed information (invoice) for a specific order"""
    order = db_helper.get_order_by_id(order_id)
    if not order:
        flash('Order not found.', 'danger')
        return redirect(url_for('admin.admin_orders'))
    items = db_helper.get_order_items(order_id)
    return render_template('admin_order_detail.html', order=order, items=items)

@admin_bp.route('/orders/<int:order_id>/update-status', methods=['POST'])
@admin_required
def update_order_status(order_id):
    """Update the status of an order"""
    new_status = request.form.get('status')
    if not new_status:
        flash('Status is required.', 'danger')
        return redirect(url_for('admin.admin_orders'))
    
    # Validate status value
    valid_statuses = ['pending', 'processing', 'shipped', 'delivered', 'cancelled']
    if new_status not in valid_statuses:
        flash('Invalid status value.', 'danger')
        return redirect(url_for('admin.admin_orders'))
    
    success = db_helper.update_order_status(order_id, new_status)
    if success:
        flash(f'Order #{order_id} status updated to {new_status.title()}.', 'success')
    else:
        flash('Failed to update order status.', 'danger')
    
    return redirect(url_for('admin.admin_orders'))

@admin_bp.route('/logout')
def admin_logout():
    if 'session_id' in session:
        db_helper.delete_session(session['session_id'])
    
    session.clear()
    flash('Admin logged out successfully.', 'info')
    return redirect(url_for('admin.admin_login'))

