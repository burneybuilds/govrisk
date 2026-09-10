from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session
from auth.database import get_auth_db
from auth.models import User
from auth.schemas import (
    UserResponse, ProfileUpdate, PasswordChange,
    UserRoleUpdate, UserStatusUpdate, AdminUserCreate, AdminUserUpdate,
    PasswordResetResponse,
)
from auth.security import hash_password, verify_password, generate_id
from auth.dependencies import get_current_user, require_admin
from auth.serializers import user_to_response
from auth.audit import log_audit, next_user_id, ACTIONS

router = APIRouter(prefix="/api/users", tags=["users"])


def _resolve_user(db: Session, identifier: str) -> User:
    user = db.query(User).filter(
        or_(User.user_id == identifier, User.id == identifier)
    ).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.get("/me", response_model=UserResponse)
def get_profile(user: User = Depends(get_current_user)):
    return user_to_response(user)


@router.put("/me", response_model=UserResponse)
def update_profile(
    data: ProfileUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_auth_db),
):
    if data.fullName is not None:
        user.full_name = data.fullName
    if data.department is not None:
        user.department = data.department
    if data.designation is not None:
        user.designation = data.designation
    db.commit()
    db.refresh(user)
    return user_to_response(user)


@router.put("/me/password")
def change_password(
    data: PasswordChange,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_auth_db),
):
    if not verify_password(data.currentPassword, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    user.password_hash = hash_password(data.newPassword)
    db.commit()
    log_audit(db, user, ACTIONS["PASSWORD_CHANGED"], target_user_id=user.user_id)
    db.commit()
    return {"message": "Password changed successfully"}


@router.get("/stats")
def get_users_stats(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_auth_db),
):
    total = db.query(User).count()
    active = db.query(User).filter(User.is_active == True).count()
    inactive = db.query(User).filter(User.is_active == False).count()
    admins = db.query(User).filter(User.role == "admin").count()
    officers = db.query(User).filter(User.role == "officer").count()
    analysts = db.query(User).filter(User.role == "analyst").count()
    viewers = db.query(User).filter(User.role == "viewer").count()
    return {
        "total": total,
        "active": active,
        "inactive": inactive,
        "admins": admins,
        "officers": officers,
        "analysts": analysts,
        "viewers": viewers,
    }


@router.get("")
def list_users(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_auth_db),
    search: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    query = db.query(User)

    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                User.full_name.ilike(like),
                User.email.ilike(like),
                User.user_id.ilike(like),
                User.designation.ilike(like),
            )
        )
    if role:
        query = query.filter(User.role == role)
    if status:
        if status == "active":
            query = query.filter(User.is_active == True)
        elif status == "inactive":
            query = query.filter(User.is_active == False)
    if department:
        query = query.filter(User.department.ilike(f"%{department}%"))

    total = query.count()
    total_pages = (total + limit - 1) // limit if total else 0
    users = query.order_by(User.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

    return {
        "items": [user_to_response(u) for u in users],
        "page": page,
        "limit": limit,
        "total": total,
        "totalPages": total_pages,
    }


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    data: AdminUserCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_auth_db),
):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists")

    user = User(
        id=generate_id(),
        user_id=next_user_id(db),
        full_name=data.fullName,
        email=data.email,
        password_hash=hash_password(data.temporaryPassword),
        role=data.role,
        department=data.department,
        designation=data.designation,
        is_active=data.isActive,
    )
    db.add(user)
    db.flush()
    log_audit(
        db,
        admin,
        ACTIONS["USER_CREATED"],
        target_user_id=user.user_id,
        details=f"Created new {data.role} account",
    )
    db.commit()
    db.refresh(user)
    return user_to_response(user)


@router.get("/{identifier}", response_model=UserResponse)
def get_user(
    identifier: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_auth_db),
):
    return user_to_response(_resolve_user(db, identifier))


@router.put("/{identifier}", response_model=UserResponse)
def admin_update_user(
    identifier: str,
    data: AdminUserUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_auth_db),
):
    user = _resolve_user(db, identifier)
    if data.fullName is not None:
        user.full_name = data.fullName
    if data.email is not None and data.email != user.email:
        if db.query(User).filter(User.email == data.email, User.id != user.id).first():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists")
        user.email = data.email
    if data.department is not None:
        user.department = data.department
    if data.designation is not None:
        user.designation = data.designation
    db.flush()
    log_audit(
        db,
        admin,
        ACTIONS["USER_UPDATED"],
        target_user_id=user.user_id,
        details="Updated user profile information",
    )
    db.commit()
    db.refresh(user)
    return user_to_response(user)


@router.patch("/{identifier}/role", response_model=UserResponse)
def update_user_role(
    identifier: str,
    data: UserRoleUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_auth_db),
):
    user = _resolve_user(db, identifier)
    if user.id == admin.id and data.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own admin role",
        )
    if user.role == "admin" and data.role != "admin":
        active_admins = db.query(User).filter(
            User.role == "admin", User.is_active == True, User.id != user.id
        ).count()
        if active_admins == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the last active admin role",
            )
    old_role = user.role
    user.role = data.role
    db.flush()
    log_audit(
        db,
        admin,
        ACTIONS["ROLE_CHANGED"],
        target_user_id=user.user_id,
        details=f"Changed role from {old_role} to {data.role}",
    )
    db.commit()
    db.refresh(user)
    return user_to_response(user)


@router.patch("/{identifier}/status", response_model=UserResponse)
def update_user_status(
    identifier: str,
    data: UserStatusUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_auth_db),
):
    user = _resolve_user(db, identifier)
    if user.id == admin.id and not data.isActive:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account",
        )
    if user.role == "admin" and not data.isActive:
        active_admins = db.query(User).filter(
            User.role == "admin", User.is_active == True, User.id != user.id
        ).count()
        if active_admins == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate the last active admin",
            )
    user.is_active = data.isActive
    db.flush()
    log_audit(
        db,
        admin,
        ACTIONS["USER_ACTIVATED"] if data.isActive else ACTIONS["USER_DEACTIVATED"],
        target_user_id=user.user_id,
        details="Activated account" if data.isActive else "Deactivated account",
    )
    db.commit()
    db.refresh(user)
    return user_to_response(user)


@router.post("/{identifier}/reset-password", response_model=PasswordResetResponse)
def reset_user_password(
    identifier: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_auth_db),
):
    user = _resolve_user(db, identifier)
    temp_password = f"GovRisk@{_random_temp_suffix()}"
    user.password_hash = hash_password(temp_password)
    db.flush()
    log_audit(
        db,
        admin,
        ACTIONS["PASSWORD_RESET"],
        target_user_id=user.user_id,
        details="Generated temporary password",
    )
    db.commit()
    return PasswordResetResponse(
        message="Temporary password generated",
        temporaryPassword=temp_password,
    )


def _random_temp_suffix() -> str:
    import random
    import string
    digits = "".join(random.choices(string.digits, k=4))
    return f"{digits}"