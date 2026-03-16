from datetime import datetime
import psutil

from sm_client.sensors.base import BaseCollector, Metric


class NetCollector(BaseCollector):
    """Network traffic collector - aggregated across all physical interfaces."""
    device_type = "network"
    
    def __init__(self, host_id: str):
        super().__init__(host_id)
        self.prev_io_sent = 0
        self.prev_io_recv = 0
        self.prev_time = datetime.now()
        # Initialize on first run
        self._init_counters()
    
    def _init_counters(self):
        """Initialize counters with current values."""
        bytes_sent, bytes_recv = self._get_physical_io()
        self.prev_io_sent = bytes_sent
        self.prev_io_recv = bytes_recv
    
    def _get_physical_io(self) -> tuple[int, int]:
        """Get aggregated I/O from physical interfaces only."""
        per_nic = psutil.net_io_counters(pernic=True)
        bytes_sent = 0
        bytes_recv = 0

        for nic, io in per_nic.items():
            nic_lower = nic.lower()
            # Skip loopback
            if nic_lower == 'lo':
                continue
            # Skip virtual interfaces
            if any(nic_lower.startswith(x) for x in ['veth', 'fw', 'tap', 'br', 'vmbr', 'docker']):
                continue
            bytes_sent += io.bytes_sent
            bytes_recv += io.bytes_recv

        return bytes_sent, bytes_recv

    async def collect(self) -> list[Metric]:
        """Collect network metrics (upload/download speed)."""
        now = datetime.now()
        bytes_sent, bytes_recv = self._get_physical_io()

        dt = (now - self.prev_time).total_seconds()
        metrics = []

        if dt > 0:
            # Calculate KB/s (as int)
            up_speed = int(max(0, (bytes_sent - self.prev_io_sent) / dt / 1024))
            down_speed = int(max(0, (bytes_recv - self.prev_io_recv) / dt / 1024))

            metrics.extend([
                Metric(
                    host_id=self.host_id,
                    device_id="net",
                    device_type="network",
                    name="upload",
                    timestamp=self._now_timestamp(),
                    value=up_speed
                ),
                Metric(
                    host_id=self.host_id,
                    device_id="net",
                    device_type="network",
                    name="download",
                    timestamp=self._now_timestamp(),
                    value=down_speed
                )
            ])

        self.prev_io_sent = bytes_sent
        self.prev_io_recv = bytes_recv
        self.prev_time = now

        return metrics
    
    @classmethod
    async def check_availability(cls) -> bool:
        """Check if psutil network is available."""
        try:
            psutil.net_io_counters()
            return True
        except Exception:
            return False
