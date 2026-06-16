import asyncio
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class MonitorWSManager:
    """Manages WebSocket connections for the system dashboard."""

    def __init__(self):
        self._connections: list[WebSocket] = []
        self._heartbeat_task: asyncio.Task | None = None

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._connections.append(ws)
        logger.info(f"Monitor WS connected, total: {len(self._connections)}")

    def disconnect(self, ws: WebSocket):
        if ws in self._connections:
            self._connections.remove(ws)
        logger.info(f"Monitor WS disconnected, total: {len(self._connections)}")

    async def broadcast(self, data: dict):
        dead = []
        for ws in self._connections:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    def start_heartbeat(self, interval: int = 30):
        if self._heartbeat_task is None:
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop(interval))

    async def _heartbeat_loop(self, interval: int):
        while True:
            await asyncio.sleep(interval)
            await self.broadcast({"type": "ping"})


# Global singleton
ws_manager = MonitorWSManager()
