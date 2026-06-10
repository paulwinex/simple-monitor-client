import os
import socket
from dotenv import load_dotenv
from pathlib import Path

# Load .env file
env_file = Path.cwd().joinpath(".env")
if not env_file.exists():
    env_file = None
else:
    print('Load env file', env_file)
load_dotenv(env_file)


class ClientSettings:
    """Client configuration from environment variables."""
    
    BACKEND_URL: str = os.getenv("SIMPLE_MONITOR_BACKEND_URL", "http://localhost:8000")
    HOST_ID: str | None = os.getenv("SIMPLE_MONITOR_HOST_ID")
    
    @classmethod
    def get_host_id(cls) -> str:
        """Get host ID from env or generate one from hostname."""
        if cls.HOST_ID:
            return cls.HOST_ID
        return socket.gethostname()
