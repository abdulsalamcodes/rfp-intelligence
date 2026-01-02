"""
Seed default plans into the database.

Run this script after migrations to set up pricing plans.

Usage:
    python scripts/seed_plans.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from database.connection import get_db_context
from database.models import Plan


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
        "price_monthly": 4900,
        "price_yearly": 47000,
        "rfp_limit": 10,
        "user_limit": 3,
        "history_days": 30,
        "features": ["all_agents", "export"],
        "is_active": True
    },
    {
        "name": "pro",
        "display_name": "Pro",
        "price_monthly": 14900,
        "price_yearly": 142900,
        "rfp_limit": 50,
        "user_limit": 10,
        "history_days": 365,
        "features": ["all_agents", "export", "priority_support", "api_access"],
        "is_active": True
    },
    {
        "name": "enterprise",
        "display_name": "Enterprise",
        "price_monthly": 0,
        "price_yearly": 0,
        "rfp_limit": None,
        "user_limit": None,
        "history_days": None,
        "features": ["all_agents", "export", "priority_support", "api_access", "dedicated_support", "sso"],
        "is_active": True
    }
]


async def seed_plans():
    """Seed default plans."""
    async with get_db_context() as db:
        for plan_data in DEFAULT_PLANS:
            # Check if plan exists
            result = await db.execute(
                select(Plan).where(Plan.name == plan_data["name"])
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                print(f"Plan '{plan_data['name']}' already exists, skipping")
                continue
            
            plan = Plan(**plan_data)
            db.add(plan)
            print(f"Created plan: {plan_data['display_name']}")
        
        await db.commit()
    
    print("\n✅ Plans seeded successfully!")


if __name__ == "__main__":
    asyncio.run(seed_plans())
