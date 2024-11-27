from __future__ import annotations

import abc
import asyncio
import collections
import concurrent.futures
import dataclasses
import inspect
import threading
import typing
import weakref
import sys

from . import base
from .base import SynchronousDecorated

type Cache[** Param, Ret] = dict[Key, Exit[Param, Ret]]
type Expire = float
type Future[Result] = asyncio.Future[Result] | concurrent.futures.Future[Result]
type GenerateKey[** Params, Key] = typing.Callable[Params, Key]
type Key = typing.Hashable
type Lock = asyncio.Lock | threading.Lock


@dataclasses.dataclass(frozen=True, kw_only=True)
class BaseData[** Param, Ret](base.BaseData[Param, Ret], abc.ABC):
@dataclasses.dataclass(frozen=True, kw_only=True)
class CooperativeData[** Param, Ret](BaseData[Param, Ret], abc.ABC): ...
@dataclasses.dataclass(frozen=True, kw_only=True)
class SynchronousData[** Param, Ret](BaseData[Param, Ret], abc.ABC): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class DecoratedData[** Param, Ret](BaseData[Param, Ret], base.DecoratedData[Param, Ret], abc.ABC):
@dataclasses.dataclass(frozen=True, kw_only=True)
class CooperativeDecoratedData[** Param, Ret](CooperativeData[Param, Ret], DecoratedData[Param, Ret], abc.ABC): ...
@dataclasses.dataclass(frozen=True, kw_only=True)
class SynchronousDecoratedData[** Param, Ret](SynchronousData[Param, Ret], DecoratedData[Param, Ret], abc.ABC): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class EnterData[** Param, Ret](BaseData[Param, Ret], abc.ABC):
    lock: Lock
@dataclasses.dataclass(frozen=True, kw_only=True)
class CooperativeEnterData[** Param, Ret](EnterData[Param, Ret], CooperativeDecoratedData[Param, Ret], abc.ABC):
    lock: asyncio.Lock = dataclasses.field(default_factory=asyncio.Lock)
@dataclasses.dataclass(frozen=True, kw_only=True)
class SynchronousEnterData[** Param, Ret](EnterData[Param, Ret], SynchronousDecoratedData[Param, Ret], abc.ABC):
    lock: threading.Lock = dataclasses.field(default_factory=threading.Lock)


@dataclasses.dataclass(frozen=True, kw_only=True)
class ExitData[** Param, Ret](BaseData[Param, Ret], abc.ABC):
    future: Future[base.Raise | Ret]
@dataclasses.dataclass(frozen=True, kw_only=True)
class CooperativeExitData[** Param, Ret](ExitData[Param, Ret], CooperativeEnterData[Param, Ret], abc.ABC):
    future: asyncio.Future[base.Raise | Ret]
@dataclasses.dataclass(frozen=True, kw_only=True)
class SynchronousExitData[** Param, Ret](ExitData[Param, Ret], SynchronousEnterData[Param, Ret], abc.ABC):

@dataclasses.dataclass(frozen=True, kw_only=True)
class Cooperative[** Param, Ret](base.Cooperative[Param, Ret], abc.ABC): ...
@dataclasses.dataclass(frozen=True, kw_only=True)
class Synchronous[** Param, Ret](base.Synchronous[Param, Ret], abc.ABC): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class Decorated[** Param, Ret, Enter](base.Decorated[Param, Ret], DecoratedData[Param, Ret], abc.ABC):
    enter: Enter
    enter_by_instance: weakref.WeakKeyDictionary[
        base.Instance, Enter
    ] = dataclasses.field(default_factory=weakref.WeakKeyDictionary)

    def __get__(self, instance, owner) -> typing.Self:
        return dataclasses.replace(
            (decorated := dataclasses.replace(self, decoratee=self.decoratee.__get__(instance, owner))),
            enter=self.enter_by_instance.setdefault(instance, self.enter_t(decorated=decorated)),
        )

@dataclasses.dataclass(frozen=True, kw_only=True)
class CooperativeDecorated[** Param, Ret, Enter](
    Cooperative[Param, Ret],
    Decorated[Param, Ret, Enter],
    base.CooperativeDecorated[Param, Ret],
): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class SynchronousDecorated[** Param, Ret, SynchronousEnter](
    Synchronous[Param, Ret],
    Decorated[Param, Ret, SynchronousEnter],
    base.SynchronousDecorated[Param, Ret],
): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class Enter[** Param, Ret, Exit](base.Enter[Param, Ret], abc.ABC):
    exit_by_key: collections.OrderedDict[Key, Exit] = dataclasses.field(
        default_factory=collections.OrderedDict,
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class CooperativeEnter[** Param, Ret, CooperativeExit](
    Cooperative[Param, Ret],
    Enter[Param, Ret, CooperativeExit],
    base.CooperativeEnter[Param, Ret],
):

    @property
    def future_t(self) -> type[asyncio.Future[Ret]]:
        return asyncio.Future

    @typing.final
    async def __call__(self, *args: Param.args, **kwargs: Param.kwargs) -> (
        (base.CooperativeDecoratee[Param, Ret]) | (CooperativeExit, base.CooperativeDecoratee[Param, Ret])
    ):
        key = self.decorated.decorator.generate_key(*args, **kwargs)

        exit_ = self.exit_by_key.pop(key, None)
        while self.size <= len(self.future_by_key):
            self.future_by_key.popitem(last=False)
        if future is not None:
            self.future_by_key[key] = future
            return (lambda *_args, **_kwargs: future),
        else:
            exit_: CooperativeExit = self.exit_t[Param, Ret](
                decoratee=self.decoratee,
                future=self.future_by_key.setdefault(key, asyncio.Future()),
                generate_key=self.generate_key,
                lock=self.lock,
                size=self.size,
            )
            return exit_, self.decoratee


@dataclasses.dataclass(frozen=True, kw_only=True)
class SynchronousEnter[** Param, Ret](
    Synchronous[Param, Ret],
    Enter[Param, Ret],
    base.SynchronousEnter[Param, Ret],
    SynchronousEnterData[Param, Ret],
):

    @property
    def future_t(self) -> type[concurrent.futures.Future[Ret]]:
        return concurrent.futures.Future

    def __call__(self, *args: Param.args, **kwargs: Param.kwargs) -> (
        (base.SynchronousDecoratee[Param, Ret]) | (SynchronousExit[Param, Ret], base.SynchronousDecoratee[Param, Ret])
    ):
        key = self.generate_key(*args, **kwargs)

        with self.lock:
            future = self.future_by_key.pop(key, None)
            while self.size <= len(self.future_by_key):
                self.future_by_key.popitem(last=False)
            if future is not None:
                self.future_by_key[key] = future
                return tuple([lambda *_args, **_kwargs: future.result()])
            else:
                exit_: SynchronousExit = self.exit_t[Param, Ret](
                    decoratee=self.decoratee,
                    future=self.future_by_key.setdefault(key, concurrent.futures.Future()),
                    generate_key=self.generate_key,
                    lock=self.lock,
                    size=self.size,
                )
                return exit_, self.decoratee


@dataclasses.dataclass(frozen=True, kw_only=True)
class Exit[** Param, Ret](base.Exit[Param, Ret], abc.ABC): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class CooperativeExit[** Param, Ret](Cooperative[Param, Ret], Exit[Param, Ret], base.CooperativeExit[Param, Ret]):
    async def __call__(self, result: base.Raise | Ret) -> ():
        self.future.set_result(result)

        return tuple()
@dataclasses.dataclass(frozen=True, kw_only=True)
class SynchronousExit[** Param, Ret](
    Synchronous[Param, Ret],
    Exit[Param, Ret],
    SynchronousEnterData[Param, Ret],
    base.SynchronousExit[Param, Ret],
):

    def __call__(self, result: base.Raise | Ret) -> ():
        self.future.set_result(result)

        return tuple()


@dataclasses.dataclass(frozen=True, kw_only=True)
class Decorator[** Param, Ret](Base[Param, Ret], base.Decorator[Param, Ret]):
    generate_key: GenerateKey[Param] = lambda *args, **kwargs: (tuple(args), tuple(sorted([*kwargs.items()])))
    size: int = sys.maxsize

    #@typing.overload
    #def __call__(self, decoratee: base.CooperativeDecoratee[Param, Ret], /) -> CooperativeDecorated[Param, Ret]: ...
    #@typing.overload
    #def __call__(self, decoratee: base.SynchronousDecoratee[Param, Ret], /) -> SynchronousDecorated[Param, Ret]: ...
    #@typing.override
    #def __call__(self, decoratee, /):
    #    if inspect.iscoroutinefunction(decoratee):
    #        decorated_t: typing.Callable[..., CooperativeDecorated] = self.cooperative_decorated_t
    #    else:
    #        decorated_t: typing.Callable[..., SynchronousDecorated] = self.synchronous_decorated_t

    #    return decorated_t(
    #        decoratee=decoratee,
    #        generate_key=self.generate_key,
    #        size=self.size,
    #        __doc__=str(decoratee.__doc__),
    #        __module__=str(decoratee.__module__),
    #        __name__=str(decoratee.__name__),
    #        __qualname__=str(decoratee.__qualname__),
    #    )
