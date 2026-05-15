import logging
import sys

import httpx

from sm_client.sensors.base import Metric


logger = logging.getLogger(__name__)


class APIClient:
    """Async HTTP client for backend API communication."""
    
    def __init__(self, base_url: str, host_id: str):
        self.base_url = base_url.rstrip('/')
        self.host_id = host_id
        self.client = httpx.AsyncClient(timeout=10.0)
    
    async def register_host(self, collectors: list[str]) -> bool:
        """Register host with backend."""
        logger.info(f"Registering host with backend {self.base_url}")
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/hosts/register",
                json={"host_id": self.host_id, "collectors": collectors}
            )
            if response.status_code == 200:
                logger.info(f"Host {self.host_id} registered successfully")
                return True
            else:
                logger.error(f"Failed to register host: {response.status_code}")
                logger.error(response.text)
                sys.exit(1)
        except httpx.RequestError as e:
            logger.error(f"Failed to register host: {e}")
            sys.exit(1)

    async def get_host_config(self, host_id: str) -> dict:
        """Fetch host configuration from backend."""
        logger.info(f"Fetching host config from backend {self.base_url}")
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/hosts/{host_id}/config"
            )
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            logger.error(f"Failed to fetch config: {e}")
            return {}
    
    async def get_config_version(self, host_id: str) -> int:
        """Get configuration version for change detection."""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/hosts/{host_id}/config/version"
            )
            response.raise_for_status()
            return response.json().get('version', 0)
        except httpx.RequestError as e:
            logger.error(f"Failed to fetch config version: {e}")
            return 0
    
    async def send_metrics(self, metrics: list[Metric]) -> bool:
        """
        Send batch of raw metrics to backend.
        Client only sends raw data - resampling is backend responsibility.
        """
        logger.info(f"Sending metrics to backend... [{len(metrics)}]")
        if not metrics:
            return True
        
        # Always send as batch (even single metric)
        payload = {
            "host_id": self.host_id,
            "metrics": [
                {
                    "device_id": m.device_id,
                    "device_type": m.device_type,
                    "name": m.name,
                    "timestamp": m.timestamp,
                    "value": m.value  # Always int for raw data
                }
                for m in metrics
            ]
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/metrics/ingest",
                json=payload
            )
            if response.status_code == 200:
                return True
            else:
                logger.warning(f"Failed to send metrics: {response.status_code}")
                return False
        except httpx.RequestError:
            # Backend unavailable - drop metrics (no local buffering)
            logger.warning("Backend unavailable - dropping metrics")
            return False
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
