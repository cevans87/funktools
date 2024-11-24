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

type Cache[** Param, Ret] = dict[Key, Exit[Param, Ret]]
type Expire = float
type Future[Return] = asyncio.Future[Return] | concurrent.futures.Future[Return]
type GenerateKey[** Params, Key] = typing.Callable[Params, Key]
type Key = typing.Hashable


@dataclasses.dataclass(frozen=True, kw_only=True)
class Base[** Param, Ret](base.Base[Param, Ret], abc.ABC):
    generate_key: GenerateKey
    size: int


@dataclasses.dataclass(frozen=True, kw_only=True)
class Async[** Param, Ret](Base[Param, Ret], base.Async[Param, Ret], abc.ABC):
    lock: asyncio.Lock = dataclasses.field(default_factory=asyncio.Lock)


@dataclasses.dataclass(frozen=True, kw_only=True)
class Multi[** Param, Ret](Base[Param, Ret], base.Multi[Param, Ret], abc.ABC):
    lock: threading.Lock = dataclasses.field(default_factory=threading.Lock)


@dataclasses.dataclass(frozen=True, kw_only=True)
class Context[** Param, Ret](Base[Param, Ret], base.Context[Param, Ret], abc.ABC): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class Enter[** Param, Ret](Base[Param, Ret], base.Enter[Param, Ret], abc.ABC):
    future_by_key: collections.OrderedDict[Key, Future[Ret]] = dataclasses.field(
        default_factory=collections.OrderedDict,
    )

    @property
    @abc.abstractmethod
    def future_t(self) -> type[Future[Ret]]: ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class Exit[** Param, Ret](Base[Param, Ret], base.Exit[Param, Ret], abc.ABC):
    future: Future[base.Raise | Ret]


@dataclasses.dataclass(frozen=True, kw_only=True)
class AsyncEnter[** Param, Ret](Async[Param, Ret], Enter[Param, Ret], base.AsyncEnter[Param, Ret]):

    @property
    def future_t(self) -> type[asyncio.Future[Ret]]:
        return asyncio.Future

    async def __call__(self) -> (
        tuple[base.AsyncDecoratee[Param, Ret]] |
        tuple[AsyncExit[Param, Ret], base.AsyncDecoratee[Param, Ret]]
    ):
        key = self.generate_key(*self.args, **self.kwargs)

        async with self.lock:
            future = self.future_by_key.pop(key, None)
            while self.size <= len(self.future_by_key):
                self.future_by_key.popitem(last=False)
            if future is not None:
                self.future_by_key[key] = future
                return tuple([lambda *_args, **_kwargs: future])
            else:
                exit_context = self.exit_t(
                    args=self.args,
                    decoratee=self.decoratee,
                    future=self.future_by_key.setdefault(key, asyncio.Future()),
                    generate_key=self.generate_key,
                    kwargs=self.kwargs,
                    size=self.size,
                )
                return tuple([exit_context, self.decoratee])


@dataclasses.dataclass(frozen=True, kw_only=True)
class MultiEnter[** Param, Ret](Multi[Param, Ret], Enter[Param, Ret], base.MultiEnter[Param, Ret]):

    @property
    def future_t(self) -> type[concurrent.futures.Future[Ret]]:
        return concurrent.futures.Future

    def __call__(self) -> (
        tuple[base.MultiDecoratee[Param, Ret]] |
        tuple[MultiExit[Param, Ret], base.MultiDecoratee[Param, Ret]]
    ):
        key = self.generate_key(*self.args, **self.kwargs)

        with self.lock:
            future = self.future_by_key.pop(key, None)
            while self.size <= len(self.future_by_key):
                self.future_by_key.popitem(last=False)
            if future is not None:
                self.future_by_key[key] = future
                return tuple([lambda *_args, **_kwargs: future.result()])
            else:
                exit_ = self.exit_t(
                    args=self.args,
                    decoratee=self.decoratee,
                    future=self.future_by_key.setdefault(key, concurrent.futures.Future()),
                    generate_key=self.generate_key,
                    kwargs=self.kwargs,
                    size=self.size,
                )
                return tuple([exit_, self.decoratee])


@dataclasses.dataclass(frozen=True, kw_only=True)
class AsyncExit[** Param, Ret](Async[Param, Ret], Exit[Param, Ret], base.AsyncExit[Param, Ret]):
    future: asyncio.Future[base.Raise | Ret]

    async def __call__(self, result: base.Raise | Ret) -> tuple[base.Raise | Ret]:
        self.future.set_result(result)

        return tuple([result])


@dataclasses.dataclass(frozen=True, kw_only=True)
class MultiExit[** Param, Ret](Multi[Param, Ret], Exit[Param, Ret], base.MultiExit[Param, Ret]):
    future: concurrent.futures.Future[base.Raise | Ret]

    def __call__(self, result: base.Raise | Ret) -> tuple[base.Raise | Ret]:
        self.future.set_result(result)

        return tuple([result])


@dataclasses.dataclass(frozen=True, kw_only=True)
class Decorated[** Param, Ret](Base[Param, Ret], base.Decorated[Param, Ret], abc.ABC):
    future_by_key: collections.OrderedDict[Key, Future[Ret]] = dataclasses.field(
        default_factory=collections.OrderedDict,
    )
    future_by_key_by_instance: weakref.WeakKeyDictionary[
        base.Instance, collections.OrderedDict[Key, Future[Ret]]
    ] = dataclasses.field(default_factory=weakref.WeakKeyDictionary)

    def to_enter(self, *args: Param.args, **kwargs: Param.kwargs) -> Enter[Param, Ret]:
        return self.enter_t(
            args=args,
            decoratee=self.decoratee,
            kwargs=kwargs,
            future_by_key=self.future_by_key,
            generate_key=self.generate_key,
            size=self.size,
        )

    def __get__(self, instance, owner) -> typing.Self:
        return dataclasses.replace(
            self,
            decoratee=self.decoratee.__get__(instance, owner),
            future_by_key=self.future_by_key_by_instance.setdefault(instance, collections.OrderedDict()),
        )


@dataclasses.dataclass(frozen=True, kw_only=True)
class AsyncDecorated[** Param, Ret](Decorated[Param, Ret], base.AsyncDecorated[Param, Ret]): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class MultiDecorated[** Param, Ret](Decorated[Param, Ret], base.MultiDecorated[Param, Ret]): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class Decorator[** Param, Ret](base.Decorator[Param, Ret]):
    generate_key: GenerateKey[Param] = lambda *args, **kwargs: (tuple(args), tuple(sorted([*kwargs.items()])))
    size: int = sys.maxsize

    def __call__(self, decoratee: base.Decoratee[Param, Ret], /) -> Decorated[Param, Ret]:
        if inspect.iscoroutinefunction(decoratee):
            decorated_t: AsyncDecorated[Param, Ret] = AsyncDecorated
        else:
            decorated_t: MultiDecorated[Param, Ret] = MultiDecorated

        decorated = decorated_t(
            decoratee=decoratee,
            generate_key=self.generate_key,
            size=self.size,
            __doc__=str(decoratee.__doc__),
            __module__=str(decoratee.__module__),
            __name__=str(decoratee.__name__),
            __qualname__=str(decoratee.__qualname__),
        )

        return decorated
