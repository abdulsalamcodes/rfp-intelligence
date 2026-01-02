"""
Billing Router (v1)

API endpoints for subscription and usage management.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from database.models import Organization
from api.auth.dependencies import get_current_active_user, get_current_org
from services.billing import get_usage_summary


router = APIRouter(prefix="/billing", tags=["Billing"])


# ============================================================================
# Response Models
# ============================================================================

class PlanInfo(BaseModel):
    """Plan information."""
    name: str
    display_name: str
    rfp_limit: Optional[int]
    user_limit: Optional[int]


class UsageSummaryResponse(BaseModel):
    """Usage summary response."""
    has_subscription: bool
    plan: Optional[PlanInfo] = None
    subscription_status: Optional[str] = None
    billing_cycle: Optional[str] = None
    current_period_end: Optional[str] = None
    rfps_used: int
    rfps_limit: Optional[int]
    rfps_remaining: Optional[int]


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/usage", response_model=UsageSummaryResponse)
async def get_usage(
    current_org: Organization = Depends(get_current_org)
):
    """Get current usage summary for the organization."""
    summary = await get_usage_summary(str(current_org.id))
    
    plan_info = None
    if summary.get("plan"):
        plan_info = PlanInfo(**summary["plan"])
    
    return UsageSummaryResponse(
        has_subscription=summary.get("has_subscription", False),
        plan=plan_info,
        subscription_status=summary.get("subscription_status"),
        billing_cycle=summary.get("billing_cycle"),
        current_period_end=summary.get("current_period_end"),
        rfps_used=summary.get("rfps_used", 0),
        rfps_limit=summary.get("rfps_limit"),
        rfps_remaining=summary.get("rfps_remaining")
    )


@router.get("/can-create-rfp")
async def check_can_create(
    current_org: Organization = Depends(get_current_org)
):
    """Check if organization can create a new RFP."""
    from services.billing import check_can_create_rfp
    
    can_create, message = await check_can_create_rfp(str(current_org.id))
    
    return {
        "can_create": can_create,
        "message": message
    }
