import asyncio
import shutil
import re
from typing import Optional

from sm_client.sensors.base import BaseCollector, DeviceInfo, Metric


class ZFSCollector(BaseCollector):
    """ZFS pool collector using zfs/zpool commands."""
    device_type = "zfs_pool"
    
    def __init__(self, host_id: str):
        super().__init__(host_id)
        self._pools: list[dict] = []
    
    async def _run_command(self, cmd: list[str]) -> str:
        """Run a command asynchronously."""
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"Command failed: {stderr.decode()}")
        return stdout.decode()
    
    async def _get_pools(self) -> list[dict]:
        """Get ZFS pool information."""
        pools = []
        
        try:
            # Get pool list with properties
            output = await self._run_command([
                'zpool', 'list', '-H', '-o', 'name,size,alloc,free,cap,health'
            ])
            
            lines = output.strip().split('\n')
            for line in lines:
                parts = line.split()
                if len(parts) >= 6:
                    pool = {
                        'name': parts[0],
                        'size': parts[1],
                        'allocated': parts[2],
                        'free': parts[3],
                        'capacity': parts[4],
                        'health': parts[5]
                    }
                    
                    # Parse capacity as percentage
                    cap_match = re.search(r'(\d+)%', parts[4])
                    if cap_match:
                        pool['capacity_pct'] = int(cap_match.group(1))
                    
                    # Get additional properties
                    props = await self._get_pool_properties(parts[0])
                    pool.update(props)
                    
                    pools.append(pool)
        
        except Exception:
            pass
        
        return pools
    
    async def _get_pool_properties(self, pool_name: str) -> dict:
        """Get additional ZFS pool properties."""
        props = {}
        
        try:
            output = await self._run_command([
                'zpool', 'get', '-H', 'allocated,free,size,capacity,fragmentation,allocated',
                pool_name
            ])
            
            for line in output.strip().split('\n'):
                parts = line.split()
                if len(parts) >= 3:
                    prop_name = parts[1]
                    prop_value = parts[2]
                    
                    if prop_name == 'allocated':
                        props['allocated_bytes'] = self._parse_size(prop_value)
                    elif prop_name == 'free':
                        props['free_bytes'] = self._parse_size(prop_value)
                    elif prop_name == 'size':
                        props['size_bytes'] = self._parse_size(prop_value)
                    elif prop_name == 'capacity':
                        props['capacity_pct'] = int(prop_value.rstrip('%'))
                    elif prop_name == 'fragmentation':
                        props['fragmentation_pct'] = int(prop_value.rstrip('%'))
        
        except Exception:
            pass
        
        return props
    
    def _parse_size(self, size_str: str) -> int:
        """Parse ZFS size string to bytes."""
        # Size format: e.g., "10.5T", "500G", "10T"
        multipliers = {
            'K': 1024,
            'M': 1024 ** 2,
            'G': 1024 ** 3,
            'T': 1024 ** 4,
            'P': 1024 ** 5,
        }
        
        match = re.match(r'([\d.]+)([KMGTP])', size_str, re.IGNORECASE)
        if match:
            value = float(match.group(1))
            unit = match.group(2).upper()
            return int(value * multipliers.get(unit, 1))
        
        return 0
    
    async def collect(self) -> list[Metric]:
        """Collect ZFS pool metrics."""
        # Refresh pool list
        self._pools = await self._get_pools()
        
        metrics = []
        now = self._now_timestamp()
        
        for pool in self._pools:
            pool_name = pool.get('name', 'unknown')
            
            # Capacity percentage
            if 'capacity_pct' in pool:
                metrics.append(Metric(
                    host_id=self.host_id,
                    device_id=pool_name,
                    device_type=self.device_type,
                    name="usage_percent",
                    timestamp=now,
                    value=pool['capacity_pct']
                ))
            
            # Size in MB
            if 'size_bytes' in pool:
                size_mb = pool['size_bytes'] // (1024 * 1024)
                metrics.append(Metric(
                    host_id=self.host_id,
                    device_id=pool_name,
                    device_type=self.device_type,
                    name="total_mb",
                    timestamp=now,
                    value=size_mb
                ))
            
            # Used in MB
            if 'allocated_bytes' in pool:
                allocated_mb = pool['allocated_bytes'] // (1024 * 1024)
                metrics.append(Metric(
                    host_id=self.host_id,
                    device_id=pool_name,
                    device_type=self.device_type,
                    name="used_mb",
                    timestamp=now,
                    value=allocated_mb
                ))
            
            # Free in MB
            if 'free_bytes' in pool:
                free_mb = pool['free_bytes'] // (1024 * 1024)
                metrics.append(Metric(
                    host_id=self.host_id,
                    device_id=pool_name,
                    device_type=self.device_type,
                    name="free_mb",
                    timestamp=now,
                    value=free_mb
                ))
            
            # Fragmentation
            if 'fragmentation_pct' in pool:
                metrics.append(Metric(
                    host_id=self.host_id,
                    device_id=pool_name,
                    device_type=self.device_type,
                    name="fragmentation_percent",
                    timestamp=now,
                    value=pool['fragmentation_pct']
                ))
            
            # Health (1 = ONLINE, 0 = other)
            health = 1 if pool.get('health') == 'ONLINE' else 0
            metrics.append(Metric(
                host_id=self.host_id,
                device_id=pool_name,
                device_type=self.device_type,
                name="health",
                timestamp=now,
                value=health
            ))
        
        return metrics
    
    async def get_devices(self) -> list[DeviceInfo]:
        pools = await self._get_pools()
        return [
            DeviceInfo(device_id=pool['name'], label=pool['name'], details={})
            for pool in pools
        ]

    @classmethod
    async def check_availability(cls) -> bool:
        """Check if zfs/zpool is available."""
        if not shutil.which('zpool'):
            return False
        
        # Check if we can run zpool list
        proc = await asyncio.create_subprocess_exec(
            'zpool', 'list',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()
        return proc.returncode == 0
