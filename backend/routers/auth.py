from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from auth.database import get_auth_db
from auth.models import User
from auth.schemas import (
    UserRegister, UserLogin, UserResponse, AuthResponse,
    TokenRefresh,
)
from auth.security import (
    generate_id, hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
)
from auth.dependencies import get_current_user
from auth.serializers import user_to_response
from auth.audit import log_audit, next_user_id, ACTIONS

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(data: UserRegister, db: Session = Depends(get_auth_db)):
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    user = User(
        id=generate_id(),
        user_id=next_user_id(db),
        full_name=data.fullName,
        email=data.email,
        password_hash=hash_password(data.password),
        role="viewer",
        department=data.department,
        designation=data.designation,
        is_active=True,
    )
    db.add(user)
    db.flush()
    log_audit(
        db,
        user,
        ACTIONS["REGISTERED"],
        target_user_id=user.user_id,
        details="Self-registered account",
    )
    db.commit()
    db.refresh(user)

    access_token = create_access_token(user.id, user.role)
    refresh_token = create_refresh_token(user.id)

    return AuthResponse(
        accessToken=access_token,
        refreshToken=refresh_token,
        user=user_to_response(user),
    )


@router.post("/login", response_model=AuthResponse)
def login(data: UserLogin, db: Session = Depends(get_auth_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        if user:
            log_audit(
                db,
                user,
                ACTIONS["LOGIN_FAILED"],
                target_user_id=user.user_id,
                details="Failed login attempt (invalid password)",
            )
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        log_audit(
            db,
            user,
            ACTIONS["LOGIN_FAILED"],
            target_user_id=user.user_id,
            details="Login rejected: account deactivated",
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    user.last_login = datetime.now(timezone.utc)
    log_audit(db, user, ACTIONS["LOGIN_SUCCESS"], target_user_id=user.user_id, details="Successful login")
    db.commit()

    access_token = create_access_token(user.id, user.role)
    refresh_token = create_refresh_token(user.id)

    return AuthResponse(
        accessToken=access_token,
        refreshToken=refresh_token,
        user=user_to_response(user),
    )


@router.post("/refresh", response_model=AuthResponse)
def refresh_token(data: TokenRefresh, db: Session = Depends(get_auth_db)):
    payload = decode_token(data.refreshToken)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    access_token = create_access_token(user.id, user.role)
    refresh_token_new = create_refresh_token(user.id)

    return AuthResponse(
        accessToken=access_token,
        refreshToken=refresh_token_new,
        user=user_to_response(user),
    )


@router.post("/logout")
def logout(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_auth_db),
):
    log_audit(db, user, ACTIONS["LOGOUT"], target_user_id=user.user_id, details="Logged out")
    db.commit()
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
def get_me(user: User = Depends(get_current_user)):
    return user_to_response(user)