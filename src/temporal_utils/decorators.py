import asyncio
from datetime import datetime
from functools import wraps
from typing import Any, Awaitable, Callable, TypeVar, cast

from temporalio import activity

F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


def auto_heartbeater(fn: F) -> F:
    """
    ```python
    # Here we use our automatic heartbeater decorator. If this wasn't present, our activity would timeout
    #  if we set the `heartbeat_timeout` option during execution since it isn't heartbeating in our code.

    @activity.defn
    @auto_heartbeater
    async def wait_for_cancel_activity() -> str:
        # Wait forever, catch the cancel, and return some value
        try:
            await asyncio.Future()
            raise RuntimeError("unreachable")
        except asyncio.CancelledError:
            return "activity cancelled!"
    ```
    """

    # We want to ensure that the type hints from the original callable are
    # available via our wrapper, so we use the functools wraps decorator
    @wraps(fn)
    async def wrapper(*args, **kwargs):  # type: ignore
        heartbeat_timeout = activity.info().heartbeat_timeout
        heartbeat_task = None
        if heartbeat_timeout:
            # Heartbeat twice as often as the timeout
            heartbeat_task = asyncio.create_task(
                _heartbeat_every(heartbeat_timeout.total_seconds() / 2)
            )
        try:
            return await fn(*args, **kwargs)
        finally:
            if heartbeat_task:
                heartbeat_task.cancel()
                # Wait for heartbeat cancellation to complete
                await asyncio.wait([heartbeat_task])

    return cast(F, wrapper)


async def _heartbeat_every(delay: float, *details: Any) -> None:
    # Heartbeat every so often while not cancelled
    while True:
        await asyncio.sleep(delay)
        print(f"Heartbeating at {datetime.now()}")
        activity.heartbeat(*details)
