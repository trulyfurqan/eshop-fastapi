import re
from passlib.context import CryptContext
from fastapi import HTTPException, status
import jwt
import random  # For generating 2FA codes
from models import User
from config import get_settings
import smtplib  # For sending 2FA codes via email

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_hashed_password(password):
    return pwd_context.hash(password)

async def very_token(token: str):
    '''verify token from login'''
    try:
        payload = jwt.decode(token, get_settings().SECRET,
                             algorithms=["HS256"])
        user = await User.get(id=payload.get("id"))
    except:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return await user

async def very_token_email(token: str):
    '''verify token from email'''
    try:
        payload = jwt.decode(token, get_settings().SECRET,
                             algorithms=["HS256"])
        user = await User.get(id=payload.get("id"), email=payload.get("email"))
    except:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return await user

# bug: sam_ple@gma.com:Trye ; sam_p_le@gma.com: False!!
regex = '^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w{2,3}$'

def is_not_email(email):
    """if valid mail: return 'True' \n 
     ** This is a simple way to do this and is not recommended for a real project ** """
    if(re.search(regex, email)):
        return False
    else:
        return True

async def verify_password(plain_password, database_hashed_password):
    return pwd_context.verify(plain_password, database_hashed_password)

async def authenticate_user(username: str, password: str):
    user = await User.get(username=username)
    if user and verify_password(password, user.password):
        if not user.is_verifide:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email not verifide",
                headers={"WWW-Authenticate": "Bearer"}
            )
        return user
    return False

async def token_generator(username: str, password: str):
    user = await authenticate_user(username, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Username or Password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    token_data = {
        "id": user.id,
        "username": user.username
    }
    token = jwt.encode(token_data, get_settings().SECRET, algorithm="HS256")
    return token

# New Feature: Two-Factor Authentication (2FA)
async def send_2fa_code(email: str):
    code = random.randint(100000, 999999)
    server = smtplib.SMTP('smtp.example.com', 587)
    server.starttls()
    server.login("your-email@example.com", "your-password")
    message = f"Your 2FA code is: {code}"
    server.sendmail("your-email@example.com", email, message)
    server.quit()
    return code

async def verify_2fa_code(user: User, code: int):
    # This is just a placeholder. The actual implementation should verify the code.
    if user.two_factor_code == code:
        return True
    return False

async def enable_2fa(user: User):
    code = await send_2fa_code(user.email)
    user.two_factor_code = code
    await user.save()
    return "2FA enabled, check your email for the code."
