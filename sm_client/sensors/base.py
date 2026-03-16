from abc import ABC, abstractmethod
from typing import NamedTuple
from datetime import datetime


class Metric(NamedTuple):
    """Metric data point."""
    host_id: str        # Unique host identifier
    device_id: str      # Device unique name (e.g., serial number)
    device_type: str    # cpu, ram, hdd, ssd, zfs_pool, network
    name: str           # Metric name (temperature, load, usage_percent)
    timestamp: int      # Unix timestamp
    value: int          # Metric value (always int for raw data)


class BaseCollector(ABC):
    """Abstract base class for all collectors."""
    
    device_type: str  # Class attribute: 'cpu', 'ram', etc.
    
    def __init__(self, host_id: str):
        self.host_id = host_id
    
    @abstractmethod
    async def collect(self) -> list[Metric]:
        """Collect metrics from sensors. Returns list of Metric objects."""
        pass
    
    @abstractmethod
    async def check_availability(self) -> bool:
        """Check if required tools/sensors are available on this host."""
        pass
    
    def _now_timestamp(self) -> int:
        """Get current timestamp as int."""
        return int(datetime.now().timestamp())
