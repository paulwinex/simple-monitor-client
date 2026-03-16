import asyncio
import shutil
import re
from typing import Optional

from sm_client.sensors.base import BaseCollector, Metric


class StorageCollector(BaseCollector):
    """HDD/SSD SMART collector using smartctl."""
    device_type = "hdd"  # Could also be 'ssd' based on device
    
    def __init__(self, host_id: str):
        super().__init__(host_id)
        self._disks: list[dict] = []
    
    async def _run_smartctl(self, args: list[str]) -> str:
        """Run smartctl asynchronously."""
        proc = await asyncio.create_subprocess_exec(
            'smartctl', *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"smartctl failed: {stderr.decode()}")
        return stdout.decode()
    
    async def _scan_disks(self) -> list[dict]:
        """Scan for available disks."""
        if not shutil.which('smartctl'):
            return []
        
        try:
            # Scan for devices
            output = await self._run_smartctl(['--scan-open'])
            lines = output.strip().split('\n')
            
            disks = []
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                # Parse device line
                parts = line.split()
                if parts:
                    device = parts[0]
                    # Get info
                    info = await self._get_device_info(device)
                    if info:
                        disks.append(info)
            
            return disks
        except Exception:
            return []
    
    async def _get_device_info(self, device: str) -> Optional[dict]:
        """Get device information."""
        try:
            output = await self._run_smartctl(['-a', device])
            
            info = {'device': device, 'type': 'hdd'}
            
            # Parse model
            model_match = re.search(r'Device Model:\s*(.+)', output)
            if model_match:
                info['model'] = model_match.group(1).strip()
            else:
                model_match = re.search(r'Model Family:\s*(.+)', output)
                if model_match:
                    info['model'] = model_match.group(1).strip()
            
            # Parse serial
            serial_match = re.search(r'Serial Number:\s*(.+)', output)
            if serial_match:
                info['serial'] = serial_match.group(1).strip()
            
            # Parse capacity
            capacity_match = re.search(r'User Capacity:\s*\[(\d+)\s*bytes\]', output)
            if capacity_match:
                info['capacity_bytes'] = int(capacity_match.group(1))
            
            # Parse temperature (try multiple formats)
            temp_match = re.search(r'Temperature.*?\s(\d+)\s*C', output)
            if not temp_match:
                # Try parsing from SMART attributes (e.g., "194 Temperature_Celsius ... 44 (Min/Max 20/62)")
                temp_match = re.search(r'Temperature_Celsius.*?\s(\d+)\s*\(', output)
            if not temp_match:
                # Alternative: just temperature value at the end of line
                temp_match = re.search(r'Temperature.*?RAW_VALUE.*?\n.*?\s(\d+)$', output, re.MULTILINE)
            if temp_match:
                info['temperature'] = int(temp_match.group(1))
            
            # Parse health
            health_match = re.search(r'SMART overall-health self-assessment test result:\s*(\w+)', output)
            if health_match:
                info['health'] = health_match.group(1)
                if info['health'] == 'PASSED':
                    info['health'] = 'ok'
            
            # Check if SSD (based on rotation rate or model)
            if 'SSD' in output or 'Solid State' in output:
                info['type'] = 'ssd'
            
            return info
        except Exception:
            return None
    
    async def collect(self) -> list[Metric]:
        """Collect storage metrics from all disks."""
        # Scan disks if not done yet
        if not self._disks:
            self._disks = await self._scan_disks()
        
        metrics = []
        now = self._now_timestamp()
        
        for disk in self._disks:
            device_id = disk.get('serial', disk['device'].replace('/', '_').replace('dev_', ''))
            device_type = disk.get('type', 'hdd')
            
            # Temperature
            if 'temperature' in disk:
                metrics.append(Metric(
                    host_id=self.host_id,
                    device_id=device_id,
                    device_type=device_type,
                    name="temperature",
                    timestamp=now,
                    value=disk['temperature']
                ))
            
            # Health status (1 = OK, 0 = not OK)
            health_value = 1 if disk.get('health') == 'ok' else 0
            metrics.append(Metric(
                host_id=self.host_id,
                device_id=device_id,
                device_type=device_type,
                name="health",
                timestamp=now,
                value=health_value
            ))
            
            # Capacity in MB
            if 'capacity_bytes' in disk:
                capacity_mb = disk['capacity_bytes'] // (1024 * 1024)
                metrics.append(Metric(
                    host_id=self.host_id,
                    device_id=device_id,
                    device_type=device_type,
                    name="total_mb",
                    timestamp=now,
                    value=capacity_mb
                ))
        
        return metrics
    
    @classmethod
    async def check_availability(cls) -> bool:
        """Check if smartctl is available and disks exist."""
        if not shutil.which('smartctl'):
            return False
        
        # Check if we can run smartctl
        proc = await asyncio.create_subprocess_exec(
            'smartctl', '--scan',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()
        return proc.returncode == 0
