"""In-process async event bus.

Every hub module publishes through `publish(event)`; never write to sockets directly.
Subscribers (ws gateway, state, settlement, guard) each get their own asyncio.Queue.
"""
import asyncio
import logging

from hizashi_shared.models import Event

log = logging.getLogger("hizashi.bus")

QUEUE_SIZE = 5000
_subscribers: set[asyncio.Queue] = set()


def publish(event: Event) -> None:
    """Fan out to every subscriber. Non-blocking; a full (stuck) queue drops the event."""
    for q in list(_subscribers):
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            log.warning("subscriber queue full, dropped %s", event.type)


def subscribe(maxsize: int = QUEUE_SIZE) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=maxsize)
    _subscribers.add(q)
    return q


def unsubscribe(q: asyncio.Queue) -> None:
    _subscribers.discard(q)


def subscriber_count() -> int:
    return len(_subscribers)
