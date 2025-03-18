from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from firebase_config import db
from auth import admin_required
from datetime import datetime
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
admin_bp = Blueprint('admin_bp', __name__, url_prefix='/admin')

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle admin login."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        try:
            # Check admin credentials
            admins_ref = db.collection('admins')
            admin = admins_ref.where('username', '==', username).get()
            
            if not admin:
                flash('Invalid credentials', 'error')
                return render_template('admin/login.html')
            
            admin_data = admin[0].to_dict()
            if password != admin_data.get('password'):  # In production, use proper password hashing
                flash('Invalid credentials', 'error')
                return render_template('admin/login.html')
            
            # Set admin session
            session['admin_id'] = admin[0].id
            session['admin_username'] = username
            
            flash('Login successful', 'success')
            return redirect(url_for('admin_bp.dashboard'))
            
        except Exception as e:
            logger.error(f"Admin login error: {str(e)}")
            flash('An error occurred. Please try again.', 'error')
            return render_template('admin/login.html')
    
    return render_template('admin/login.html')

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """Admin dashboard showing overview statistics."""
    try:
        # Get statistics
        users_ref = db.collection('users')
        deposits_ref = db.collection('deposits')
        withdrawals_ref = db.collection('withdrawals')
        investments_ref = db.collection('investments')
        
        stats = {
            'total_users': len(users_ref.get()),
            'total_deposits': sum(d.to_dict().get('amount', 0) for d in deposits_ref.get()),
            'total_withdrawals': sum(w.to_dict().get('amount', 0) for w in withdrawals_ref.get()),
            'total_investments': sum(i.to_dict().get('amount', 0) for i in investments_ref.get()),
            'pending_deposits': len(deposits_ref.where('status', '==', 'pending').get()),
            'pending_withdrawals': len(withdrawals_ref.where('status', '==', 'pending').get())
        }
        
        return render_template('admin/dashboard.html', stats=stats)
        
    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}")
        flash('Error loading dashboard data', 'error')
        return render_template('admin/dashboard.html')

@admin_bp.route('/users')
@admin_required
def users():
    """Manage users."""
    try:
        users_ref = db.collection('users')
        users = [{'id': doc.id, **doc.to_dict()} for doc in users_ref.get()]
        return render_template('admin/users.html', users=users)
    except Exception as e:
        logger.error(f"Users page error: {str(e)}")
        flash('Error loading users', 'error')
        return render_template('admin/users.html', users=[])

@admin_bp.route('/deposits')
@admin_required
def deposits():
    """Manage deposits."""
    try:
        deposits_ref = db.collection('deposits')
        deposits = [{'id': doc.id, **doc.to_dict()} for doc in deposits_ref.get()]
        return render_template('admin/deposits.html', deposits=deposits)
    except Exception as e:
        logger.error(f"Deposits page error: {str(e)}")
        flash('Error loading deposits', 'error')
        return render_template('admin/deposits.html', deposits=[])

@admin_bp.route('/withdrawals')
@admin_required
def withdrawals():
    """Manage withdrawals."""
    try:
        withdrawals_ref = db.collection('withdrawals')
        withdrawals = [{'id': doc.id, **doc.to_dict()} for doc in withdrawals_ref.get()]
        return render_template('admin/withdrawals.html', withdrawals=withdrawals)
    except Exception as e:
        logger.error(f"Withdrawals page error: {str(e)}")
        flash('Error loading withdrawals', 'error')
        return render_template('admin/withdrawals.html', withdrawals=[])

@admin_bp.route('/investments')
@admin_required
def investments():
    """Manage investments."""
    try:
        investments_ref = db.collection('investments')
        investments = [{'id': doc.id, **doc.to_dict()} for doc in investments_ref.get()]
        return render_template('admin/investments.html', investments=investments)
    except Exception as e:
        logger.error(f"Investments page error: {str(e)}")
        flash('Error loading investments', 'error')
        return render_template('admin/investments.html', investments=[])

@admin_bp.route('/announcements')
@admin_required
def announcements():
    """Manage announcements."""
    try:
        announcements_ref = db.collection('announcements')
        announcements = [{'id': doc.id, **doc.to_dict()} for doc in announcements_ref.get()]
        return render_template('admin/announcements.html', announcements=announcements)
    except Exception as e:
        logger.error(f"Announcements page error: {str(e)}")
        flash('Error loading announcements', 'error')
        return render_template('admin/announcements.html', announcements=[])

@admin_bp.route('/chat')
@admin_required
def chat():
    """Chat support system."""
    try:
        chats_ref = db.collection('chats')
        chats = [{'id': doc.id, **doc.to_dict()} for doc in chats_ref.get()]
        return render_template('admin/chat.html', chats=chats)
    except Exception as e:
        logger.error(f"Chat page error: {str(e)}")
        flash('Error loading chats', 'error')
        return render_template('admin/chat.html', chats=[])

@admin_bp.route('/advertisements')
@admin_required
def advertisements():
    """Manage advertisements."""
    try:
        ads_ref = db.collection('advertisements')
        ads = [{'id': doc.id, **doc.to_dict()} for doc in ads_ref.get()]
        return render_template('admin/advertisements.html', advertisements=ads)
    except Exception as e:
        logger.error(f"Advertisements page error: {str(e)}")
        flash('Error loading advertisements', 'error')
        return render_template('admin/advertisements.html', advertisements=[])

# API Endpoints for AJAX requests

@admin_bp.route('/api/approve-deposit/<deposit_id>', methods=['POST'])
@admin_required
def approve_deposit(deposit_id):
    """Approve a deposit."""
    try:
        deposit_ref = db.collection('deposits').document(deposit_id)
        deposit = deposit_ref.get()
        
        if not deposit.exists:
            return jsonify({'error': 'Deposit not found'}), 404
        
        deposit_data = deposit.to_dict()
        user_ref = db.collection('users').document(deposit_data['user_id'])
        
        # Update deposit status
        deposit_ref.update({
            'status': 'approved',
            'approved_at': datetime.utcnow(),
            'approved_by': session['admin_id']
        })
        
        # Update user balance
        user_ref.update({
            'balance': user_ref.get().to_dict()['balance'] + deposit_data['amount']
        })
        
        return jsonify({'message': 'Deposit approved successfully'})
        
    except Exception as e:
        logger.error(f"Approve deposit error: {str(e)}")
        return jsonify({'error': 'Failed to approve deposit'}), 500

@admin_bp.route('/api/approve-withdrawal/<withdrawal_id>', methods=['POST'])
@admin_required
def approve_withdrawal(withdrawal_id):
    """Approve a withdrawal."""
    try:
        withdrawal_ref = db.collection('withdrawals').document(withdrawal_id)
        withdrawal = withdrawal_ref.get()
        
        if not withdrawal.exists:
            return jsonify({'error': 'Withdrawal not found'}), 404
        
        withdrawal_data = withdrawal.to_dict()
        user_ref = db.collection('users').document(withdrawal_data['user_id'])
        
        # Update withdrawal status
        withdrawal_ref.update({
            'status': 'approved',
            'approved_at': datetime.utcnow(),
            'approved_by': session['admin_id']
        })
        
        # Update user balance
        user_ref.update({
            'balance': user_ref.get().to_dict()['balance'] - withdrawal_data['amount']
        })
        
        return jsonify({'message': 'Withdrawal approved successfully'})
        
    except Exception as e:
        logger.error(f"Approve withdrawal error: {str(e)}")
        return jsonify({'error': 'Failed to approve withdrawal'}), 500

@admin_bp.route('/logout', methods=['POST'])
@admin_required
def logout():
    """Handle admin logout."""
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('admin_bp.login'))
