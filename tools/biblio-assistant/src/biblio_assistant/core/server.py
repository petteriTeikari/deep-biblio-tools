"""Server management for biblio-assistant."""

from typing import Any

import uvicorn

from .app import create_app


class BiblioServer:
    """Manages the web server."""

    def __init__(self, config: dict[str, Any] = None):
        self.config = config or {}
        self.app = create_app(config)

    def run(self):
        """Run the server."""
        server_config = self.config.get("server", {})

        host = server_config.get("host", "127.0.0.1")
        port = server_config.get("port", 8000)
        debug = server_config.get("debug", False)

        # Configure uvicorn
        uvicorn_config = {
            "host": host,
            "port": port,
            "reload": debug,
            "log_level": "debug" if debug else "info",
        }

        # Run server
        uvicorn.run(self.app, **uvicorn_config)
