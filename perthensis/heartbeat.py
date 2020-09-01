"""Toggle an output pin in a repeating pattern similar to a human heartbeat."""


from machine import Pin, Signal


PATTERN = [50, 100, 100, 750]
"""A list of millisecond delay values specifying on/off times.

Values at even indexes (0, 2, ...) specify how long the LED should be on, while
values at odd indexes (1, 3, ...) specify how long it should be off.  The list
could be longer or shorter than the default four items.  Also, the default list
adds up to 1000 milliseconds on purpose, but that's not required either.
"""


class Heartbeat:
    """Toggle an output pin in a repeating pattern."""

    def __init__(self, pin_id, invert=False):
        """Initialize a new heartbeat.

        Args:
            pin_id (int): Which pin to toggle.
            invert (bool): Whether the pin should be considered "active low".
                See the ``invert`` parameter of MicroPython's ``Signal``.
        """
        self._sig = Signal(pin_id, Pin.OUT, invert=invert)
        self._sig.off()

    async def beat(self, sch):
        """Perform the heartbeat.

        Pass this function to ``create_task`` of Perthensis' ``Scheduler``.

        Note that it will set the pin to "on" for 2 seconds before starting the
        pattern. This is supposed to make board resets clearly visible.
        """
        self._sig.on()
        await sch.sleep(2)

        while True:
            for idx, delay in enumerate(PATTERN):
                self._sig.on() if idx % 2 == 0 else self._sig.off()
                await sch.sleep_ms(delay)
