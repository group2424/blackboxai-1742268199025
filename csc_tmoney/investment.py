from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from auth import login_required
from firebase_config import db
import logging
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
investment_bp = Blueprint('investment_bp', __name__)

@investment_bp.route('/investment/calculator')
def calculator():
    """Investment calculator page."""
    return render_template('investment_calculator.html')

@investment_bp.route('/investment/invest', methods=['GET', 'POST'])
@login_required
def invest():
    """Handle investment creation."""
    if request.method == 'POST':
        try:
            amount = float(request.form.get('amount'))
            tier = request.form.get('tier')
            
            # Validate investment amount based on tier
            if tier == 'starter' and (amount < 50000 or amount > 499999):
                return render_template('investment_calculator.html', 
                                    error="Starter tier requires 50,000 - 499,999 RWF")
            elif tier == 'premium' and (amount < 500000 or amount > 4999999):
                return render_template('investment_calculator.html', 
                                    error="Premium tier requires 500,000 - 4,999,999 RWF")
            elif tier == 'vip' and amount < 5000000:
                return render_template('investment_calculator.html', 
                                    error="VIP tier requires minimum 5,000,000 RWF")
            
            # Get daily return rate based on tier
            daily_rate = {
                'starter': 0.02,  # 2%
                'premium': 0.05,  # 5%
                'vip': 0.08      # 8%
            }.get(tier)
            
            # Create investment record
            investment_data = {
                'user_id': session['user_id'],
                'amount': amount,
                'tier': tier,
                'daily_rate': daily_rate,
                'status': 'pending',
                'created_at': datetime.utcnow(),
                'duration_days': 30
            }
            
            # Add to database
            db.collection('investments').add(investment_data)
            
            # Update user's pending investments
            user_ref = db.collection('users').document(session['user_id'])
            user_ref.update({
                'pending_investments': firestore.ArrayUnion([investment_data])
            })
            
            return redirect(url_for('dashboard_bp.dashboard'))
            
        except Exception as e:
            logger.error(f"Investment creation error: {str(e)}")
            return render_template('investment_calculator.html', 
                                error="An error occurred. Please try again.")
    
    return render_template('investment_calculator.html')

@investment_bp.route('/investment/<investment_id>')
@login_required
def view(investment_id):
    """View investment details."""
    try:
        investment = db.collection('investments').document(investment_id).get()
        if not investment.exists:
            return render_template('errors/404.html'), 404
            
        investment_data = investment.to_dict()
        
        # Check if user owns this investment
        if investment_data['user_id'] != session['user_id']:
            return render_template('errors/403.html'), 403
            
        return render_template('investment/view.html', investment=investment_data)
        
    except Exception as e:
        logger.error(f"Investment view error: {str(e)}")
        return render_template('errors/500.html'), 500

@investment_bp.route('/api/calculate-returns', methods=['POST'])
def calculate_returns():
    """API endpoint to calculate investment returns."""
    try:
        data = request.get_json()
        amount = float(data.get('amount', 0))
        tier = data.get('tier')
        
        # Get daily return rate based on tier
        daily_rate = {
            'starter': 0.02,  # 2%
            'premium': 0.05,  # 5%
            'vip': 0.08      # 8%
        }.get(tier)
        
        if not daily_rate:
            return jsonify({'error': 'Invalid investment tier'}), 400
            
        # Calculate returns
        daily_return = amount * daily_rate
        monthly_return = daily_return * 30
        total_return = amount + monthly_return
        
        return jsonify({
            'daily_return': daily_return,
            'monthly_return': monthly_return,
            'total_return': total_return
        })
        
    except Exception as e:
        logger.error(f"Return calculation error: {str(e)}")
        return jsonify({'error': 'Calculation failed'}), 500
