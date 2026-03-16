import os
import socket
from dotenv import load_dotenv

# Load .env file
load_dotenv()


class ClientSettings:
    """Client configuration from environment variables."""
    
    BACKEND_URL: str = os.getenv("BACKEND_URL", "http://192.168.0.206:8000")
    HOST_ID: str | None = os.getenv("SMART_MONITOR_HOST_ID")
    
    @classmethod
    def get_host_id(cls) -> str:
        """Get host ID from env or generate one from hostname."""
        if cls.HOST_ID:
            return cls.HOST_ID
        return socket.gethostname()
