"""
Authentication utilities for the Culinary Companion API.

Flow: AuthenticationFlow
Contract:
  - Input: Credentials (email/password) or JWT token
  - Output: Authenticated user or JWT token
  - Errors: 401 Unauthorized, 403 Forbidden
  - Side effects: None (stateless JWT)
"""
import logging
import os
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from src.api.database import get_db
from src.api.models import User

logger = logging.getLogger(__name__)

# Configuration from environment; see .env.example for required variables
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "culinary-companion-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# PUBLIC_INTERFACE
def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt.

    Args:
        password: The plaintext password to hash.

    Returns:
        The bcrypt hash string.
    """
    return pwd_context.hash(password)


# PUBLIC_INTERFACE
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash.

    Args:
        plain_password: The plaintext password.
        hashed_password: The stored bcrypt hash.

    Returns:
        True if the password matches, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)


# PUBLIC_INTERFACE
def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT access token.

    Args:
        data: Claims to encode in the token (must include 'sub').
        expires_delta: Optional custom expiry duration.

    Returns:
        Encoded JWT string.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    logger.info("Created access token for sub=%s", data.get("sub"))
    return encoded_jwt


# PUBLIC_INTERFACE
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """FastAPI dependency that extracts and validates the current user from a JWT token.

    Args:
        token: Bearer token from the Authorization header.
        db: Database session.

    Returns:
        The authenticated User ORM object.

    Raises:
        HTTPException: 401 if token is invalid or user not found.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = int(user_id_str)
    except (JWTError, ValueError):
        logger.warning("Invalid JWT token received")
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        logger.warning("Token references inactive or missing user id=%s", user_id_str)
        raise credentials_exception
    return user


# PUBLIC_INTERFACE
def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """FastAPI dependency that ensures the current user has admin role.

    Args:
        current_user: The authenticated user.

    Returns:
        The admin User ORM object.

    Raises:
        HTTPException: 403 if user is not an admin.
    """
    if current_user.role != "admin":
        logger.warning("Non-admin user id=%d attempted admin action", current_user.id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


# PUBLIC_INTERFACE
def get_optional_current_user(
    token: str | None = Depends(OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)),
    db: Session = Depends(get_db),
) -> User | None:
    """FastAPI dependency that optionally extracts the current user.

    Returns None if no token is provided, instead of raising an error.
    Useful for endpoints where authentication is optional.

    Args:
        token: Optional bearer token.
        db: Database session.

    Returns:
        The User object if authenticated, None otherwise.
    """
    if token is None:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            return None
        user_id = int(user_id_str)
    except (JWTError, ValueError):
        return None

    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    return user
