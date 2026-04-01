"""
Security utilities: password hashing, JWT, and authentication.
"""
from datetime import datetime, timezone, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_DAYS
from database import db, sb_find_one
from models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)

DEFAULT_ADMIN = User(
    id="default-admin",
    email="admin@industria.visual",
    name="Administrador",
    role="admin",
    is_active=True,
    password_hash=None,
    created_at=datetime.now(timezone.utc),
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash."""
    return pwd_context.hash(password)


def create_access_token(data: dict) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> User:
    """Get current authenticated user from JWT token. Returns default admin if no token."""
    if credentials is None:
        return DEFAULT_ADMIN

    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return DEFAULT_ADMIN
    except JWTError:
        return DEFAULT_ADMIN

    user_doc = await sb_find_one("users", {"id": user_id})
    if user_doc is None:
        return DEFAULT_ADMIN

    if isinstance(user_doc.get('created_at'), str):
        user_doc['created_at'] = datetime.fromisoformat(user_doc['created_at'])

    return User(**user_doc)


async def require_role(user: User, allowed_roles: list) -> User:
    """Check if user has required role."""
    if user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return user
