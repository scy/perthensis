from machine import disable_irq, enable_irq, Pin, Timer
from micropython import schedule


class TimerDebounce:
    """Debounce pins using change and timer interrupts."""
    RUNNING_NONE = 0
    RUNNING_SOME = 1
    RUNNING_CHECKING = 2

    def __init__(self, timer_id):
        """Create a new debouncer for one or more pins.

        args:
            timer_id: Will be passed to ``machine.Timer`` and should therefore
                be a valid and unused timer ID.
        """
        self._timer = Timer(timer_id)
        self._pins = {}
        self._timer_handler_bound = self._timer_handler

        # This keeps track of whether there are some debouncing jobs (and thus
        # the interval timer) running or not. 2-state logic would probably be
        # sufficient, but 3-state logic makes the loop in ``settle_checker``
        # work even if a new job is added while it's running.
        self._running_jobs = self.RUNNING_NONE

    def _change_handler(self, pin):
        """Scheduled(!) every time a pin's state changes."""
        irq = disable_irq()
        try:
            # Start the timer interrupt, if it's not already running.
            if self._running_jobs == self.RUNNING_NONE:
                self._timer.init(period=1, mode=Timer.PERIODIC,
                                 callback=self._timer_handler_bound)
            # Whatever this was before, now there's at least one running.
            self._running_jobs = self.RUNNING_SOME
        finally:
            enable_irq(irq)

    def _timer_handler(self, timer):
        """This is the callback of the settle timer interrupt."""
        schedule(self._settle_checker, None)

    def _settle_checker(self, _):
        """Scheduled(!) each ms while we're debouncing something."""
        self._running_jobs = self.RUNNING_CHECKING
        # Most of the following code could possibly be moved into the
        # ``DebouncedTimer`` class for separation of concerns, but we should
        # probably do some benchmarking first.
        for pin_id, pin in self._pins.items():
            if pin._settle_wait is not None:  # pin is being debounced
                if pin._settle_wait <= 0:     # it has settled now
                    pin._settle_wait = None
                    if pin._value != pin._previous:
                        pin._previous = pin._value
                        pin._callback(pin_id, pin._value)
                else:
                    # Since no interrupt sets this to None, we can safely
                    # assume that it's an int.
                    pin._settle_wait -= 1
                    # There is at least one running job left.
                    self._running_jobs = self.RUNNING_SOME

        # If there are no debouncing jobs left, disable the timer.
        irq = disable_irq()
        try:
            if self._running_jobs == self.RUNNING_CHECKING:
                # Didn't see running jobs, and no new ones were inserted
                # meanwhile via an interrupt.
                self._running_jobs = self.RUNNING_NONE
                self._timer.deinit()
        finally:
            enable_irq(irq)

    def add_pin(self, pin_id, callback, pull=None, threshold=20):
        """Add a new pin to be debounced.

        args:
            pin_id: The number of the pin.
            callback: The function to call once the pin has settled. It will
                receive two parameters: The pin ID and the value.
            pull: Pull-up/-down configuration. Pass the usual ``Pin.PULL_*``
                constants.
            threshold: After how many milliseconds of having the same value
                should the pin be considered settled?
        """
        if pin_id in self._pins:
            raise IndexError('pin {0} already present'.format(pin_id))
        self._pins[pin_id] = DebouncedPin(
                self, pin_id, callback, pull, threshold)


class DebouncedPin:
    """Represents a single pin to be debounced by ``TimerDebounce``.

    You should not create new instances of this class yourself; use the
    ``TimerDebounce.add_pin()`` method instead.
    """

    def __init__(self, debouncer, pin_id, callback, pull, threshold_ms):
        self._debounce_handler = debouncer._change_handler
        self._id = pin_id
        self._callback = callback
        self._threshold = int(threshold_ms)
        self._settle_wait = None
        self._previous = None
        self._value = None

        # Configure the pin and its interrupt handler.
        self._pin = Pin(pin_id, Pin.IN, pull)
        self._pin.irq(self._irq_handler, Pin.IRQ_FALLING | Pin.IRQ_RISING)

    def _irq_handler(self, pin):
        """This is the pin change interrupt handler."""
        self._settle_wait = self._threshold
        self._value = pin.value()
        try:
            schedule(self._debounce_handler, self)
        except RuntimeError:
            # Probably "schedule queue full", but it doesn't raise a more
            # specific exception. :( Best thing we can do is probably to just
            # ignore it, however sad that is.
            pass


class DebouncedRotary:
    """Read a rotary encoder in a debounced way.

    This implementation borrows a lot from
    <https://www.best-microcontroller-projects.com/rotary-encoder.html>."""

    VALID_TRANSITIONS = (False, True, True, False, True, False, False, True,
                         True, False, False, True, False, True, True, False)

    def __init__(self, clk_id, data_id, callback,
                 pull=None, invert=False, reverse=False):
        """Create a new debouncer for a single rotary encoder.

        args:
            clk_id: Which pin number is the "CLK" pin of the encoder connected
                to? If yours is of the "ABC" style, find one of the two
                contacts it has that connect to the third while turning it and
                use that.
            data_id: Which pin number is the "DATA" pin connected to? If yours
                is of the "ABC" style, choose the other of the two contacts
                that connect to a third while turning and use that.
            callback: A function or method that will be called with either 1 or
                -1 as its single parameter every time the encoder is being
                moved one step.
            pull: If your two encoder pins should be pulled high or low, set
                this to one of the ``Pin.PULL_*`` constants.
            invert: If your encoder pins are normally low and become high while
                the encoder is being moved, set this to True.
            reverse: Set this to True to reverse how the turning direction is
                being interpreted.
        """
        self._clk = Pin(clk_id, Pin.IN, pull)
        self._dat = Pin(data_id, Pin.IN, pull)
        self._invert = 0x03 if invert else 0x00
        self._reverse = -1 if reverse else 1
        self._callback = callback
        self._state = 0x00

        self._clk.irq(self._irq_handler, Pin.IRQ_FALLING | Pin.IRQ_RISING)
        self._dat.irq(self._irq_handler, Pin.IRQ_FALLING | Pin.IRQ_RISING)

    def _irq_handler(self, pin):
        newstate = (
                (self._state << 2)  # move the previous state to the left
                # and then add the current values
                | (((self._dat.value() << 1) | self._clk.value())
                   ^ self._invert)  # invert both if we need to
                ) & 0x0f  # and make sure to only keep the rightmost 4 bit
        if self.VALID_TRANSITIONS[newstate]:
            self._state = newstate
            try:
                if self._state == 0x07:  # moved clockwise
                    schedule(self._callback, self._reverse)
                elif self._state == 0x0b:  # moved counterclockwise
                    schedule(self._callback, -1 * self._reverse)
            except RuntimeError:
                # Again, this might just be "schedule queue full". Ignore. :(
                pass
