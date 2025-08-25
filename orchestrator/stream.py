import asyncio
from typing import Dict, Tuple

# Map run_id -> (queue, loop)
_streams: Dict[str, Tuple[asyncio.Queue, asyncio.AbstractEventLoop]] = {}


def register(run_id: str, loop: asyncio.AbstractEventLoop | None = None) -> asyncio.Queue:
    """Create a queue for a run and remember its event loop.

    The loop parameter is optional and defaults to the current event loop.
    This makes registration simpler for callers that are already running
    inside the desired loop.
    """
    if loop is None:
        loop = asyncio.get_event_loop()
    q: asyncio.Queue = asyncio.Queue()
    _streams[run_id] = (q, loop)
    return q

def get(run_id: str) -> asyncio.Queue | None:
    pair = _streams.get(run_id)
    return pair[0] if pair else None

def publish(run_id: str, chunk: dict) -> None:
    pair = _streams.get(run_id)
    if not pair:
        return
    q, loop = pair
    # Schedule put on the stored loop so it's safe from other threads
    asyncio.run_coroutine_threadsafe(q.put(chunk), loop)

def close(run_id: str) -> None:
    pair = _streams.get(run_id)
    if not pair:
        return
    q, loop = pair
    if loop.is_closed():
        return
    asyncio.run_coroutine_threadsafe(q.put(None), loop)


def discard(run_id: str) -> None:
    _streams.pop(run_id, None)
