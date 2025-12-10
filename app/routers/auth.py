from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from datetime import datetime, timedelta
import os
import jwt
from passlib.context import CryptContext
from typing import Optional

router = APIRouter(prefix="/api", tags=["auth"])

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("ADMIN_JWT_SECRET", "my_very_long_random_secret_1234567890")
ALGORITHM = "HS256"
# ACCESS_TOKEN_EXPIRE_MINUTES will be read from env at token creation time if overridden
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ADMIN_TOKEN_EXPIRE_MINUTES", "240"))

class LoginIn(BaseModel):
    username: Optional[str] = "admin"
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

def verify_password(plain_password: str) -> bool:
    # Read env vars at call time so tests can monkeypatch them before calling
    admin_hash = os.getenv("ADMIN_PASSWORD_HASH")
    admin_pw = os.getenv("ADMIN_PASSWORD")
    if admin_hash:
        return pwd_ctx.verify(plain_password, admin_hash)
    if admin_pw:
        return plain_password == admin_pw
    return False

def create_access_token(*, data: dict, expires_delta: timedelta):
    # Read secret at call time to respect test monkeypatching or runtime env changes
    secret = os.getenv("ADMIN_JWT_SECRET", SECRET_KEY)
    alg = ALGORITHM
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, secret, algorithm=alg)

@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn):
    if not verify_password(payload.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(data={"sub": "admin", "role": "admin"}, expires_delta=access_token_expires)
    return {"access_token": token, "token_type": "bearer"}