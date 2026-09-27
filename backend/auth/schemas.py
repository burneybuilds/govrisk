from pydantic import BaseModel, EmailStr, Field
from typing import Annotated, Optional
from datetime import datetime
from pydantic.functional_validators import AfterValidator

# bcrypt hashes at most 72 bytes of input and raises ValueError beyond that.
# Enforcing the limit here turns an unhandled ValueError (HTTP 500) into a
# normal 422 validation response.
BCRYPT_MAX_PASSWORD_BYTES = 72


def _password_within_bcrypt_limit(value: str) -> str:
    if len(value.encode("utf-8")) > BCRYPT_MAX_PASSWORD_BYTES:
        raise ValueError(
            "password must be at most "
            f"{BCRYPT_MAX_PASSWORD_BYTES} bytes when UTF-8 encoded"
        )
    return value


Password = Annotated[str, AfterValidator(_password_within_bcrypt_limit)]


class UserRegister(BaseModel):
    fullName: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: Password = Field(..., min_length=6)
    department: Optional[str] = None
    designation: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    userId: str
    fullName: str
    email: str
    role: str
    department: Optional[str] = None
    designation: Optional[str] = None
    isActive: bool
    createdAt: str
    updatedAt: str
    lastLogin: Optional[str] = None


class AuthResponse(BaseModel):
    accessToken: str
    refreshToken: str
    user: UserResponse


class TokenRefresh(BaseModel):
    refreshToken: str


class ProfileUpdate(BaseModel):
    fullName: Optional[str] = Field(None, min_length=1, max_length=100)
    department: Optional[str] = None
    designation: Optional[str] = None


class PasswordChange(BaseModel):
    currentPassword: str
    newPassword: Password = Field(..., min_length=6)


class UserRoleUpdate(BaseModel):
    role: str = Field(..., pattern="^(admin|officer|analyst|viewer)$")


class UserStatusUpdate(BaseModel):
    isActive: bool


class AdminUserCreate(BaseModel):
    fullName: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    role: str = Field(..., pattern="^(admin|officer|analyst|viewer)$")
    department: Optional[str] = None
    designation: Optional[str] = None
    temporaryPassword: Password = Field(..., min_length=6)
    isActive: bool = True


class AdminUserUpdate(BaseModel):
    fullName: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    department: Optional[str] = None
    designation: Optional[str] = None


class PasswordResetResponse(BaseModel):
    message: str
    temporaryPassword: str