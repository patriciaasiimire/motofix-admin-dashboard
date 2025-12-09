from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import os

security = HTTPBearer()

SECRET_KEY = os.getenv("ADMIN_JWT_SECRET", "change-me-to-something-very-strong")  # set this in Render
ALGORITHM = "HS256"

def verify_admin_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Not authorized")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload