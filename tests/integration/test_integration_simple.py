#\!/usr/bin/env python3
"""
Simple integration test for the subscription system.
"""

import asyncio
import logging
import tempfile
from pathlib import Path
from mcp_server.resources.subscriptions import (
    SubscriptionManager,
    NotificationFilter,
    NotificationType,
    SubscriptionScope,
    create_subscription_manager
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_integration():
    """Test subscription system integration."""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        logger.info(f"Using temp directory: {temp_path}")
        
        # Create subscription manager
        manager = create_subscription_manager(batch_size=2, batch_timeout=1.0)
        await manager.start()
        
        try:
            # Create session and subscription
            session_id = manager.create_session()
            
            filter_obj = NotificationFilter(
                file_extensions={"py"},
                notification_types={NotificationType.FILE_CREATED, NotificationType.FILE_MODIFIED}
            )
            
            result = await manager.subscribe(
                session_id=session_id,
                scope=SubscriptionScope.DIRECTORY,
                resource_uri=str(temp_path),
                notification_filter=filter_obj
            )
            
            if not result.success:
                logger.error(f"Subscription failed: {result.error}")
                return
            
            subscription_id = result.value
            logger.info(f"Created subscription: {subscription_id}")
            
            # Simulate file events
            test_file = temp_path / "test.py"
            test_file.write_text("print(Hello
