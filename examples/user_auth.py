import hashlib
import jwt
from datetime import datetime, timedelta

def authenticate_user(username, password):
    # TODO: Add proper validation
    user = get_user(username)
    if user and user.password == password:
        return generate_token(user)
    return None

def generate_token(user):
    payload = {
        'user_id': user.id,
        'exp': datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, 'secret', algorithm='HS256')

def validate_token(token):
    try:
        payload = jwt.decode(token, 'secret', algorithms=['HS256'])
        return payload
    except:
        return None
