from __future__ import annotations

import abc
import asyncio
import collections
import concurrent.futures
import dataclasses
import threading
import typing
import weakref
import sys

from . import base

type GenerateKey[** Params, Key] = typing.Callable[Params, Key]
type Key = typing.Hashable
type Lock = asyncio.Lock | threading.Lock


@dataclasses.dataclass(frozen=True, kw_only=True)
class Cooperative(base.Cooperative, abc.ABC): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class Synchronous(base.Synchronous, abc.ABC): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class Base(base.Base, abc.ABC): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class Exit[** Param, Ret, Future, Decoratee, Exit, Enter, Decorated, Decorator](
    base.Exit[Param, Ret, Decoratee, Exit, Enter, Decorated, Decorator],
    abc.ABC,
):
    future: Future


@dataclasses.dataclass(frozen=True, kw_only=True)
class CooperativeExit[** Param, Ret, Enter, Decorated, Decorator](
    Cooperative,
    Exit[
        Param,
        Ret,
        asyncio.Future[Ret],
        base.CooperativeDecoratee[Param, Ret],
        typing.Self,
        Enter,
        Decorated,
        Decorator,
    ],
    base.CooperativeExit[Param, Ret, Enter, Decorated, Decorator],
):
    future: asyncio.Future[Ret] = dataclasses.field(default_factory=asyncio.Future)

    async def __call__(self, result: base.Raise | Ret) -> ():
        self.future.set_result(result)

        return tuple()


@dataclasses.dataclass(frozen=True, kw_only=True)
class SynchronousExit[** Param, Ret, Enter, Decorated, Decorator](
    Synchronous,
    Exit[
        Param,
        Ret,
        concurrent.futures.Future[Ret],
        base.SynchronousDecoratee[Param, Ret],
        typing.Self,
        Enter,
        Decorated,
        Decorator,
    ],
    base.SynchronousExit[Param, Ret, Enter, Decorated, Decorator],
):
    future: concurrent.futures.Future[Ret] = dataclasses.field(default_factory=concurrent.futures.Future)

    def __call__(self, result: base.Raise | Ret) -> ():
        self.future.set_result(result)

        return tuple()

@dataclasses.dataclass(frozen=True, kw_only=True)
class Enter[** Param, Ret, Lock, Decoratee, Exit, Enter, Decorated, Decorator](
    Base,
    base.Enter[Param, Ret, Decoratee, Exit, typing.Self, Decorated, Decorator],
    abc.ABC,
):
    exit_by_key: collections.OrderedDict[Key, Exit] = dataclasses.field(
        default_factory=collections.OrderedDict,
    )
    lock: Lock


@dataclasses.dataclass(frozen=True, kw_only=True)
class CooperativeEnter[** Param, Ret, Decorated, Decorator](
    Cooperative,
    Enter[
        Param,
        Ret,
        asyncio.Lock,
        base.CooperativeDecoratee[Param, Ret],
        CooperativeExit[Param, Ret, typing.Self, Decorated, Decorator],
        typing.Self,
        Decorated,
        Decorator,
    ],
    base.CooperativeEnter[Param, Ret, Decorated, Decorator],
):
    type Decoratee = base.CooperativeDecoratee[Param, Ret]
    type Exit = CooperativeExit[Param, Ret, typing.Self, Decorated, Decorator]
    type Enter = typing.Self

    @typing.final
    async def __call__(self, *args: Param.args, **kwargs: Param.kwargs) -> tuple[Decoratee] | tuple[Exit, Decorator]:
        key = self.decorated.decorator.generate_key(*args, **kwargs)

        async with self.lock:
            exit_ = self.exit_by_key.pop(key, None)
            while self.decorated.decorator.size <= len(self.exit_by_key):
                self.exit_by_key.popitem(last=False)
            if exit_ is None:
                exit_ = self.exit_by_key[key] = CooperativeExit(enter=self)
                return exit_, self.decorated.decoratee
            else:
                self.exit_by_key[key] = exit_
                return (lambda *_args, **_kwargs: exit_.future),


@dataclasses.dataclass(frozen=True, kw_only=True)
class SynchronousEnter[** Param, Ret, Decorated, Decorator](
    Synchronous,
    Enter[
        Param,
        Ret,
        threading.Lock,
        base.SynchronousDecoratee[Param, Ret],
        SynchronousExit[Param, Ret, typing.Self, Decorated, Decorator],
        typing.Self,
        Decorated,
        Decorator,
    ],
    base.SynchronousEnter[Param, Ret, Decorated, Decorator],
):
    type Decoratee = base.SynchronousDecoratee[Param, Ret]
    type Exit = SynchronousExit[Param, Ret, typing.Self, Decorated, Decorator]
    type Enter = typing.Self

    def __call__(self, *args: Param.args, **kwargs: Param.kwargs) -> tuple[Decoratee] | tuple[Exit, Decorator]:
        key = self.decorated.decorator.generate_key(*args, **kwargs)

        with self.lock:
            exit_ = self.exit_by_key.pop(key, None)
            while self.decorated.decorator.size <= len(self.exit_by_key):
                self.exit_by_key.popitem(last=False)
            if exit_ is None:
                exit_ = self.exit_by_key[key] = SynchronousExit(enter=self)
                return exit_, self.decorated.decoratee
            else:
                self.exit_by_key[key] = exit_
                return (lambda *_args, **_kwargs: exit_.future.result()),


@dataclasses.dataclass(frozen=True, kw_only=True)
class Decorated[** Param, Ret, Lock, Decoratee, Exit, Enter, Decorated, Decorator](
    base.Decorated[Param, Ret, Decoratee, Exit, Enter, Decorated, Decorator],
    abc.ABC,
):
    lock: Lock
    enter_by_instance: weakref.WeakKeyDictionary[
        base.Instance, Enter
    ] = dataclasses.field(default_factory=weakref.WeakKeyDictionary)
    instance: base.Instance | None = None

    def __get__(self, instance, owner) -> typing.Self:
        # TODO: Left off changing `enter` to `instance`. The way a memoized `enter` is created needs to be debugged.
        return dataclasses.replace(self, decoratee=self.decoratee.__get__(instance, owner), instance=instance)

@dataclasses.dataclass(frozen=True, kw_only=True)
class CooperativeDecorated[** Param, Ret, Decorator](
    Cooperative,
    Decorated[
        Param,
        Ret,
        asyncio.Lock,
        base.CooperativeDecoratee[Param, Ret],
        CooperativeExit[Param, Ret, CooperativeEnter[Param, Ret, typing.Self, Decorator], typing.Self, Decorator],
        CooperativeEnter[Param, Ret, typing.Self, Decorator],
        typing.Self,
        Decorator,
    ],
    base.CooperativeDecorated[Param, Ret, Decorator],
):
    lock: asyncio.Lock = dataclasses.field(default_factory=asyncio.Lock)


@dataclasses.dataclass(frozen=True, kw_only=True)
class SynchronousDecorated[** Param, Ret, Decorator](
    Synchronous,
    Decorated[
        Param,
        Ret,
        threading.Lock,
        base.SynchronousDecoratee[Param, Ret],
        SynchronousExit[Param, Ret, SynchronousEnter[Param, Ret, typing.Self, Decorator], typing.Self, Decorator],
        SynchronousEnter[Param, Ret, typing.Self, Decorator],
        typing.Self,
        Decorator,
    ],
    base.SynchronousDecorated[Param, Ret, Decorator],
):
    lock: threading.Lock = dataclasses.field(default_factory=threading.Lock)


@dataclasses.dataclass(frozen=True, kw_only=True)
class Decorator[** Param, Ret](
    base.Decorator[
        Param,
        Ret,
        CooperativeDecorated[Param, Ret, typing.Self],
        SynchronousDecorated[Param, Ret, typing.Self],
    ]
):
    generate_key: GenerateKey[Param] = lambda *args, **kwargs: (tuple(args), tuple(sorted([*kwargs.items()])))
    size: int = sys.maxsize
