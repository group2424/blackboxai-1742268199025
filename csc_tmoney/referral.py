from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from auth import login_required
from firebase_config import db
import logging
from datetime import datetime
import random
import string

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
referral_bp = Blueprint('referral_bp', __name__)

def generate_referral_code(phone):
    """Generate unique referral code."""
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"REF{timestamp}{random_str}"

@referral_bp.route('/referral')
@login_required
def referral():
    """Referral program page."""
    try:
        user_ref = db.collection('users').document(session['user_id'])
        user = user_ref.get().to_dict()
        
        # Get user's referrals
        referrals = []
        referrals_ref = db.collection('users').where('referred_by', '==', session['user_id']).get()
        
        total_earnings = 0
        for ref in referrals_ref:
            ref_data = ref.to_dict()
            ref_data['id'] = ref.id
            
            # Calculate earnings from this referral
            earnings = 0
            investments_ref = db.collection('investments').where('user_id', '==', ref.id).get()
            for inv in investments_ref:
                inv_data = inv.to_dict()
                if inv_data['status'] == 'active':
                    earnings += inv_data['amount'] * 0.05  # 5% referral bonus
            
            ref_data['earnings'] = earnings
            total_earnings += earnings
            referrals.append(ref_data)
        
        return render_template('referral.html',
                            referral_code=user.get('referral_code'),
                            referrals=referrals,
                            total_earnings=total_earnings)
                            
    except Exception as e:
        logger.error(f"Referral page error: {str(e)}")
        return render_template('errors/500.html'), 500

@referral_bp.route('/api/referral-stats')
@login_required
def referral_stats():
    """API endpoint to get referral statistics."""
    try:
        # Get user's referrals
        referrals_ref = db.collection('users').where('referred_by', '==', session['user_id']).get()
        
        total_referrals = len(referrals_ref)
        active_referrals = 0
        total_earnings = 0
        
        for ref in referrals_ref:
            # Check if referral has active investments
            investments_ref = db.collection('investments').where('user_id', '==', ref.id).get()
            has_active = False
            ref_earnings = 0
            
            for inv in investments_ref:
                inv_data = inv.to_dict()
                if inv_data['status'] == 'active':
                    has_active = True
                    ref_earnings += inv_data['amount'] * 0.05  # 5% referral bonus
            
            if has_active:
                active_referrals += 1
            total_earnings += ref_earnings
        
        return jsonify({
            'total_referrals': total_referrals,
            'active_referrals': active_referrals,
            'total_earnings': total_earnings
        })
        
    except Exception as e:
        logger.error(f"Referral stats error: {str(e)}")
        return jsonify({'error': 'Failed to load stats'}), 500

@referral_bp.route('/api/validate-referral', methods=['POST'])
def validate_referral():
    """API endpoint to validate referral code."""
    try:
        data = request.get_json()
        referral_code = data.get('referral_code')
        
        if not referral_code:
            return jsonify({'error': 'Referral code is required'}), 400
        
        # Find user with this referral code
        users_ref = db.collection('users')
        referrer = users_ref.where('referral_code', '==', referral_code).get()
        
        if not referrer:
            return jsonify({'error': 'Invalid referral code'}), 404
        
        return jsonify({'valid': True})
        
    except Exception as e:
        logger.error(f"Referral validation error: {str(e)}")
        return jsonify({'error': 'Validation failed'}), 500

@referral_bp.route('/api/referral-earnings')
@login_required
def referral_earnings():
    """API endpoint to get detailed referral earnings."""
    try:
        # Get user's referrals
        referrals_ref = db.collection('users').where('referred_by', '==', session['user_id']).get()
        
        earnings_data = []
        for ref in referrals_ref:
            ref_data = ref.to_dict()
            
            # Get referral's investments
            investments_ref = db.collection('investments').where('user_id', '==', ref.id).get()
            
            ref_earnings = {
                'referral_id': ref.id,
                'name': ref_data.get('full_name', 'Anonymous'),
                'phone': ref_data.get('phone'),
                'joined_at': ref_data.get('created_at'),
                'investments': [],
                'total_earnings': 0
            }
            
            for inv in investments_ref:
                inv_data = inv.to_dict()
                if inv_data['status'] == 'active':
                    earnings = inv_data['amount'] * 0.05  # 5% referral bonus
                    ref_earnings['total_earnings'] += earnings
                    ref_earnings['investments'].append({
                        'amount': inv_data['amount'],
                        'created_at': inv_data['created_at'],
                        'earnings': earnings
                    })
            
            earnings_data.append(ref_earnings)
        
        return jsonify(earnings_data)
        
    except Exception as e:
        logger.error(f"Referral earnings error: {str(e)}")
        return jsonify({'error': 'Failed to load earnings'}), 500
