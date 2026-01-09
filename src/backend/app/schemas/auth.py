"""Pydantic schemas for authentication endpoints."""

from pydantic import BaseModel, EmailStr, field_validator
from typing import Literal
from datetime import datetime


class SignupRequest(BaseModel):
    """Request schema for user signup."""

    email: EmailStr
    password: str
    confirm_password: str
    first_name: str | None = None
    last_name: str | None = None
    native_language: str = "es"

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v, info):
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Passwords do not match")
        return v


class LoginRequest(BaseModel):
    """Request schema for user login."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Response schema for login/refresh endpoints."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshRequest(BaseModel):
    """Request schema for token refresh."""

    refresh_token: str


class PasswordResetRequest(BaseModel):
    """Request schema for password reset request."""

    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Request schema for password reset confirmation."""

    token: str
    new_password: str
    confirm_password: str

    @field_validator("new_password")
    @classmethod
    def password_min_length(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v, info):
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("Passwords do not match")
        return v


class UserResponse(BaseModel):
    """Response schema for user info."""

    id: str
    email: str
    display_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    auth_provider: str
    is_approved: bool
    approval_status: str
    roles: list[str] = []

    class Config:
        from_attributes = True


class AuthConfigResponse(BaseModel):
    """Response schema for auth configuration."""

    auth_mode: Literal["local", "azure_ad", "both"]
    azure_ad_client_id: str | None = None
    azure_ad_tenant_id: str | None = None


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str


# Admin endpoint schemas
class UserListItem(BaseModel):
    """Schema for user in admin list."""

    id: str
    email: str
    display_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    auth_provider: str
    is_approved: bool
    approval_status: str
    roles: list[str] = []
    created_at: datetime

    class Config:
        from_attributes = True


class ApproveUserRequest(BaseModel):
    """Request schema for approving/rejecting a user."""

    user_id: str
    approved: bool  # True to approve, False to reject


class AssignRoleRequest(BaseModel):
    """Request schema for assigning a role."""

    user_id: str
    role: Literal["admin", "teacher", "student"]
