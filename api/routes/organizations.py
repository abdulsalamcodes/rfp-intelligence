"""
Organizations Router

API endpoints for organization management.
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from database.models import Organization, OrganizationMember, User
from api.auth.dependencies import get_current_active_user, get_current_org, require_roles


router = APIRouter(prefix="/organizations", tags=["Organizations"])


# ============================================================================
# Request/Response Models
# ============================================================================

class OrganizationCreate(BaseModel):
    """Create organization request."""
    name: str
    slug: Optional[str] = None


class OrganizationUpdate(BaseModel):
    """Update organization request."""
    name: Optional[str] = None
    settings: Optional[dict] = None


class OrganizationResponse(BaseModel):
    """Organization response."""
    id: str
    name: str
    slug: str
    settings: dict
    member_count: int = 0
    
    class Config:
        from_attributes = True


class MemberResponse(BaseModel):
    """Organization member response."""
    id: str
    user_id: str
    email: str
    full_name: Optional[str]
    role: str
    
    class Config:
        from_attributes = True


class AddMemberRequest(BaseModel):
    """Add member request."""
    email: EmailStr
    role: str = "member"


class UpdateMemberRequest(BaseModel):
    """Update member role request."""
    role: str


# ============================================================================
# Organization Endpoints
# ============================================================================

@router.get("", response_model=List[OrganizationResponse])
async def list_organizations(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List all organizations the current user belongs to."""
    result = await db.execute(
        select(Organization, OrganizationMember.role)
        .join(OrganizationMember)
        .where(OrganizationMember.user_id == current_user.id)
    )
    orgs = result.all()
    
    response = []
    for org, role in orgs:
        # Count members
        count_result = await db.execute(
            select(OrganizationMember)
            .where(OrganizationMember.organization_id == org.id)
        )
        member_count = len(count_result.scalars().all())
        
        response.append(OrganizationResponse(
            id=str(org.id),
            name=org.name,
            slug=org.slug,
            settings=org.settings or {},
            member_count=member_count
        ))
    
    return response


@router.post("", response_model=OrganizationResponse)
async def create_organization(
    data: OrganizationCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new organization."""
    # Generate slug if not provided
    slug = data.slug or data.name.lower().replace(" ", "-").replace("'", "")[:50]
    slug = f"{slug}-{str(uuid.uuid4())[:8]}"
    
    # Check slug uniqueness
    result = await db.execute(
        select(Organization).where(Organization.slug == slug)
    )
    if result.scalar_one_or_none():
        slug = f"{slug}-{str(uuid.uuid4())[:4]}"
    
    # Create organization
    org = Organization(
        name=data.name,
        slug=slug,
        settings={}
    )
    db.add(org)
    await db.flush()
    
    # Add current user as owner
    member = OrganizationMember(
        organization_id=org.id,
        user_id=current_user.id,
        role="owner"
    )
    db.add(member)
    await db.commit()
    
    return OrganizationResponse(
        id=str(org.id),
        name=org.name,
        slug=org.slug,
        settings=org.settings or {},
        member_count=1
    )


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get organization details."""
    # Verify membership
    result = await db.execute(
        select(Organization, OrganizationMember.role)
        .join(OrganizationMember)
        .where(
            Organization.id == uuid.UUID(org_id),
            OrganizationMember.user_id == current_user.id
        )
    )
    row = result.one_or_none()
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found or access denied"
        )
    
    org, role = row
    
    # Count members
    count_result = await db.execute(
        select(OrganizationMember)
        .where(OrganizationMember.organization_id == org.id)
    )
    member_count = len(count_result.scalars().all())
    
    return OrganizationResponse(
        id=str(org.id),
        name=org.name,
        slug=org.slug,
        settings=org.settings or {},
        member_count=member_count
    )


@router.patch("/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: str,
    data: OrganizationUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update organization (admin/owner only)."""
    # Verify admin/owner role
    result = await db.execute(
        select(Organization, OrganizationMember.role)
        .join(OrganizationMember)
        .where(
            Organization.id == uuid.UUID(org_id),
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.role.in_(["owner", "admin"])
        )
    )
    row = result.one_or_none()
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this organization"
        )
    
    org, role = row
    
    # Update fields
    if data.name:
        org.name = data.name
    if data.settings:
        org.settings = {**(org.settings or {}), **data.settings}
    
    await db.commit()
    await db.refresh(org)
    
    return OrganizationResponse(
        id=str(org.id),
        name=org.name,
        slug=org.slug,
        settings=org.settings or {},
        member_count=0  # Not recounting for update
    )


# ============================================================================
# Member Management
# ============================================================================

@router.get("/{org_id}/members", response_model=List[MemberResponse])
async def list_members(
    org_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List organization members."""
    # Verify membership
    result = await db.execute(
        select(OrganizationMember)
        .where(
            OrganizationMember.organization_id == uuid.UUID(org_id),
            OrganizationMember.user_id == current_user.id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization"
        )
    
    # Get all members with user info
    result = await db.execute(
        select(OrganizationMember, User)
        .join(User)
        .where(OrganizationMember.organization_id == uuid.UUID(org_id))
    )
    members = result.all()
    
    return [
        MemberResponse(
            id=str(member.id),
            user_id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            role=member.role
        )
        for member, user in members
    ]


@router.post("/{org_id}/members", response_model=MemberResponse)
async def add_member(
    org_id: str,
    data: AddMemberRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Add a member to the organization (admin/owner only)."""
    # Verify admin/owner role
    result = await db.execute(
        select(OrganizationMember.role)
        .where(
            OrganizationMember.organization_id == uuid.UUID(org_id),
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.role.in_(["owner", "admin"])
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to add members"
        )
    
    # Find user by email
    result = await db.execute(
        select(User).where(User.email == data.email.lower())
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found. They must register first."
        )
    
    # Check if already a member
    result = await db.execute(
        select(OrganizationMember)
        .where(
            OrganizationMember.organization_id == uuid.UUID(org_id),
            OrganizationMember.user_id == user.id
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member"
        )
    
    # Add member
    member = OrganizationMember(
        organization_id=uuid.UUID(org_id),
        user_id=user.id,
        role=data.role
    )
    db.add(member)
    await db.commit()
    
    return MemberResponse(
        id=str(member.id),
        user_id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=member.role
    )


@router.patch("/{org_id}/members/{user_id}", response_model=MemberResponse)
async def update_member_role(
    org_id: str,
    user_id: str,
    data: UpdateMemberRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a member's role (owner only)."""
    # Only owners can change roles
    result = await db.execute(
        select(OrganizationMember.role)
        .where(
            OrganizationMember.organization_id == uuid.UUID(org_id),
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.role == "owner"
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners can change member roles"
        )
    
    # Get the member
    result = await db.execute(
        select(OrganizationMember, User)
        .join(User)
        .where(
            OrganizationMember.organization_id == uuid.UUID(org_id),
            OrganizationMember.user_id == uuid.UUID(user_id)
        )
    )
    row = result.one_or_none()
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    
    member, user = row
    member.role = data.role
    await db.commit()
    
    return MemberResponse(
        id=str(member.id),
        user_id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=member.role
    )


@router.delete("/{org_id}/members/{user_id}")
async def remove_member(
    org_id: str,
    user_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove a member from the organization (admin/owner only)."""
    # Verify admin/owner role
    result = await db.execute(
        select(OrganizationMember.role)
        .where(
            OrganizationMember.organization_id == uuid.UUID(org_id),
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.role.in_(["owner", "admin"])
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to remove members"
        )
    
    # Can't remove yourself if you're the only owner
    if str(current_user.id) == user_id:
        result = await db.execute(
            select(OrganizationMember)
            .where(
                OrganizationMember.organization_id == uuid.UUID(org_id),
                OrganizationMember.role == "owner"
            )
        )
        owners = result.scalars().all()
        if len(owners) <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the only owner. Transfer ownership first."
            )
    
    # Remove member
    await db.execute(
        delete(OrganizationMember)
        .where(
            OrganizationMember.organization_id == uuid.UUID(org_id),
            OrganizationMember.user_id == uuid.UUID(user_id)
        )
    )
    await db.commit()
    
    return {"message": "Member removed"}
