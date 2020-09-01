"""Manage tasks running in a "cooperative multitasking" style."""


# Import MicroPython's uasyncio or fall back to standard Python asyncio.
try:
    import uasyncio
except ImportError:
    try:
        import asyncio as uasyncio
    except ImportError:
        raise ImportError(
            'Neither the `uasyncio` nor the `asyncio` module could be loaded. '
            'uasyncio support requires MicroPython > 1.12 (possibly nightly).'
        )


class Scheduler:
    """Manage tasks running in a "cooperative multitasking" style.

    Note:
        Scheduler instances are callable. This is an alias for ``create_task``.
    """

    def __init__(self):
        self._tasks = []

        # We alias some of asyncio's functions.
        self.run = uasyncio.run
        self.sleep = uasyncio.sleep
        self.wait_for = uasyncio.wait_for

        # Standard asyncio doesn't have sleep_ms, so we shim it.
        self.sleep_ms = getattr(uasyncio, 'sleep_ms',
                                lambda ms: uasyncio.sleep(ms / 1000))

    async def _wait_loop(self, interval):
        while True:
            await self.sleep_ms(interval)

    def create_task(self, coro, *args):
        """Launch a new task.

        Args:
            coro: An async function (or method) to be started. It will receive
                this scheduler instance as its first argument.
            args: Additional arguments that the coro should receive.

        Returns:
            The task that has been created.
        """
        task = uasyncio.create_task(coro(self, *args))
        self._tasks.append(task)
        return task

    # Make it easy to call create_task().
    __call__ = create_task

    def run_forever(self):
        """Give control (permanently) to the background tasks defined."""
        self.run(self._wait_loop(10_000))
