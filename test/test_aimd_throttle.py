import asyncio
import inspect
import pytest

import funktools

module = inspect.getmodule(funktools.AimdThrottle)


# TODO: Multi tests are missing. This suite heavily relies upon determining whether coroutines are running vs suspended
#  (via asyncio.eager_task_factory). Ideally, similar functionality exists for threading. Otherwise, we need to find a
#  way to determine that thread execution has reached a certain point. Ideally without mocking synchronization
#  primitives.


@pytest.fixture(autouse=True)
def event_loop() -> asyncio.AbstractEventLoop:
    """All async tests execute eagerly.

    Upon task creation return, we can be sure that the task has gotten to a point that it is either blocked or done.
    """

    eager_loop = asyncio.new_event_loop()
    eager_loop.set_task_factory(asyncio.eager_task_factory)
    yield eager_loop
    eager_loop.close()


@pytest.mark.asyncio
async def test_throttle_additive_increase_adds_1() -> None:
    event = asyncio.Event()
    n_running = 0

    @funktools.AimdThrottle()
    async def foo():
        nonlocal n_running
        n_running += 1
        await event.wait()
        n_running -= 1

        for i in range(1, 10):
            event.clear()
            async with asyncio.TaskGroup() as tg:
                for j in range(i + 1):
                    tg.create_task(foo())
                assert n_running == i
                event.set()
