"""
Authentication router: registration, login, and profile management.

Flow: AuthRouter
Entrypoint: router (APIRouter mounted at /api/auth)
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from src.api.database import get_db
from src.api.models import User
from src.api.schemas import TokenResponse, UserOut, UserRegister, UserLogin, UserUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


# PUBLIC_INTERFACE
@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Creates a new user account with the provided credentials.",
)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    """Register a new user account.

    Args:
        payload: Registration data (username, email, password, optional display_name).
        db: Database session.

    Returns:
        The newly created user profile.

    Raises:
        HTTPException 400: If username or email already exists.
    """
    logger.info("Registration attempt for email=%s", payload.email)

    # Check uniqueness
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")

    user = User(
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name or payload.username,
        role="user",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("User registered successfully id=%d", user.id)
    return user


# PUBLIC_INTERFACE
@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and obtain JWT token",
    description="Authenticates with email and password, returns a JWT access token.",
)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    """Authenticate a user and return a JWT token.

    Args:
        payload: Login credentials (email, password).
        db: Database session.

    Returns:
        JWT access token.

    Raises:
        HTTPException 401: If credentials are invalid.
    """
    logger.info("Login attempt for email=%s", payload.email)
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        logger.warning("Failed login attempt for email=%s", payload.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")

    token = create_access_token(data={"sub": str(user.id), "role": user.role})
    logger.info("Login successful for user id=%d", user.id)
    return TokenResponse(access_token=token)


# PUBLIC_INTERFACE
@router.get(
    "/me",
    response_model=UserOut,
    summary="Get current user profile",
    description="Returns the profile of the currently authenticated user.",
)
def get_profile(current_user: User = Depends(get_current_user)):
    """Return the current authenticated user's profile.

    Args:
        current_user: The authenticated user (injected via dependency).

    Returns:
        User profile data.
    """
    return current_user


# PUBLIC_INTERFACE
@router.put(
    "/me",
    response_model=UserOut,
    summary="Update current user profile",
    description="Updates display_name, bio, or avatar_url for the authenticated user.",
)
def update_profile(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update the current user's profile fields.

    Args:
        payload: Fields to update.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        Updated user profile.
    """
    if payload.display_name is not None:
        current_user.display_name = payload.display_name
    if payload.bio is not None:
        current_user.bio = payload.bio
    if payload.avatar_url is not None:
        current_user.avatar_url = payload.avatar_url
    current_user.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(current_user)
    logger.info("Profile updated for user id=%d", current_user.id)
    return current_user
