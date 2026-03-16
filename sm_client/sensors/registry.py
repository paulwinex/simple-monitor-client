from typing import Type

from sm_client.sensors.base import BaseCollector
from sm_client.sensors.cpu import CPUCollector
from sm_client.sensors.ram import RAMCollector
from sm_client.sensors.network import NetCollector
from sm_client.sensors.storage import StorageCollector
from sm_client.sensors.zfs import ZFSCollector


# Registry of all available collectors
COLLECTORS: dict[str, Type[BaseCollector]] = {
    "cpu": CPUCollector,
    "ram": RAMCollector,
    "network": NetCollector,
    "storage": StorageCollector,
    "zfs_pool": ZFSCollector,
}


async def discover_collectors(host_id: str) -> dict[str, BaseCollector]:
    """
    Discover available collectors on this host.
    
    Returns:
        Dictionary of collector_type -> collector instance
    """
    available = {}
    
    for collector_type, collector_class in COLLECTORS.items():
        collector = collector_class(host_id)
        if await collector.check_availability():
            available[collector_type] = collector
    
    return available


def get_collector_types() -> list[str]:
    """Get list of all supported collector types."""
    return list(COLLECTORS.keys())


def get_collector_class(collector_type: str) -> Type[BaseCollector] | None:
    """Get collector class by type."""
    return COLLECTORS.get(collector_type)
