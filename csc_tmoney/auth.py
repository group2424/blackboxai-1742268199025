from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for, flash
from firebase_config import db
from functools import wraps
import logging
import bcrypt
import re
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
auth_bp = Blueprint('auth_bp', __name__)

def login_required(f):
    """Decorator to check if user is logged in."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page', 'error')
            return redirect(url_for('auth_bp.login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to check if user is an admin."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page', 'error')
            return redirect(url_for('auth_bp.login'))
            
        user_ref = db.collection('users').document(session['user_id'])
        user = user_ref.get()
        
        if not user.exists or not user.to_dict().get('is_admin', False):
            flash('You do not have permission to access this page', 'error')
            return redirect(url_for('index'))
            
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    if request.method == 'POST':
        try:
            phone = request.form.get('phone')
            password = request.form.get('password')
            remember = request.form.get('remember', False)
            
            # Validate phone number format
            if not re.match(r'^07[2389][0-9]{7}$', phone):
                flash('Invalid phone number format', 'error')
                return render_template('auth/login.html')
            
            # Check if user exists
            users_ref = db.collection('users')
            user = users_ref.where('phone', '==', phone).get()
            
            if not user:
                flash('Invalid phone number or password', 'error')
                return render_template('auth/login.html')
                
            user_data = user[0].to_dict()
            
            # Verify password
            if not bcrypt.checkpw(password.encode('utf-8'), user_data['password'].encode('utf-8')):
                flash('Invalid phone number or password', 'error')
                return render_template('auth/login.html')
            
            # Set session
            session['user_id'] = user[0].id
            if remember:
                session.permanent = True
            
            # Update last login
            users_ref.document(user[0].id).update({
                'last_login': datetime.utcnow()
            })
            
            flash('Login successful', 'success')
            return redirect(url_for('dashboard_bp.dashboard'))
            
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            flash('An error occurred. Please try again.', 'error')
            return render_template('auth/login.html')
    
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Handle user registration."""
    if request.method == 'POST':
        try:
            full_name = request.form.get('full_name')
            phone = request.form.get('phone')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            referral_code = request.form.get('referral_code')
            
            # Validate inputs
            if not all([full_name, phone, password, confirm_password]):
                flash('All fields are required', 'error')
                return render_template('auth/register.html')
            
            if not re.match(r'^07[2389][0-9]{7}$', phone):
                flash('Invalid phone number format', 'error')
                return render_template('auth/register.html')
            
            if password != confirm_password:
                flash('Passwords do not match', 'error')
                return render_template('auth/register.html')
            
            if len(password) < 8:
                flash('Password must be at least 8 characters long', 'error')
                return render_template('auth/register.html')
            
            # Check if phone number is already registered
            users_ref = db.collection('users')
            existing_user = users_ref.where('phone', '==', phone).get()
            
            if existing_user:
                flash('Phone number is already registered', 'error')
                return render_template('auth/register.html')
            
            # Hash password
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            
            # Create user data
            user_data = {
                'full_name': full_name,
                'phone': phone,
                'password': hashed_password.decode('utf-8'),
                'balance': 0,
                'created_at': datetime.utcnow(),
                'is_active': True,
                'is_admin': False
            }
            
            # Check referral code
            if referral_code:
                referrer = users_ref.where('referral_code', '==', referral_code).get()
                if referrer:
                    user_data['referred_by'] = referrer[0].id
                else:
                    flash('Invalid referral code', 'error')
                    return render_template('auth/register.html')
            
            # Add user to database
            new_user = users_ref.add(user_data)
            
            # Set session
            session['user_id'] = new_user[1].id
            
            flash('Registration successful', 'success')
            return redirect(url_for('dashboard_bp.dashboard'))
            
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            flash('An error occurred. Please try again.', 'error')
            return render_template('auth/register.html')
    
    return render_template('auth/register.html')

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Handle password reset request."""
    if request.method == 'POST':
        try:
            phone = request.form.get('phone')
            
            # Validate phone number format
            if not re.match(r'^07[2389][0-9]{7}$', phone):
                flash('Invalid phone number format', 'error')
                return render_template('auth/forgot_password.html')
            
            # Check if user exists
            users_ref = db.collection('users')
            user = users_ref.where('phone', '==', phone).get()
            
            if not user:
                flash('No account found with this phone number', 'error')
                return render_template('auth/forgot_password.html')
            
            # Generate and send reset code
            # TODO: Implement SMS sending functionality
            reset_code = '123456'  # For testing purposes
            
            # Store reset code in session
            session['reset_phone'] = phone
            session['reset_code'] = reset_code
            
            flash('Reset code has been sent to your phone', 'success')
            return render_template('auth/forgot_password.html', step=2)
            
        except Exception as e:
            logger.error(f"Password reset error: {str(e)}")
            flash('An error occurred. Please try again.', 'error')
            return render_template('auth/forgot_password.html')
    
    return render_template('auth/forgot_password.html', step=1)

@auth_bp.route('/verify-reset-code', methods=['POST'])
def verify_reset_code():
    """Verify password reset code."""
    try:
        code = request.form.get('code')
        
        if not code:
            flash('Please enter the verification code', 'error')
            return render_template('auth/forgot_password.html', step=2)
        
        if code != session.get('reset_code'):
            flash('Invalid verification code', 'error')
            return render_template('auth/forgot_password.html', step=2)
        
        return render_template('auth/forgot_password.html', step=3)
        
    except Exception as e:
        logger.error(f"Code verification error: {str(e)}")
        flash('An error occurred. Please try again.', 'error')
        return render_template('auth/forgot_password.html', step=2)

@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """Reset user password."""
    try:
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not all([password, confirm_password]):
            flash('All fields are required', 'error')
            return render_template('auth/forgot_password.html', step=3)
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('auth/forgot_password.html', step=3)
        
        if len(password) < 8:
            flash('Password must be at least 8 characters long', 'error')
            return render_template('auth/forgot_password.html', step=3)
        
        # Get user by phone
        phone = session.get('reset_phone')
        if not phone:
            flash('Password reset session expired', 'error')
            return redirect(url_for('auth_bp.forgot_password'))
        
        users_ref = db.collection('users')
        user = users_ref.where('phone', '==', phone).get()
        
        if not user:
            flash('User not found', 'error')
            return redirect(url_for('auth_bp.forgot_password'))
        
        # Update password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        users_ref.document(user[0].id).update({
            'password': hashed_password.decode('utf-8')
        })
        
        # Clear reset session
        session.pop('reset_phone', None)
        session.pop('reset_code', None)
        
        flash('Password has been reset successfully', 'success')
        return redirect(url_for('auth_bp.login'))
        
    except Exception as e:
        logger.error(f"Password reset error: {str(e)}")
        flash('An error occurred. Please try again.', 'error')
        return render_template('auth/forgot_password.html', step=3)

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """Handle user logout."""
    session.clear()
    flash('You have been logged out', 'success')
    return redirect(url_for('index'))
