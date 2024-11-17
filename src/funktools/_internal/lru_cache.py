from __future__ import annotations

import abc
import asyncio
import concurrent.futures
import dataclasses
import threading
import typing
import weakref
import sys

from . import base

type Cache[** Params, Return] = dict[Key, ExitContext[Params, Return]]
type Expire = float
type Future[Return] = asyncio.Future[Return] | concurrent.futures.Future[Return]
type GenerateKey[** Params, Key] = typing.Callable[Params, Key]
type Key = typing.Hashable


@dataclasses.dataclass(frozen=True, kw_only=True)
class Base[** Params, Return](base.Base[Params, Return], abc.ABC):
    generate_key: GenerateKey
    size: int


@dataclasses.dataclass(frozen=True, kw_only=True)
class Context[** Params, Return](Base[Params, Return], base.Context[Params, Return], abc.ABC): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class AsyncContext[** Params, Return](Context[Params, Return], base.AsyncContext[Params, Return], abc.ABC):
    lock: asyncio.Lock = dataclasses.field(default_factory=asyncio.Lock)


@dataclasses.dataclass(frozen=True, kw_only=True)
class MultiContext[** Params, Return](Context[Params, Return], base.MultiContext[Params, Return], abc.ABC):
    lock: threading.Lock = dataclasses.field(default_factory=threading.Lock)


@dataclasses.dataclass(frozen=True, kw_only=True)
class EnterContext[** Params, Return](Context[Params, Return], base.EnterContext[Params, Return], abc.ABC):
    future_by_key: dict[Key, Future[Return]] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass(frozen=True, kw_only=True)
class ExitContext[** Params, Return](Context[Params, Return], base.ExitContext[Params, Return], abc.ABC): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class AsyncEnterContext[** Params, Return](
    AsyncContext[Params, Return],
    EnterContext[Params, Return],
    base.AsyncEnterContext[Params, Return],
):

    async def __call__(
        self,
        *args: Params.args,
        **kwargs: Params.kwargs,
    ) -> (
        tuple[base.AsyncDecoratee[Params, Return]] |
        tuple[AsyncExitContext[Params, Return], base.AsyncDecoratee[Params, Return]]
    ):
        key = self.generate_key(*args, **kwargs)

        async with self.lock:
            future = self.future_by_key.pop(key, None)
            while self.size <= len(self.future_by_key):
                self.future_by_key.popitem(last=False)
            if future is not None:
                self.future_by_key[key] = future
                return tuple([lambda *_args, **_kwargs: future])
            else:
                future = self.future_by_key[key] = asyncio.Future()
                return tuple([self.exit_context_t(future=future, **dataclasses.asdict(self)), self.decoratee])


@dataclasses.dataclass(frozen=True, kw_only=True)
class MultiEnterContext[** Params, Return](
    MultiContext[Params, Return],
    EnterContext[Params, Return],
    base.MultiEnterContext[Params, Return],
):

    def __call__(
        self,
        *args: Params.args,
        **kwargs: Params.kwargs,
    ) -> (
        tuple[base.MultiDecoratee[Params, Return]] |
        tuple[MultiExitContext[Params, Return], base.MultiDecoratee[Params, Return]]
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
                future = self.future_by_key[key] = concurrent.futures.Future()
                return tuple([self.exit_context_t(future=future, **dataclasses.asdict(self)), self.decoratee])


@dataclasses.dataclass(frozen=True, kw_only=True)
class AsyncExitContext[** Params, Return](ExitContext[Params, Return], base.AsyncExitContext[Params, Return]):

    async def __call__(self, result: base.Raise | Return) -> Return:
        return super().__call__(result)


@dataclasses.dataclass(frozen=True, kw_only=True)
class MultiExitContext[** Params, Return](ExitContext[Params, Return], base.MultiExitContext[Params, Return]):

    def __call__(self, result: base.Raise | Return) -> Return:
        return super().__call__(result)


@dataclasses.dataclass(frozen=True, kw_only=True)
class Decorated[** Params, Return](Base[Params, Return], base.Decorated[Params, Return], abc.ABC):
    future_by_key_by_instance: weakref.WeakKeyDictionary[base.Instance, dict[Key, Future[Return]]] = dataclasses.field(
        default_factory=weakref.WeakKeyDictionary)

    def __get__(self, instance, owner) -> typing.Self:
        return dataclasses.replace(self, instance=instance)


@dataclasses.dataclass(frozen=True, kw_only=True)
class AsyncDecorated[** Params, Return](Decorated[Params, Return], base.AsyncDecorated[Params, Return]): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class MultiDecorated[** Params, Return](Decorated[Params, Return], base.MultiDecorated[Params, Return]): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class Decorator[** Params, Return](base.Decorator[Params, Return]):
    generate_key: GenerateKey[Params] = lambda *args, **kwargs: (tuple(args), tuple(sorted([*kwargs.items()])))
    size: int = sys.maxsize
