from fastapi import WebSocket


class WebSocketConnectionManager:
    """Track active Orbyntiq WebSocket connections."""

    def __init__(self) -> None:
        self._active_connections: set[WebSocket] = set()

    @property
    def active_connection_count(self) -> int:
        """Return the number of currently connected WebSocket clients."""

        return len(self._active_connections)

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a WebSocket connection."""

        await websocket.accept()
        self._active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection if it is currently registered."""

        self._active_connections.discard(websocket)


connection_manager = WebSocketConnectionManager()
