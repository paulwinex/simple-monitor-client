import asyncio
import logging
from typing import Callable

from sm_client.api.client import APIClient
from sm_client.scheduler.manager import SchedulerManager
from sm_client.config.manager import ConfigManager
from sm_client.settings import ClientSettings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Main entry point for the client application."""
    # Load configuration from .env
    host_id = ClientSettings.get_host_id()
    backend_url = ClientSettings.BACKEND_URL
    
    logger.info(f"Starting client for host: {host_id}")
    logger.info(f"Backend URL: {backend_url}")
    
    # Create API client
    api_client = APIClient(base_url=backend_url, host_id=host_id)
    
    # Create config manager (fetches from backend)
    config_manager = ConfigManager(api_client, host_id)
    
    # Discover and initialize collectors
    scheduler = SchedulerManager(config_manager, api_client)
    await scheduler.initialize()
    
    # Register host with backend (if not already registered)
    await api_client.register_host(scheduler.get_enabled_device_types())
    
    # Start config watcher for hot-reload (polls backend)
    asyncio.create_task(watch_config_updates(config_manager, scheduler.reload_config))
    
    # Start scheduler
    scheduler.start()
    
    # Keep running until shutdown
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        scheduler.shutdown()
        await api_client.close()


async def watch_config_updates(config_manager: ConfigManager, callback: Callable):
    """Poll backend for configuration changes."""
    while True:
        await asyncio.sleep(30)  # Check every 30 seconds
        try:
            if await config_manager.check_update():
                await callback()
        except Exception as e:
            logger.warning(f"Config check failed: {e}")
