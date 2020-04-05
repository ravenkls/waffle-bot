import asyncio
import datetime


async def _wait_until(date, callback, args=None, kwargs=None):
    difference = max(0, (date - datetime.datetime.now()).total_seconds())
    await asyncio.sleep(difference)

    args = () if args is None else args
    kwargs = {} if kwargs is None else kwargs

    if asyncio.iscoroutinefunction(callback):
        await callback(*args, **kwargs)
    else:
        callback(*args, **kwargs)


def start_waiting(*, date, callback, args=None, kwargs=None):
    """Start a background task which waits until a datetime has been
    reached and then execute a callback."""
    loop = asyncio.get_event_loop()
    loop.create_task(_wait_until(date, callback, args, kwargs))
