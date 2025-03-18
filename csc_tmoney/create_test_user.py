from firebase_config import db
import bcrypt
from datetime import datetime

def create_test_user():
    try:
        # Test user data
        phone = "0722123456"
        password = "test1234"
        
        # Hash password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        # User data
        user_data = {
            'full_name': 'Test User',
            'phone': phone,
            'password': hashed_password.decode('utf-8'),
            'balance': 0,
            'created_at': datetime.utcnow(),
            'is_active': True,
            'is_admin': False
        }
        
        # Check if user already exists
        users_ref = db.collection('users')
        existing_user = users_ref.where('phone', '==', phone).get()
        
        if existing_user:
            print(f"Test user with phone {phone} already exists")
            return
        
        # Add user to database
        new_user = users_ref.add(user_data)
        print(f"Test user created successfully with ID: {new_user[1].id}")
        print(f"Login credentials:")
        print(f"Phone: {phone}")
        print(f"Password: {password}")
        
    except Exception as e:
        print(f"Error creating test user: {str(e)}")

if __name__ == '__main__':
    create_test_user()
