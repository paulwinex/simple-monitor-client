# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "apscheduler>=3.10.4",
#     "httpx>=0.26.0",
#     "psutil>=5.9.8",
#     "python-dotenv>=1.0.0",
# ]
# ///

"""
Simple Monitor Client - Collects system metrics and sends to backend.

Usage:
    uv run -m sm_client              Run the monitor
    uv run -m sm_client check        Check sensor availability
    uv run -m sm_client scan         Scan sensors and print values
"""
import argparse
import asyncio

from sm_client.app import main


def _cmd_check(_args: argparse.Namespace) -> None:
    from sm_client.utils import check_sensors
    asyncio.run(check_sensors())


def _cmd_scan(_args: argparse.Namespace) -> None:
    from sm_client.utils import scan_sensors
    asyncio.run(scan_sensors())


def _cmd_run(_args: argparse.Namespace) -> None:
    asyncio.run(main())


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="sm_client",
        description="Simple Monitor Client",
    )
    sub = parser.add_subparsers(dest="command")
    sub.required = False

    sub.add_parser("check", help="Check sensor availability")
    sub.add_parser("scan", help="Scan sensors and print current values")

    args = parser.parse_args(argv)
    return args


if __name__ == "__main__":
    args = parse_args()

    commands = {
        "check": _cmd_check,
        "scan": _cmd_scan,
        None: _cmd_run,
    }

    commands[args.command](args)
