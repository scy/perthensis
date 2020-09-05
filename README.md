# Perthensis: an asynchronous framework for MicroPython.

The Perthensis library uses [`uasyncio`](https://docs.micropython.org/en/latest/library/uasyncio.html) functionality present in recent versions of [MicroPython](https://micropython.org/) to simplify running multiple (background) tasks on your board.

But it's not just about the async stuff.
Additionally, it should be a kind of framework or toolset to make everyday MicroPython tasks easier.

## Example: Heartbeat and counter

```python
from perthensis import Scheduler, Heartbeat

# This class manages your background tasks.
sch = Scheduler()

# Perthensis comes with a convenient class to blink LEDs in a heartbeat rhythm.
# Initialize it and tell it to blink on pin 33.
hb = Heartbeat(33)
# Then tell the scheduler to run its "beat" method as a background task.
sch.create_task(hb.beat)

# Let's write a simple background task that prints ever increasing numbers.
async def counter(scheduler):
    x = 1
    while True:
        print(x)
        # The scheduler will always be passed as first argument to a task and
        # provides access to some convenience methods.
        await scheduler.sleep(1)
        x += 1
# Launch that task, too. This is a shorthand way of calling create_task():
sch(counter)

# Give control to the scheduler. This method will never return.
sch.run_forever()
```

## How does it work?

In version 3.5, Python started supporting `async`/`await` syntax for [coroutines](https://en.wikipedia.org/wiki/Coroutine).
And MicroPython has a subset of that functionality available in version 1.13 and newer.

It's important to know that these are not threads.
They do not actually run in parallel.
Instead, every time an `async` function (in our case, that's usually a background task) calls `await`, its state will be frozen and it will be paused until the function specified after `await` returns.
During that time, other functions can do stuff.
This is what's called [cooperative multitasking](https://en.wikipedia.org/wiki/Cooperative_multitasking):
Functions voluntarily pause themselves, so that other functions can run.

So, when you want to make an LED blink, instead of switching it on, then blocking the processor for some time, then switching it off and blocking again, you instead switch it on and tell Python that you're not interested in running for the next 100 milliseconds.
Then, when that time has passed, your next line of code will run.

You can of course also wait for incoming network connections, changes in the value of input pins etc.

## Design goals

* Make asynchronous MicroPython easy to use.
* Provide convenience functionality for everyday requirements (keep network connections alive, debounce buttons, sync NTP time regularly, etc).
* Preserve the freedom of the library's user as much as feasible.
* Be modular.
* Generate synergies between these modules, but try not to make them depend on one another.

## Requirements

* MicroPython ≥ 1.13

## Status

The scheduler can create new tasks (but not cancel them yet), and there is an LED heartbeat class.
Also, the package's module loading deals gracefully with module files not being present.
This means you only have to copy those modules to your board you actually want to use.

I have, from a [previous proof-of-concept version of this library](https://github.com/scy/krebskandidat/blob/21b4a01a29a1c16d80198dcae60ed6d90e177bb1/src/perthensis.py), a bunch of other functionality that just requires cleanup before it can be published here.
Since I'll be working on a paid project that involves this library, expect that functionality to arrive in the coming days.

## FAQ

### Can I use Perthensis with CircuitPython?

Honestly, I don't know, because I haven't used CircuitPython yet, but I'd like to support it.
Try it and let me know!
CircuitPython doesn't seem to have async support yet, though, and that is (and probably will continue to be) a requirement for most of Perthensis.
You can track the dicussion and implementation process in [CircuitPython's #1380](https://github.com/adafruit/circuitpython/issues/1380).

Nevertheless, issues and pull requests about CircuitPython compatibility are encouraged.

### Can it run on a "normal" Python implementation, e.g. on a Raspberry Pi?

Sigh.

Running MicroPython locally on your laptop or Pi is way harder than it should be, some might even say it's impossible.
There's [the Unix port of MicroPython](https://github.com/micropython/micropython#the-unix-version), but it has its quirks.

I'd say:
Try it, but don't expect too much.
It's more of a problem with MicroPython itself than with this library.

### I have a feature request!

That's not a question.

### Would you be interested in my feature request?

Yes.
Feel free to open an issue.

## Contact

The author is [on Mastodon](https://mastodon.scy.name/@scy) and [on Twitter](https://twitter.com/scy), but creating a GitHub issue works fine, too.
