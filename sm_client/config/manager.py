import time
from sm_client.api.client import APIClient


class ConfigManager:
    """Manages configuration fetched from backend."""
    
    def __init__(self, api_client: APIClient, host_id: str):
        self.api_client = api_client
        self.host_id = host_id
        self._config: dict = {}
        self._last_fetch: int = 0
        self._poll_interval: int = 30  # Check every 30 seconds
    
    async def fetch_config(self) -> dict:
        """Fetch configuration from backend."""
        config = await self.api_client.get_host_config(self.host_id)
        self._config = config
        self._last_fetch = int(time.time())
        return config
    
    async def check_update(self) -> bool:
        """Check if config has been updated on server."""
        if int(time.time()) - self._last_fetch < self._poll_interval:
            return False
        
        # Check for config version/hash change
        try:
            remote_version = await self.api_client.get_config_version(self.host_id)
            local_version = self._config.get('version', 0)
            if remote_version != local_version:
                await self.fetch_config()
                return True
        except Exception:
            pass
        
        return False
    
    def get_collector_config(self, collector_type: str) -> dict:
        """Get configuration for specific collector."""
        return self._config.get('collectors', {}).get(collector_type, {})
    
    def get_all_collectors(self) -> dict:
        """Get all collector configurations."""
        return self._config.get('collectors', {})
