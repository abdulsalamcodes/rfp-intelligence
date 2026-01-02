"""
Authentication Dependencies

FastAPI dependencies for authentication and authorization.
"""

from typing import Optional, List, Callable
from functools import wraps
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.connection import get_db
from database.models import User, Organization, OrganizationMember
from api.auth.jwt import verify_token, TokenError


# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Get the current authenticated user from JWT token.
    
    Returns None if no token provided (for optional auth).
    Raises HTTPException if token is invalid.
    """
    if token is None:
        return None
    
    try:
        payload = verify_token(token, "access")
        user_id = payload.get("sub")
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Query user from database
        result = await db.execute(
            select(User).where(User.id == uuid.UUID(user_id))
        )
        user = result.scalar_one_or_none()
        
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        return user
        
    except TokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


async def get_current_active_user(
    current_user: Optional[User] = Depends(get_current_user)
) -> User:
    """
    Get the current user, requiring authentication.
    
    Raises HTTPException if user is not authenticated or inactive.
    """
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    return current_user


async def get_current_org(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Organization:
    """
    Get the current organization context.
    
    Uses org_id from token if present, otherwise gets user's first org.
    """
    org_id = None
    
    # Try to get org_id from token
    if token:
        try:
            payload = verify_token(token, "access")
            org_id = payload.get("org_id")
        except TokenError:
            pass
    
    if org_id:
        # Verify user is member of this org
        result = await db.execute(
            select(Organization)
            .join(OrganizationMember)
            .where(
                Organization.id == uuid.UUID(org_id),
                OrganizationMember.user_id == current_user.id
            )
        )
        org = result.scalar_one_or_none()
        
        if org is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this organization"
            )
        
        return org
    
    # Get user's first organization
    result = await db.execute(
        select(Organization)
        .join(OrganizationMember)
        .where(OrganizationMember.user_id == current_user.id)
        .limit(1)
    )
    org = result.scalar_one_or_none()
    
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has no organization"
        )
    
    return org


def require_roles(allowed_roles: List[str]) -> Callable:
    """
    Dependency factory for role-based access control.
    
    Usage:
        @router.delete("/users/{id}", dependencies=[Depends(require_roles(["owner", "admin"]))])
        async def delete_user(...):
            ...
    """
    async def role_checker(
        current_user: User = Depends(get_current_active_user),
        current_org: Organization = Depends(get_current_org),
        db: AsyncSession = Depends(get_db)
    ):
        # Superusers bypass role checks
        if current_user.is_superuser:
            return True
        
        # Get user's role in the org
        result = await db.execute(
            select(OrganizationMember.role)
            .where(
                OrganizationMember.user_id == current_user.id,
                OrganizationMember.organization_id == current_org.id
            )
        )
        member = result.scalar_one_or_none()
        
        if member is None or member not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of these roles: {', '.join(allowed_roles)}"
            )
        
        return True
    
    return role_checker


async def get_optional_org(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
) -> Optional[Organization]:
    """
    Get organization context if user is authenticated, None otherwise.
    
    Useful for endpoints that work differently for authenticated vs anonymous users.
    """
    if current_user is None:
        return None
    
    try:
        return await get_current_org(token, db, current_user)
    except HTTPException:
        return None
