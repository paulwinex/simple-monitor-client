import psutil

from sm_client.sensors.base import BaseCollector, Metric


class CPUCollector(BaseCollector):
    """CPU metrics collector (load, temp)."""
    device_type = "cpu"

    async def collect(self) -> list[Metric]:
        """Collect CPU metrics."""
        metrics = []

        # CPU load (percentage)
        load = psutil.cpu_percent(interval=0.1)
        metrics.append(Metric(
            host_id=self.host_id,
            device_id="cpu",
            device_type=self.device_type,
            name="load",
            timestamp=self._now_timestamp(),
            value=int(load)
        ))

        # CPU temperature (if available)
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                cpu_temp = None
                
                # Priority 1: k10temp (AMD CPUs) - Tctl is the most accurate
                if 'k10temp-pci-00c3' in temps or 'k10temp' in temps:
                    key = 'k10temp-pci-00c3' if 'k10temp-pci-00c3' in temps else 'k10temp'
                    for entry in temps[key]:
                        if entry.label == 'Tctl':
                            cpu_temp = entry.current
                            break
                
                # Priority 2: coretemp (Intel CPUs) - Package id 0
                if cpu_temp is None:
                    if 'coretemp-isa-0000' in temps or 'coretemp' in temps:
                        key = 'coretemp-isa-0000' if 'coretemp-isa-0000' in temps else 'coretemp'
                        for entry in temps[key]:
                            if 'Package' in entry.label or 'Core' in entry.label:
                                cpu_temp = entry.current
                                break
                
                # Priority 3: zenpower (AMD with zenpower module)
                if cpu_temp is None:
                    if 'zenpower-isa-0000' in temps or 'zenpower' in temps:
                        key = 'zenpower-isa-0000' if 'zenpower-isa-0000' in temps else 'zenpower'
                        for entry in temps[key]:
                            if 'Tdie' in entry.label or 'Tctl' in entry.label:
                                cpu_temp = entry.current
                                break
                
                # Fallback: first reasonable temperature (> 20°C to avoid fake sensors)
                if cpu_temp is None:
                    for name, entries in temps.items():
                        # Skip known fake sensors
                        if 'acpitz' in name.lower():
                            continue
                        for entry in entries:
                            if entry.current > 20:  # Reasonable minimum temperature
                                cpu_temp = entry.current
                                break
                        if cpu_temp:
                            break
                
                if cpu_temp is not None:
                    metrics.append(Metric(
                        host_id=self.host_id,
                        device_id="cpu",
                        device_type=self.device_type,
                        name="temperature",
                        timestamp=self._now_timestamp(),
                        value=int(cpu_temp)
                    ))
        except Exception:
            raise
        return metrics
    
    @classmethod
    async def check_availability(cls) -> bool:
        """Check if psutil is available."""
        try:
            psutil.cpu_percent()
            return True
        except Exception:
            return False
