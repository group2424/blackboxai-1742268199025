from flask import Blueprint, render_template, session
from auth import login_required
from firebase_config import db
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
dashboard_bp = Blueprint('dashboard_bp', __name__)

@dashboard_bp.route('/dashboard')
@login_required
def dashboard():
    try:
        user_id = session['user_id']
        user_ref = db.collection('users').document(user_id)
        user_data = user_ref.get().to_dict()
        
        # Get user's investments
        investments = []
        investments_ref = db.collection('investments').where('user_id', '==', user_id).get()
        for inv in investments_ref:
            inv_data = inv.to_dict()
            inv_data['id'] = inv.id
            investments.append(inv_data)
            
        # Get user's deposits
        deposits = []
        deposits_ref = db.collection('deposits').where('user_id', '==', user_id).get()
        for dep in deposits_ref:
            dep_data = dep.to_dict()
            dep_data['id'] = dep.id
            deposits.append(dep_data)
            
        # Get user's withdrawals
        withdrawals = []
        withdrawals_ref = db.collection('withdrawals').where('user_id', '==', user_id).get()
        for wit in withdrawals_ref:
            wit_data = wit.to_dict()
            wit_data['id'] = wit.id
            withdrawals.append(wit_data)
            
        # Get user's referrals
        referrals = []
        referrals_ref = db.collection('users').where('referred_by', '==', user_id).get()
        for ref in referrals_ref:
            ref_data = ref.to_dict()
            ref_data['id'] = ref.id
            referrals.append(ref_data)
            
        return render_template('dashboard.html',
                            user=user_data,
                            investments=investments,
                            deposits=deposits,
                            withdrawals=withdrawals,
                            referrals=referrals)
                            
    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}")
        return render_template('errors/500.html'), 500
