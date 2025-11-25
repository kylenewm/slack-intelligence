#!/usr/bin/env python3
"""
One-time sync script for testing.
Fetches messages and prioritizes them.
"""

import sys
import asyncio
import logging
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from backend.services.sync_service import SyncService
from backend.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Run a one-time sync"""
    logger.info("Starting one-time sync...")
    
    # Validate configuration
    if not settings.validate():
        logger.error("Configuration validation failed")
        sys.exit(1)
    
    # Create sync service
    sync_service = SyncService()
    
    # Run sync (default 24 hours)
    try:
        result = await sync_service.sync(hours_ago=24)
        
        logger.info("=" * 60)
        logger.info("SYNC RESULTS")
        logger.info("=" * 60)
        logger.info(f"Status: {result['status']}")
        logger.info(f"Duration: {result['duration_seconds']:.1f}s")
        logger.info(f"Channels synced: {result['fetch']['channels_synced']}")
        logger.info(f"Messages fetched: {result['fetch']['messages_fetched']}")
        logger.info(f"New messages: {result['fetch']['new_messages']}")
        logger.info(f"Prioritized: {result['prioritization']['prioritized']}")
        
        if result['fetch']['errors']:
            logger.warning(f"Errors: {len(result['fetch']['errors'])}")
        
        logger.info("=" * 60)
        logger.info("✅ Sync complete!")
        
    except Exception as e:
        logger.error(f"❌ Sync failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
