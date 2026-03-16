import logging
from typing import TYPE_CHECKING

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from sm_client.sensors.base import BaseCollector
from sm_client.config.manager import ConfigManager
from sm_client.api.client import APIClient
from sm_client.sensors.registry import get_collector_class

if TYPE_CHECKING:
    from sm_client.sensors.base import Metric


logger = logging.getLogger(__name__)


class SchedulerManager:
    """Manages APScheduler with dynamic task management."""
    
    def __init__(self, config_manager: ConfigManager, api_client: APIClient):
        self.scheduler = AsyncIOScheduler()
        self.config_manager = config_manager
        self.api_client = api_client
        self._task_ids: dict[str, str] = {}  # collector_type -> job_id
        self._collectors: dict[str, BaseCollector] = {}
    
    async def initialize(self):
        """Initialize scheduler with configuration from backend."""
        # Fetch configuration
        await self.config_manager.fetch_config()
        config = self.config_manager._config
        
        # Discover available collectors
        from sm_client.sensors.registry import get_collector_types
        
        for collector_type in get_collector_types():
            collector_class = get_collector_class(collector_type)
            if collector_class:
                collector = collector_class(self.api_client.host_id)
                if await collector.check_availability():
                    self._collectors[collector_type] = collector
                    logger.info(f"Collector {collector_type} is available")
        
        # Create jobs for enabled collectors
        for collector_type, collector_config in config.get('collectors', {}).items():
            if not collector_config.get('enabled', True):
                continue
            
            collector = self._collectors.get(collector_type)
            if not collector:
                logger.warning('Skipping collector %s', collector_type)
                continue
            
            interval = collector_config.get('interval_sec', 5)
            self._create_collector_job(collector_type, interval, collector)
            logger.info(f"Started collector {collector_type} with interval {interval}s")
    
    async def reload_config(self):
        """Hot-reload: update tasks based on new configuration from server."""
        await self.config_manager.fetch_config()
        config = self.config_manager._config
        
        # Get currently enabled collectors from config
        enabled_in_config = set()
        for collector_type, collector_config in config.get('collectors', {}).items():
            if collector_config.get('enabled', True):
                enabled_in_config.add(collector_type)
        
        # Remove disabled collectors
        for job in self.scheduler.get_jobs():
            collector_type = job.id.replace('collector_', '')
            if collector_type not in enabled_in_config:
                self.scheduler.remove_job(job.id)
                if collector_type in self._task_ids:
                    del self._task_ids[collector_type]
                logger.info(f"Stopped collector {collector_type}")
        
        # Update or create jobs for enabled collectors
        for collector_type, collector_config in config.get('collectors', {}).items():
            if not collector_config.get('enabled', True):
                continue
            
            collector = self._collectors.get(collector_type)
            if not collector:
                continue
            
            interval = collector_config.get('interval_sec', 5)
            self._create_collector_job(collector_type, interval, collector)
            logger.info(f"Updated collector {collector_type} with interval {interval}s")
    
    def _create_collector_job(self, collector_type: str, interval: int, collector: BaseCollector):
        """Create or update a scheduled job for a collector."""
        job_id = f"collector_{collector_type}"
        
        # Remove existing job if present
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
        
        # Add new job
        self.scheduler.add_job(
            self._run_collector,
            'interval',
            seconds=interval,
            id=job_id,
            args=[collector_type, collector],
            replace_existing=True
        )
        self._task_ids[job_id] = job_id
    
    async def _run_collector(self, collector_type: str, collector: BaseCollector):
        """Execute collector and send metrics to backend."""
        try:
            metrics = await collector.collect()
            if metrics:
                # Send raw data only - resampling is backend responsibility
                await self.api_client.send_metrics(metrics)
                logger.debug(f"Collector {collector_type} collected {len(metrics)} metrics")
        except Exception as e:
            logger.warning(f"Collector {collector_type} failed: {e}")
    
    def start(self):
        """Start the scheduler."""
        self.scheduler.start()
        logger.info("Scheduler started")
    
    def shutdown(self):
        """Shutdown the scheduler."""
        self.scheduler.shutdown()
        logger.info("Scheduler shutdown")
    
    def get_enabled_device_types(self) -> list[str]:
        """Get list of enabled device types."""
        return list(self._collectors.keys())
