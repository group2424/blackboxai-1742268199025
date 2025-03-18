from flask import Flask, render_template, session, redirect, url_for
from firebase_config import db
import logging
from datetime import timedelta, datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your-secret-key-replace-in-production'
app.permanent_session_lifetime = timedelta(days=7)

# Custom filters
@app.template_filter('format_currency')
def format_currency(value):
    """Format number as currency with RWF symbol."""
    try:
        return f"RWF {int(value):,}"
    except (ValueError, TypeError):
        return "RWF 0"

# Context processor for templates
@app.context_processor
def utility_processor():
    def now():
        return datetime.utcnow()
    return dict(now=now)

# Register blueprints
from auth import auth_bp
from dashboard import dashboard_bp
from deposit import deposit_bp
from investment import investment_bp
from withdrawal import withdrawal_bp
from referral import referral_bp
from admin_panel import admin_bp

app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
app.register_blueprint(deposit_bp, url_prefix='/deposit')
app.register_blueprint(investment_bp, url_prefix='/investment')
app.register_blueprint(withdrawal_bp, url_prefix='/withdrawal')
app.register_blueprint(referral_bp, url_prefix='/referral')
app.register_blueprint(admin_bp, url_prefix='/admin')

@app.route('/')
def index():
    """Render the homepage."""
    return render_template('home.html')

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors."""
    return render_template('errors/404.html'), 404

@app.errorhandler(403)
def forbidden(e):
    """Handle 403 errors."""
    return render_template('errors/403.html'), 403

@app.errorhandler(401)
def unauthorized(e):
    """Handle 401 errors."""
    return render_template('errors/401.html'), 401

@app.errorhandler(429)
def too_many_requests(e):
    """Handle 429 errors."""
    return render_template('errors/429.html'), 429

@app.errorhandler(500)
def internal_server_error(e):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {str(e)}")
    return render_template('errors/500.html'), 500

if __name__ == '__main__':
    try:
        # Ensure Firebase is initialized
        if db:
            logger.info("Firebase connection successful")
        else:
            logger.error("Firebase connection failed")
            raise Exception("Firebase connection failed")
            
        # Run the Flask app
        app.run(host='0.0.0.0', port=8000, debug=True)
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
