"""
Cleanup task to remove stale shadow followers
Runs periodically to clean up shadows older than 24 hours
"""

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .database import Database

logger = logging.getLogger('botc_bot.cleanup')

class CleanupTask:
    """Background task for cleaning up stale data."""
    
    def __init__(self, db: 'Database'):
        self.db = db
        self.task = None
        
    async def cleanup_stale_shadows(self):
        """Remove shadow followers older than 24 hours."""
        try:
            # Calculate timestamp for 24 hours ago
            import time
            twenty_four_hours_ago = int(time.time()) - (24 * 60 * 60)
            
            async with self.db.pool.acquire() as conn:
                result = await conn.execute(
                    """
                    DELETE FROM shadow_followers 
                    WHERE created_at < $1
                    RETURNING follower_id, target_id, guild_id
                    """,
                    twenty_four_hours_ago
                )
                
                # Extract count from result string like "DELETE 5"
                if result:
                    count = int(result.split()[-1]) if result.split()[-1].isdigit() else 0
                    if count > 0:
                        logger.info(f"Cleaned up {count} stale shadow followers (>24h old)")
                        
        except Exception as e:
            logger.error(f"Error cleaning up stale shadow followers: {e}", exc_info=True)
    
    async def run_periodic_cleanup(self):
        """Run cleanup tasks periodically."""
        logger.info("Starting cleanup task (runs every hour)")
        
        while True:
            try:
                # Run cleanup immediately on start
                await self.cleanup_stale_shadows()
                
                # Wait 1 hour before next cleanup
                await asyncio.sleep(60 * 60)  # 1 hour
                
            except asyncio.CancelledError:
                logger.info("Cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Unexpected error in cleanup task: {e}", exc_info=True)
                # Wait before retrying on error
                await asyncio.sleep(300)  # 5 minutes
    
    def start(self):
        """Start the cleanup background task."""
        if self.task is None or self.task.done():
            self.task = asyncio.create_task(self.run_periodic_cleanup())
            logger.info("Cleanup task started")
    
    def stop(self):
        """Stop the cleanup background task."""
        if self.task and not self.task.done():
            self.task.cancel()
            logger.info("Cleanup task stopped")
