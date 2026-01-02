"""
Authentication Router

Endpoints for user registration, login, and token management.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from database.models import User, Organization, OrganizationMember, Plan, Subscription
from api.auth.jwt import create_access_token, create_refresh_token, verify_token, TokenError
from api.auth.password import hash_password, verify_password
from api.auth.dependencies import get_current_active_user


router = APIRouter(prefix="/auth", tags=["Authentication"])


# ============================================================================
# Request/Response Models
# ============================================================================

class UserRegister(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    organization_name: Optional[str] = None


class UserLogin(BaseModel):
    """User login request (alternative to OAuth2 form)."""
    email: EmailStr
    password: str
    org_id: Optional[str] = None


class TokenResponse(BaseModel):
    """Authentication token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenRefresh(BaseModel):
    """Token refresh request."""
    refresh_token: str


class UserResponse(BaseModel):
    """User info response."""
    id: str
    email: str
    full_name: Optional[str]
    is_active: bool
    organizations: list[dict]

    class Config:
        from_attributes = True


# ============================================================================
# Auth Endpoints
# ============================================================================

@router.post("/register", response_model=TokenResponse)
async def register(
    data: UserRegister,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user and create their organization.
    
    Returns access and refresh tokens on success.
    """
    # Check if email already exists
    result = await db.execute(
        select(User).where(User.email == data.email.lower())
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    user = User(
        email=data.email.lower(),
        password_hash=hash_password(data.password),
        full_name=data.full_name
    )
    db.add(user)
    await db.flush()  # Get user ID
    
    # Create organization
    org_name = data.organization_name or f"{data.full_name or data.email.split('@')[0]}'s Org"
    org_slug = org_name.lower().replace(" ", "-").replace("'", "")[:50] + f"-{str(user.id)[:8]}"
    
    org = Organization(
        name=org_name,
        slug=org_slug
    )
    db.add(org)
    await db.flush()
    
    # Add user as org owner
    member = OrganizationMember(
        organization_id=org.id,
        user_id=user.id,
        role="owner"
    )
    db.add(member)
    
    # Get or create free plan
    result = await db.execute(
        select(Plan).where(Plan.name == "free")
    )
    free_plan = result.scalar_one_or_none()
    
    if free_plan is None:
        # Create default free plan
        free_plan = Plan(
            name="free",
            display_name="Free",
            price_monthly=0,
            rfp_limit=2,
            user_limit=1,
            history_days=7,
            features=["basic_agents"]
        )
        db.add(free_plan)
        await db.flush()
    
    # Create subscription
    subscription = Subscription(
        organization_id=org.id,
        plan_id=free_plan.id,
        status="active",
        current_period_start=datetime.now(timezone.utc)
    )
    db.add(subscription)
    
    await db.commit()
    
    # Generate tokens
    token_data = {"sub": str(user.id), "org_id": str(org.id)}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    from config.settings import settings
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.jwt_expire_minutes * 60
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Login with email and password (OAuth2 compatible).
    
    Returns access and refresh tokens on success.
    """
    # Find user
    result = await db.execute(
        select(User).where(User.email == form_data.username.lower())
    )
    user = result.scalar_one_or_none()
    
    if user is None or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )
    
    # Get user's first organization
    result = await db.execute(
        select(Organization)
        .join(OrganizationMember)
        .where(OrganizationMember.user_id == user.id)
        .limit(1)
    )
    org = result.scalar_one_or_none()
    
    org_id = str(org.id) if org else None
    
    # Generate tokens
    token_data = {"sub": str(user.id), "org_id": org_id}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    from config.settings import settings
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.jwt_expire_minutes * 60
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    data: TokenRefresh,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh an access token using a refresh token.
    """
    try:
        payload = verify_token(data.refresh_token, "refresh")
        user_id = payload.get("sub")
        org_id = payload.get("org_id")
        
        # Verify user still exists and is active
        result = await db.execute(
            select(User).where(User.id == uuid.UUID(user_id))
        )
        user = result.scalar_one_or_none()
        
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User no longer valid"
            )
        
        # Generate new tokens
        token_data = {"sub": user_id, "org_id": org_id}
        access_token = create_access_token(token_data)
        new_refresh_token = create_refresh_token(token_data)
        
        from config.settings import settings
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_in=settings.jwt_expire_minutes * 60
        )
        
    except TokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user info and their organizations.
    """
    # Get user's organizations
    result = await db.execute(
        select(Organization, OrganizationMember.role)
        .join(OrganizationMember)
        .where(OrganizationMember.user_id == current_user.id)
    )
    orgs = [
        {"id": str(org.id), "name": org.name, "slug": org.slug, "role": role}
        for org, role in result.all()
    ]
    
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        organizations=orgs
    )


@router.post("/switch-org")
async def switch_organization(
    org_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate new tokens for a different organization.
    
    User must be a member of the target organization.
    """
    # Verify membership
    result = await db.execute(
        select(OrganizationMember)
        .where(
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.organization_id == uuid.UUID(org_id)
        )
    )
    member = result.scalar_one_or_none()
    
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization"
        )
    
    # Generate new tokens with new org context
    token_data = {"sub": str(current_user.id), "org_id": org_id}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    from config.settings import settings
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.jwt_expire_minutes * 60
    )
