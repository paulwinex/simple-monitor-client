import asyncio
import sys

import httpx


async def wait_server(url: str, delay: int = 2):
    async with httpx.AsyncClient() as client:
        while True:
            try:
                response = await client.head(url, timeout=3.0, follow_redirects=True)
                if response.is_success or response.is_server_error or response.is_client_error:
                    print("Host available!")
                    return
            except httpx.RequestError:
                print(".", end="", flush=True)
            except KeyboardInterrupt:
                sys.exit(0)
            await asyncio.sleep(delay)


async def check_sensors():
    """Check and display availability of all registered sensors with their devices."""
    from sm_client.sensors.registry import COLLECTORS

    print()
    print("  Sensor Availability Check")
    print()

    for name, cls in COLLECTORS.items():
        try:
            available = await cls.check_availability()
        except Exception:
            available = False

        status = "\u2713 Available" if available else "\u2717 Unavailable"
        print(f"  {name:15s} {status}")

        if available:
            try:
                collector = cls(host_id="check")
                devices = await collector.get_devices()
                if not devices:
                    print("    (no devices found)")
                for dev in devices:
                    parts = _format_details(dev.details)
                    suffix = f"  ({parts})" if parts else ""
                    print(f"    {dev.device_id:12s} {dev.label}{suffix}")
            except Exception as e:
                print(f"    (no device info: {e})")

    print()


def _format_details(details: dict) -> str:
    parts = []
    for k, v in details.items():
        if k == "cores":
            parts.append(f"{v} cores")
        elif k == "total_gb":
            parts.append(f"{v} GB RAM")
        elif k == "swap_gb":
            parts.append(f"{v} GB swap")
        elif k == "count":
            parts.append(f"{v} interfaces")
        elif k == "interfaces":
            parts.append(", ".join(v))
        elif k == "type":
            parts.append(v)
        else:
            parts.append(f"{k}: {v}")
    return ", ".join(parts)


async def scan_sensors():
    """Scan all available sensors and print their current values."""
    from collections import defaultdict
    from sm_client.sensors.registry import COLLECTORS

    print()
    print("  Sensor Scan")
    print()

    has_data = False

    for name, cls in COLLECTORS.items():
        try:
            available = await cls.check_availability()
        except Exception:
            available = False

        if not available:
            continue

        try:
            collector = cls(host_id="scan")
            metrics = await collector.collect()
        except Exception as e:
            print(f"  {name}: error collecting - {e}")
            print()
            continue

        if not metrics:
            print(f"  {name}: no metrics returned")
            print()
            continue

        has_data = True

        by_device: dict[str, list] = defaultdict(list)
        for m in metrics:
            by_device[m.device_id].append(m)

        print(f"  {name}")

        for device_id, device_metrics in by_device.items():
            print(f"    {device_id}")
            for m in device_metrics:
                print(f"      {m.name:20s} {m.value}")
        print()

    if not has_data:
        print("  No sensors with data found.")
        print()