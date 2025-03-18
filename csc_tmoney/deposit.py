from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from auth import login_required
from firebase_config import db
import logging
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
deposit_bp = Blueprint('deposit_bp', __name__)

@deposit_bp.route('/deposit', methods=['GET', 'POST'])
@login_required
def deposit():
    """Handle deposit creation."""
    if request.method == 'POST':
        try:
            amount = float(request.form.get('amount'))
            phone = request.form.get('phone')
            
            # Validate amount
            if amount < 50000:  # Minimum deposit amount
                return render_template('deposit.html', 
                                    error="Minimum deposit amount is 50,000 RWF")
            
            # Create deposit record
            deposit_data = {
                'user_id': session['user_id'],
                'amount': amount,
                'phone': phone,
                'status': 'pending',
                'created_at': datetime.utcnow()
            }
            
            # Add to database
            deposit_ref = db.collection('deposits').add(deposit_data)
            
            # Update user's pending deposits
            user_ref = db.collection('users').document(session['user_id'])
            user_ref.update({
                'pending_deposits': firestore.ArrayUnion([{
                    'id': deposit_ref[1].id,
                    'amount': amount,
                    'created_at': datetime.utcnow()
                }])
            })
            
            return redirect(url_for('dashboard_bp.dashboard'))
            
        except Exception as e:
            logger.error(f"Deposit creation error: {str(e)}")
            return render_template('deposit.html', 
                                error="An error occurred. Please try again.")
    
    return render_template('deposit.html')

@deposit_bp.route('/deposit/<deposit_id>')
@login_required
def view(deposit_id):
    """View deposit details."""
    try:
        deposit = db.collection('deposits').document(deposit_id).get()
        if not deposit.exists:
            return render_template('errors/404.html'), 404
            
        deposit_data = deposit.to_dict()
        
        # Check if user owns this deposit
        if deposit_data['user_id'] != session['user_id']:
            return render_template('errors/403.html'), 403
            
        return render_template('deposit/view.html', deposit=deposit_data)
        
    except Exception as e:
        logger.error(f"Deposit view error: {str(e)}")
        return render_template('errors/500.html'), 500

@deposit_bp.route('/api/verify-deposit', methods=['POST'])
@login_required
def verify_deposit():
    """API endpoint to verify deposit status."""
    try:
        data = request.get_json()
        deposit_id = data.get('deposit_id')
        
        deposit = db.collection('deposits').document(deposit_id).get()
        if not deposit.exists:
            return jsonify({'error': 'Deposit not found'}), 404
            
        deposit_data = deposit.to_dict()
        
        # Check if user owns this deposit
        if deposit_data['user_id'] != session['user_id']:
            return jsonify({'error': 'Unauthorized'}), 403
            
        return jsonify({
            'status': deposit_data['status'],
            'amount': deposit_data['amount'],
            'created_at': deposit_data['created_at'].isoformat()
        })
        
    except Exception as e:
        logger.error(f"Deposit verification error: {str(e)}")
        return jsonify({'error': 'Verification failed'}), 500

@deposit_bp.route('/api/cancel-deposit', methods=['POST'])
@login_required
def cancel_deposit():
    """API endpoint to cancel a pending deposit."""
    try:
        data = request.get_json()
        deposit_id = data.get('deposit_id')
        
        deposit_ref = db.collection('deposits').document(deposit_id)
        deposit = deposit_ref.get()
        
        if not deposit.exists:
            return jsonify({'error': 'Deposit not found'}), 404
            
        deposit_data = deposit.to_dict()
        
        # Check if user owns this deposit
        if deposit_data['user_id'] != session['user_id']:
            return jsonify({'error': 'Unauthorized'}), 403
            
        # Check if deposit is still pending
        if deposit_data['status'] != 'pending':
            return jsonify({'error': 'Only pending deposits can be cancelled'}), 400
            
        # Update deposit status
        deposit_ref.update({
            'status': 'cancelled',
            'cancelled_at': datetime.utcnow()
        })
        
        # Remove from user's pending deposits
        user_ref = db.collection('users').document(session['user_id'])
        user_ref.update({
            'pending_deposits': firestore.ArrayRemove([{
                'id': deposit_id,
                'amount': deposit_data['amount'],
                'created_at': deposit_data['created_at']
            }])
        })
        
        return jsonify({'message': 'Deposit cancelled successfully'})
        
    except Exception as e:
        logger.error(f"Deposit cancellation error: {str(e)}")
        return jsonify({'error': 'Cancellation failed'}), 500
