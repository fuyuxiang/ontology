import asyncio
import logging
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)

EventHandler = Callable[[dict], Awaitable[None]]


class EventBus:
    """Simple async event bus for decoupled module communication."""

    def __init__(self):
        self._subscribers: dict[str, list[EventHandler]] = {}

    def subscribe(self, event_type: str, handler: EventHandler):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    async def emit(self, event_type: str, data: dict[str, Any]):
        handlers = self._subscribers.get(event_type, [])
        for handler in handlers:
            try:
                asyncio.create_task(handler(data))
            except Exception as e:
                logger.error(f"EventBus error dispatching {event_type}: {e}")


# Global singleton
event_bus = EventBus()
