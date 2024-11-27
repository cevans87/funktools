import asyncio
import typing

import pytest

import funktools._internal.base as base  # noqa


@pytest.fixture(autouse=True)
def event_loop() -> asyncio.AbstractEventLoop:
    """All async tests execute eagerly.

    Upon task creation return, we can be sure that the task has gotten to a point that it is either blocked or done.
    """

    eager_loop = asyncio.new_event_loop()
    eager_loop.set_task_factory(asyncio.eager_task_factory)
    yield eager_loop
    eager_loop.close()


def test_base() -> None:
    @base.Decorator()
    def foo():
        ...

    foo()


@pytest.mark.asyncio
async def test_async_method() -> None:

    class Foo:

        @base.Decorator()
        async def bar(self, v):
            return locals()

    foo = Foo()
    x = await foo.bar(2)

    assert await (foo := Foo()).bar(42) == {'self': foo, 'v': 42}


def test_multi_method() -> None:

    class Foo:

        @base.Decorator()
        def bar(self, v):
            return locals()

    assert (foo := Foo()).bar(42) == {'self': foo, 'v': 42}


@pytest.mark.asyncio
async def test_async_classmethod() -> None:

    class Foo:

        @classmethod
        @base.Decorator()
        async def bar(cls, v):
            return locals()

    assert await Foo().bar(42) == {'cls': Foo, 'v': 42}


def test_multi_classmethod() -> None:

    class Foo:

        @classmethod
        @base.Decorator()
        def bar(cls, v):
            return locals()

    assert Foo().bar(42) == {'cls': Foo, 'v': 42}


@pytest.mark.asyncio
async def test_async_staticmethod() -> None:

    class Foo:
        v: typing.ClassVar[int]

        @staticmethod
        @base.Decorator()
        async def bar(v):
            return locals()

    assert await Foo.bar(42) == {'v': 42}


def test_multi_staticmethod() -> None:

    class Foo:

        @staticmethod
        @base.Decorator()
        def bar(v):
            return locals()

    assert Foo.bar(42) == {'v': 42}
