import psutil

from sm_client.sensors.base import BaseCollector, Metric


class RAMCollector(BaseCollector):
    """RAM metrics collector (usage, used, available, swap, temp)."""
    device_type = "ram"

    async def collect(self) -> list[Metric]:
        """Collect RAM metrics."""
        metrics = []

        # Virtual memory
        vm = psutil.virtual_memory()

        # Usage percent
        metrics.append(Metric(
            host_id=self.host_id,
            device_id="ram",
            device_type=self.device_type,
            name="usage_percent",
            timestamp=self._now_timestamp(),
            value=int(vm.percent)
        ))

        # Used MB
        used_mb = int(vm.used / (1024 * 1024))
        metrics.append(Metric(
            host_id=self.host_id,
            device_id="ram",
            device_type=self.device_type,
            name="used_mb",
            timestamp=self._now_timestamp(),
            value=used_mb
        ))

        # Available MB
        available_mb = int(vm.available / (1024 * 1024))
        metrics.append(Metric(
            host_id=self.host_id,
            device_id="ram",
            device_type=self.device_type,
            name="available_mb",
            timestamp=self._now_timestamp(),
            value=available_mb
        ))

        # Swap used MB
        swap = psutil.swap_memory()
        if swap.total > 0:
            swap_used_mb = int(swap.used / (1024 * 1024))
            metrics.append(Metric(
                host_id=self.host_id,
                device_id="ram",
                device_type=self.device_type,
                name="swap_used_mb",
                timestamp=self._now_timestamp(),
                value=swap_used_mb
            ))

        # Memory temperature (if available via sensors)
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                mem_temp = None
                
                # Priority 1: Look for memory-specific sensors by label
                for name, entries in temps.items():
                    for entry in entries:
                        label_lower = entry.label.lower()
                        if 'mem' in label_lower or 'dram' in label_lower:
                            mem_temp = entry.current
                            break
                    if mem_temp:
                        break
                
                # Priority 2: gigabyte_wmi sensors (common for RAM on some boards)
                if mem_temp is None:
                    for name, entries in temps.items():
                        if 'gigabyte_wmi' in name.lower() or 'wmi' in name.lower():
                            # Usually temp3-temp6 are chipset/memory related
                            for entry in entries:
                                if entry.label in ('temp3', 'temp4', 'temp5', 'temp6'):
                                    if 20 < entry.current < 100:  # Reasonable range
                                        mem_temp = entry.current
                                        break
                            if mem_temp:
                                break
                
                # Priority 3: k10temp Tccd (can be related to memory controller)
                if mem_temp is None:
                    if 'k10temp-pci-00c3' in temps or 'k10temp' in temps:
                        key = 'k10temp-pci-00c3' if 'k10temp-pci-00c3' in temps else 'k10temp'
                        for entry in temps[key]:
                            if entry.label == 'Tccd1':
                                if 20 < entry.current < 100:
                                    mem_temp = entry.current
                                    break
                
                # Priority 4: nct6792/nct6798 (hardware monitor chips)
                if mem_temp is None:
                    for name, entries in temps.items():
                        if 'nct' in name.lower():
                            for entry in entries:
                                if 'remote' in entry.label.lower() or 'chip' in entry.label.lower():
                                    if 20 < entry.current < 100:
                                        mem_temp = entry.current
                                        break
                            if mem_temp:
                                break
                
                if mem_temp is not None:
                    metrics.append(Metric(
                        host_id=self.host_id,
                        device_id="ram",
                        device_type=self.device_type,
                        name="temperature",
                        timestamp=self._now_timestamp(),
                        value=int(mem_temp)
                    ))
        except Exception:
            pass

        return metrics
    
    @classmethod
    async def check_availability(cls) -> bool:
        """Check if psutil is available."""
        try:
            psutil.virtual_memory()
            return True
        except Exception:
            return False
