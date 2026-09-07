"""
Script to delete all job opportunities from the database.
WARNING: This will permanently delete ALL job opportunities and related data.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import delete, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db_session
from app.models.opportunity import Opportunity
from app.models.opportunity_skill import OpportunitySkill
from app.models.application import Application
from app.models.match import Match


async def count_opportunities(session: AsyncSession) -> dict:
    """Count current opportunities and related records."""
    opp_count = await session.execute(select(func.count()).select_from(Opportunity))
    skill_count = await session.execute(select(func.count()).select_from(OpportunitySkill))
    app_count = await session.execute(select(func.count()).select_from(Application))
    match_count = await session.execute(select(func.count()).select_from(Match))
    
    return {
        "opportunities": opp_count.scalar() or 0,
        "opportunity_skills": skill_count.scalar() or 0,
        "applications": app_count.scalar() or 0,
        "matches": match_count.scalar() or 0,
    }


async def delete_all_opportunities(session: AsyncSession) -> dict:
    """Delete all opportunities and their cascading related records."""
    # First, show what will be deleted
    counts = await count_opportunities(session)
    print(f"Current database state:")
    print(f"  Opportunities: {counts['opportunities']}")
    print(f"  Opportunity Skills: {counts['opportunity_skills']}")
    print(f"  Applications: {counts['applications']}")
    print(f"  Matches: {counts['matches']}")
    
    if counts['opportunities'] == 0:
        print("No opportunities to delete.")
        return counts
    
    # Delete all opportunities (cascade will handle related records)
    await session.execute(delete(Opportunity))
    await session.commit()
    
    # Verify deletion
    new_counts = await count_opportunities(session)
    print(f"\nAfter deletion:")
    print(f"  Opportunities: {new_counts['opportunities']}")
    print(f"  Opportunity Skills: {new_counts['opportunity_skills']}")
    print(f"  Applications: {new_counts['applications']}")
    print(f"  Matches: {new_counts['matches']}")
    
    return new_counts


async def main():
    """Main function to execute the deletion."""
    import sys
    
    # Check for command-line confirmation
    auto_confirm = "--confirm" in sys.argv or "-y" in sys.argv
    
    print("=" * 60)
    print("WARNING: This will delete ALL job opportunities!")
    print("This action cannot be undone.")
    print("=" * 60)
    
    if not auto_confirm:
        confirmation = input("Type 'DELETE' to confirm: ")
        if confirmation != "DELETE":
            print("Operation cancelled.")
            return
    else:
        print("Auto-confirmation enabled via command-line flag.")
    
    print("\nStarting deletion process...")
    
    async for session in get_db_session():
        try:
            await delete_all_opportunities(session)
            print("\n[SUCCESS] All opportunities deleted successfully!")
        except Exception as e:
            print(f"\n[ERROR] Error during deletion: {e}")
            await session.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(main())