"""
Billing Service

Usage tracking, plan enforcement, and subscription management.
"""

import uuid
from datetime import datetime, timezone, date
from dateutil.relativedelta import relativedelta
from typing import Optional, Tuple

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Plan, Subscription, Usage, Organization
from database.connection import get_db_context


class BillingError(Exception):
    """Billing-related error."""
    pass


class UsageLimitError(BillingError):
    """Usage limit exceeded error."""
    pass


async def get_plan(plan_id: str, db: AsyncSession) -> Optional[Plan]:
    """Get a plan by ID."""
    result = await db.execute(
        select(Plan).where(Plan.id == uuid.UUID(plan_id))
    )
    return result.scalar_one_or_none()


async def get_plan_by_name(name: str, db: AsyncSession) -> Optional[Plan]:
    """Get a plan by name."""
    result = await db.execute(
        select(Plan).where(Plan.name == name)
    )
    return result.scalar_one_or_none()


async def get_subscription(org_id: str, db: AsyncSession) -> Optional[Subscription]:
    """Get organization's subscription."""
    result = await db.execute(
        select(Subscription).where(
            Subscription.organization_id == uuid.UUID(org_id)
        )
    )
    return result.scalar_one_or_none()


async def get_current_usage(org_id: str, db: AsyncSession) -> Optional[Usage]:
    """Get organization's current billing period usage."""
    today = date.today()
    
    result = await db.execute(
        select(Usage).where(
            Usage.organization_id == uuid.UUID(org_id),
            Usage.period_start <= today,
            Usage.period_end >= today
        )
    )
    return result.scalar_one_or_none()


async def get_or_create_usage(org_id: str, db: AsyncSession) -> Usage:
    """Get or create usage record for current billing period."""
    usage = await get_current_usage(org_id, db)
    
    if usage:
        return usage
    
    # Create new usage record for this month
    today = date.today()
    period_start = today.replace(day=1)
    period_end = (period_start + relativedelta(months=1)) - relativedelta(days=1)
    
    # Get subscription to know the limit
    subscription = await get_subscription(org_id, db)
    rfp_limit = None
    
    if subscription:
        plan = await get_plan(str(subscription.plan_id), db)
        if plan:
            rfp_limit = plan.rfp_limit
    
    usage = Usage(
        organization_id=uuid.UUID(org_id),
        period_start=period_start,
        period_end=period_end,
        rfps_used=0,
        rfps_limit=rfp_limit,
        extra_credits_used=0
    )
    db.add(usage)
    await db.flush()
    
    return usage


async def check_can_create_rfp(org_id: str) -> Tuple[bool, str]:
    """
    Check if organization can create a new RFP.
    
    Args:
        org_id: Organization ID
        
    Returns:
        Tuple of (can_create, message)
    """
    async with get_db_context() as db:
        # Get subscription
        subscription = await get_subscription(org_id, db)
        
        if not subscription:
            return False, "No active subscription. Please contact support."
        
        if subscription.status != "active":
            return False, f"Subscription is {subscription.status}. Please update payment."
        
        # Get plan
        plan = await get_plan(str(subscription.plan_id), db)
        
        if not plan:
            return False, "Invalid subscription plan."
        
        # Unlimited plan
        if plan.rfp_limit is None:
            return True, "ok"
        
        # Get usage
        usage = await get_or_create_usage(org_id, db)
        
        # Calculate available RFPs
        # extra_credits_used tracks how many extra credits have been consumed
        # We'd need a separate query to count total purchased credits
        available = plan.rfp_limit - usage.rfps_used
        
        if available <= 0:
            return False, f"RFP limit reached ({plan.rfp_limit}/month). Please upgrade or purchase credits."
        
        return True, f"ok ({available} RFPs remaining)"


async def increment_usage(org_id: str) -> Usage:
    """
    Increment RFP usage after successful upload + analysis start.
    
    Args:
        org_id: Organization ID
        
    Returns:
        Updated usage record
    """
    async with get_db_context() as db:
        usage = await get_or_create_usage(org_id, db)
        usage.rfps_used += 1
        await db.commit()
        return usage


async def get_usage_summary(org_id: str) -> dict:
    """
    Get usage summary for an organization.
    
    Returns:
        Dict with usage stats
    """
    async with get_db_context() as db:
        subscription = await get_subscription(org_id, db)
        
        if not subscription:
            return {
                "has_subscription": False,
                "plan": None,
                "rfps_used": 0,
                "rfps_limit": 0,
                "rfps_remaining": 0
            }
        
        plan = await get_plan(str(subscription.plan_id), db)
        usage = await get_or_create_usage(org_id, db)
        
        rfps_limit = plan.rfp_limit if plan else 0
        rfps_remaining = max(0, (rfps_limit or 0) - usage.rfps_used) if rfps_limit else None
        
        return {
            "has_subscription": True,
            "plan": {
                "name": plan.name if plan else "unknown",
                "display_name": plan.display_name if plan else "Unknown",
                "rfp_limit": rfps_limit,
                "user_limit": plan.user_limit if plan else None
            },
            "subscription_status": subscription.status,
            "billing_cycle": subscription.billing_cycle,
            "current_period_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
            "rfps_used": usage.rfps_used,
            "rfps_limit": rfps_limit,
            "rfps_remaining": rfps_remaining
        }


# ============================================================================
# Plan Seeding (call during migrations or startup)
# ============================================================================

DEFAULT_PLANS = [
    {
        "name": "free",
        "display_name": "Free",
        "price_monthly": 0,
        "price_yearly": 0,
        "rfp_limit": 2,
        "user_limit": 1,
        "history_days": 7,
        "features": ["basic_agents"],
        "is_active": True
    },
    {
        "name": "starter",
        "display_name": "Starter",
        "price_monthly": 4900,  # $49.00 in cents
        "price_yearly": 47000,  # $470.00 in cents (2 months free)
        "rfp_limit": 10,
        "user_limit": 3,
        "history_days": 30,
        "features": ["all_agents", "export"],
        "is_active": True
    },
    {
        "name": "pro",
        "display_name": "Pro",
        "price_monthly": 14900,  # $149.00 in cents
        "price_yearly": 142900,  # $1429.00 in cents (2 months free)
        "rfp_limit": 50,
        "user_limit": 10,
        "history_days": 365,
        "features": ["all_agents", "export", "priority_support", "api_access"],
        "is_active": True
    },
    {
        "name": "enterprise",
        "display_name": "Enterprise",
        "price_monthly": 0,  # Custom pricing
        "price_yearly": 0,
        "rfp_limit": None,  # Unlimited
        "user_limit": None,  # Unlimited
        "history_days": None,  # Unlimited
        "features": ["all_agents", "export", "priority_support", "api_access", "dedicated_support", "sso"],
        "is_active": True
    }
]


async def seed_plans() -> list[Plan]:
    """
    Seed default plans into the database.
    
    Safe to call multiple times - will skip existing plans.
    """
    created = []
    
    async with get_db_context() as db:
        for plan_data in DEFAULT_PLANS:
            # Check if plan exists
            existing = await get_plan_by_name(plan_data["name"], db)
            
            if existing:
                continue
            
            plan = Plan(**plan_data)
            db.add(plan)
            await db.flush()
            created.append(plan)
        
        await db.commit()
    
    return created


async def ensure_free_plan_exists() -> Plan:
    """Ensure the free plan exists, creating it if necessary."""
    async with get_db_context() as db:
        plan = await get_plan_by_name("free", db)
        
        if plan:
            return plan
        
        # Create free plan
        plan = Plan(**DEFAULT_PLANS[0])
        db.add(plan)
        await db.commit()
        
        return plan
