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