# src/backend/app/routers/auth.py
"""Authentication router for local JWT and Azure AD OAuth."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.middleware.auth import CurrentUser, AdminUser
from app.models.user import User
from app.models.auth import UserRole, Role
from app.services.auth_service import AuthService
from app.services.email_service import get_email_service
from app.schemas.auth import (
    SignupRequest,
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
    UserResponse,
    AuthConfigResponse,
    MessageResponse,
    UserListItem,
    ApproveUserRequest,
    AssignRoleRequest,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/config", response_model=AuthConfigResponse)
async def get_auth_config():
    """Public endpoint for frontend to determine auth mode."""
    settings = get_settings()
    return AuthConfigResponse(
        auth_mode=settings.auth_mode,
        azure_ad_client_id=(
            settings.azure_ad_client_id
            if settings.auth_mode in ["azure_ad", "both"]
            else None
        ),
        azure_ad_tenant_id=(
            settings.azure_ad_tenant_id
            if settings.auth_mode in ["azure_ad", "both"]
            else None
        ),
    )


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(request: SignupRequest, db: AsyncSession = Depends(get_db)):
    """Create a new user account (pending approval)."""
    # Check if email already exists
    stmt = select(User).where(User.email == request.email)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Create new user
    auth_service = AuthService(db)
    password_hash = auth_service.hash_password(request.password)

    # Generate display name from first/last name if provided
    display_name = None
    if request.first_name or request.last_name:
        parts = [p for p in [request.first_name, request.last_name] if p]
        display_name = " ".join(parts)

    user = User(
        email=request.email,
        password_hash=password_hash,
        first_name=request.first_name,
        last_name=request.last_name,
        display_name=display_name,
        native_language=request.native_language,
        auth_provider="local",
        is_approved=False,
        approval_status="pending",
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Assign default student role
    stmt = select(Role).where(Role.name == "student")
    result = await db.execute(stmt)
    student_role = result.scalar_one_or_none()

    if student_role:
        user_role = UserRole(user_id=user.id, role_id=student_role.id)
        db.add(user_role)
        await db.commit()

    return UserResponse(
        id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        first_name=user.first_name,
        last_name=user.last_name,
        auth_provider=user.auth_provider,
        is_approved=user.is_approved,
        approval_status=user.approval_status,
        roles=["student"],
    )


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate user and return JWT tokens."""
    # Find user by email
    stmt = select(User).where(User.email == request.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Verify password
    auth_service = AuthService(db)
    if not user.password_hash or not auth_service.verify_password(
        request.password, user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Check if approved
    if not user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account pending approval",
        )

    # Get user roles
    stmt = (
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user.id)
    )
    result = await db.execute(stmt)
    roles = [r[0] for r in result.all()]

    # Generate tokens
    settings = get_settings()
    access_token = auth_service.create_access_token(user.id, roles)
    refresh_token = await auth_service.create_refresh_token(user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Exchange refresh token for new tokens."""
    auth_service = AuthService(db)

    # Verify refresh token
    token_record = await auth_service.verify_refresh_token(request.refresh_token)
    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Revoke old refresh token (rotation)
    await auth_service.revoke_refresh_token(token_record.id)

    # Get user and roles
    stmt = select(User).where(User.id == token_record.user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or not approved",
        )

    # Get roles
    stmt = (
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user.id)
    )
    result = await db.execute(stmt)
    roles = [r[0] for r in result.all()]

    # Generate new tokens
    settings = get_settings()
    access_token = auth_service.create_access_token(user.id, roles)
    new_refresh_token = await auth_service.create_refresh_token(user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.post("/password-reset/request", response_model=MessageResponse)
async def request_password_reset(
    request: PasswordResetRequest, db: AsyncSession = Depends(get_db)
):
    """Request password reset email.

    Always returns 200 to prevent email enumeration.
    """
    # Find user by email
    stmt = select(User).where(User.email == request.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user and user.auth_provider == "local":
        # Create reset token
        auth_service = AuthService(db)
        token = await auth_service.create_password_reset_token(user.id)

        # Send email
        settings = get_settings()
        reset_link = f"{settings.azure_ad_redirect_uri.rsplit('/', 1)[0]}/reset-password?token={token}"

        email_service = get_email_service()
        await email_service.send_password_reset(
            to_email=user.email,
            reset_link=reset_link,
            display_name=user.display_name,
        )

    # Always return success (anti-enumeration)
    return MessageResponse(
        message="If this email is associated with an account, you'll receive a reset link."
    )


@router.post("/password-reset/confirm", response_model=MessageResponse)
async def confirm_password_reset(
    request: PasswordResetConfirm, db: AsyncSession = Depends(get_db)
):
    """Reset password using token."""
    auth_service = AuthService(db)

    # Verify token
    token_record = await auth_service.verify_password_reset_token(request.token)
    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    # Get user
    stmt = select(User).where(User.id == token_record.user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found",
        )

    # Update password
    user.password_hash = auth_service.hash_password(request.new_password)
    await db.commit()

    # Mark token as used
    await auth_service.mark_password_reset_token_used(token_record.id)

    # Revoke all refresh tokens (logout everywhere)
    await auth_service.revoke_all_user_refresh_tokens(user.id)

    return MessageResponse(message="Password has been reset successfully")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: CurrentUser, db: AsyncSession = Depends(get_db)
):
    """Get current authenticated user info."""
    # Get roles
    stmt = (
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == current_user.id)
    )
    result = await db.execute(stmt)
    roles = [r[0] for r in result.all()]

    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        display_name=current_user.display_name,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        auth_provider=current_user.auth_provider,
        is_approved=current_user.is_approved,
        approval_status=current_user.approval_status,
        roles=roles,
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: RefreshRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Revoke refresh token (logout)."""
    auth_service = AuthService(db)

    # Verify and revoke the refresh token
    token_record = await auth_service.verify_refresh_token(request.refresh_token)
    if token_record and token_record.user_id == current_user.id:
        await auth_service.revoke_refresh_token(token_record.id)

    return MessageResponse(message="Logged out successfully")


# ============================================================================
# Admin Endpoints
# ============================================================================


@router.get("/admin/users", response_model=list[UserListItem])
async def list_users(
    admin_user: AdminUser,
    db: AsyncSession = Depends(get_db),
    status: str | None = None,
):
    """List all users (admin only).

    Args:
        status: Optional filter by approval_status (pending, approved, rejected)
    """
    stmt = select(User)

    if status:
        stmt = stmt.where(User.approval_status == status)

    stmt = stmt.order_by(User.created_at.desc())
    result = await db.execute(stmt)
    users = result.scalars().all()

    # Get roles for each user
    user_list = []
    for user in users:
        roles_stmt = (
            select(Role.name)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user.id)
        )
        roles_result = await db.execute(roles_stmt)
        roles = [r[0] for r in roles_result.all()]

        user_list.append(
            UserListItem(
                id=str(user.id),
                email=user.email,
                display_name=user.display_name,
                first_name=user.first_name,
                last_name=user.last_name,
                auth_provider=user.auth_provider or "local",
                is_approved=user.is_approved,
                approval_status=user.approval_status or "pending",
                roles=roles,
                created_at=user.created_at,
            )
        )

    return user_list


@router.post("/admin/users/approve", response_model=UserResponse)
async def approve_user(
    request: ApproveUserRequest,
    admin_user: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Approve or reject a user (admin only)."""
    from datetime import datetime

    # Find the user
    stmt = select(User).where(User.id == request.user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Update approval status
    user.is_approved = request.approved
    user.approval_status = "approved" if request.approved else "rejected"
    user.approved_at = datetime.utcnow()
    user.approved_by = admin_user.id

    await db.commit()
    await db.refresh(user)

    # Get roles
    roles_stmt = (
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user.id)
    )
    roles_result = await db.execute(roles_stmt)
    roles = [r[0] for r in roles_result.all()]

    return UserResponse(
        id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        first_name=user.first_name,
        last_name=user.last_name,
        auth_provider=user.auth_provider or "local",
        is_approved=user.is_approved,
        approval_status=user.approval_status,
        roles=roles,
    )


@router.post("/admin/users/role", response_model=UserResponse)
async def assign_role(
    request: AssignRoleRequest,
    admin_user: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Assign a role to a user (admin only)."""
    # Find the user
    stmt = select(User).where(User.id == request.user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Find the role
    role_stmt = select(Role).where(Role.name == request.role)
    role_result = await db.execute(role_stmt)
    role = role_result.scalar_one_or_none()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role '{request.role}' not found",
        )

    # Check if user already has this role
    existing_stmt = select(UserRole).where(
        UserRole.user_id == user.id,
        UserRole.role_id == role.id,
    )
    existing_result = await db.execute(existing_stmt)
    existing = existing_result.scalar_one_or_none()

    if not existing:
        # Assign the role
        user_role = UserRole(
            user_id=user.id,
            role_id=role.id,
            assigned_by=admin_user.id,
        )
        db.add(user_role)
        await db.commit()

    # Get all roles
    roles_stmt = (
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user.id)
    )
    roles_result = await db.execute(roles_stmt)
    roles = [r[0] for r in roles_result.all()]

    return UserResponse(
        id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        first_name=user.first_name,
        last_name=user.last_name,
        auth_provider=user.auth_provider or "local",
        is_approved=user.is_approved,
        approval_status=user.approval_status or "pending",
        roles=roles,
    )
