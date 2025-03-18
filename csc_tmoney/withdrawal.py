from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from auth import login_required
from firebase_config import db
import logging
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
withdrawal_bp = Blueprint('withdrawal_bp', __name__)

@withdrawal_bp.route('/withdrawal', methods=['GET', 'POST'])
@login_required
def withdraw():
    """Handle withdrawal creation."""
    if request.method == 'POST':
        try:
            amount = float(request.form.get('amount'))
            phone = request.form.get('phone')
            
            # Get user's current balance
            user_ref = db.collection('users').document(session['user_id'])
            user = user_ref.get().to_dict()
            
            # Validate amount
            if amount > user['balance']:
                return render_template('withdrawal.html', 
                                    error="Insufficient balance")
                                    
            if amount < 10000:  # Minimum withdrawal amount
                return render_template('withdrawal.html', 
                                    error="Minimum withdrawal amount is 10,000 RWF")
            
            # Create withdrawal record
            withdrawal_data = {
                'user_id': session['user_id'],
                'amount': amount,
                'phone': phone,
                'status': 'pending',
                'created_at': datetime.utcnow()
            }
            
            # Add to database
            withdrawal_ref = db.collection('withdrawals').add(withdrawal_data)
            
            # Update user's pending withdrawals and reduce balance
            user_ref.update({
                'pending_withdrawals': firestore.ArrayUnion([{
                    'id': withdrawal_ref[1].id,
                    'amount': amount,
                    'created_at': datetime.utcnow()
                }]),
                'balance': user['balance'] - amount
            })
            
            return redirect(url_for('dashboard_bp.dashboard'))
            
        except Exception as e:
            logger.error(f"Withdrawal creation error: {str(e)}")
            return render_template('withdrawal.html', 
                                error="An error occurred. Please try again.")
    
    try:
        # Get user's current balance
        user_ref = db.collection('users').document(session['user_id'])
        user = user_ref.get().to_dict()
        
        return render_template('withdrawal.html', balance=user['balance'])
        
    except Exception as e:
        logger.error(f"Withdrawal page error: {str(e)}")
        return render_template('withdrawal.html', error="Failed to load balance")

@withdrawal_bp.route('/withdrawal/<withdrawal_id>')
@login_required
def view(withdrawal_id):
    """View withdrawal details."""
    try:
        withdrawal = db.collection('withdrawals').document(withdrawal_id).get()
        if not withdrawal.exists:
            return render_template('errors/404.html'), 404
            
        withdrawal_data = withdrawal.to_dict()
        
        # Check if user owns this withdrawal
        if withdrawal_data['user_id'] != session['user_id']:
            return render_template('errors/403.html'), 403
            
        return render_template('withdrawal/view.html', withdrawal=withdrawal_data)
        
    except Exception as e:
        logger.error(f"Withdrawal view error: {str(e)}")
        return render_template('errors/500.html'), 500

@withdrawal_bp.route('/api/verify-withdrawal', methods=['POST'])
@login_required
def verify_withdrawal():
    """API endpoint to verify withdrawal status."""
    try:
        data = request.get_json()
        withdrawal_id = data.get('withdrawal_id')
        
        withdrawal = db.collection('withdrawals').document(withdrawal_id).get()
        if not withdrawal.exists:
            return jsonify({'error': 'Withdrawal not found'}), 404
            
        withdrawal_data = withdrawal.to_dict()
        
        # Check if user owns this withdrawal
        if withdrawal_data['user_id'] != session['user_id']:
            return jsonify({'error': 'Unauthorized'}), 403
            
        return jsonify({
            'status': withdrawal_data['status'],
            'amount': withdrawal_data['amount'],
            'created_at': withdrawal_data['created_at'].isoformat()
        })
        
    except Exception as e:
        logger.error(f"Withdrawal verification error: {str(e)}")
        return jsonify({'error': 'Verification failed'}), 500

@withdrawal_bp.route('/api/cancel-withdrawal', methods=['POST'])
@login_required
def cancel_withdrawal():
    """API endpoint to cancel a pending withdrawal."""
    try:
        data = request.get_json()
        withdrawal_id = data.get('withdrawal_id')
        
        withdrawal_ref = db.collection('withdrawals').document(withdrawal_id)
        withdrawal = withdrawal_ref.get()
        
        if not withdrawal.exists:
            return jsonify({'error': 'Withdrawal not found'}), 404
            
        withdrawal_data = withdrawal.to_dict()
        
        # Check if user owns this withdrawal
        if withdrawal_data['user_id'] != session['user_id']:
            return jsonify({'error': 'Unauthorized'}), 403
            
        # Check if withdrawal is still pending
        if withdrawal_data['status'] != 'pending':
            return jsonify({'error': 'Only pending withdrawals can be cancelled'}), 400
            
        # Update withdrawal status
        withdrawal_ref.update({
            'status': 'cancelled',
            'cancelled_at': datetime.utcnow()
        })
        
        # Remove from user's pending withdrawals and restore balance
        user_ref = db.collection('users').document(session['user_id'])
        user = user_ref.get().to_dict()
        
        user_ref.update({
            'pending_withdrawals': firestore.ArrayRemove([{
                'id': withdrawal_id,
                'amount': withdrawal_data['amount'],
                'created_at': withdrawal_data['created_at']
            }]),
            'balance': user['balance'] + withdrawal_data['amount']
        })
        
        return jsonify({'message': 'Withdrawal cancelled successfully'})
        
    except Exception as e:
        logger.error(f"Withdrawal cancellation error: {str(e)}")
        return jsonify({'error': 'Cancellation failed'}), 500
