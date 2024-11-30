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

type _CooperativeDecoratee[** Param, Ret] = base.CooperativeDecoratee[Param, Ret]
type _SynchronousDecoratee[** Param, Ret] = base.SynchronousDecoratee[Param, Ret]
type _CooperativeExit[** Param, Ret] = CooperativeExit[Param, Ret]
type _SynchronousExit[** Param, Ret] = SynchronousExit[Param, Ret]
type _CooperativeEnter[** Param, Ret] = CooperativeEnter[Param, Ret]
type _SynchronousEnter[** Param, Ret] = SynchronousEnter[Param, Ret]
type _CooperativeDecorated[** Param, Ret] = CooperativeDecorated[Param, Ret]
type _SynchronousDecorated[** Param, Ret] = SynchronousDecorated[Param, Ret]
type _Decorator[** Param, Ret] = Decorator[Param, Ret]


@dataclasses.dataclass(frozen=True, kw_only=True)
class Base(
    base.Base[
        _CooperativeExit,
        _SynchronousExit,
        _CooperativeEnter,
        _SynchronousEnter,
        _CooperativeDecorated,
        _SynchronousDecorated,
        _Decorator,
    ],
    abc.ABC,
): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class Call[_Decoratee, _Exit, _Enter, _Decorated, _Decorator](
    Base,
    base.Call[_Decoratee, _Exit, _Enter, _Decorated, _Decorator],
    abc.ABC,
): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class Cooperative[** Param, Ret](
    Call[
        base.CooperativeDecoratee[Param, Ret],
        _CooperativeExit[Param, Ret],
        _CooperativeEnter[Param, Ret],
        _CooperativeDecorated[Param, Ret],
        _Decorator[Param, Ret],
    ],
    base.Cooperative[
        base.CooperativeDecoratee[Param, Ret],
        _CooperativeExit[Param, Ret],
        _CooperativeEnter[Param, Ret],
        _CooperativeDecorated[Param, Ret],
        _Decorator[Param, Ret],
    ],
    abc.ABC,
): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class Synchronous[** Param, Ret](
    Call[
        base.SynchronousDecoratee[Param, Ret],
        _SynchronousExit[Param, Ret],
        _SynchronousEnter[Param, Ret],
        _SynchronousDecorated[Param, Ret],
        _Decorator[Param, Ret],
    ],
    base.Synchronous[
        base.SynchronousDecoratee[Param, Ret],
        _SynchronousExit[Param, Ret],
        _SynchronousEnter[Param, Ret],
        _SynchronousDecorated[Param, Ret],
        _Decorator[Param, Ret],
    ],
    abc.ABC,
): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class Exit[** Param, Ret, _Decoratee, _Enter, _Decorated, _Decorator, _Future](
    Call[_Decoratee, typing.Self, _Enter, _Decorated, _Decorator],
    base.Exit[Param, Ret, _Decoratee, _Enter, _Decorated, _Decorator],
    abc.ABC,
):
    future: _Future


@dataclasses.dataclass(frozen=True, kw_only=True)
class Enter[** Param, Ret, _Decoratee, _Exit, _Decorated, _Decorator](
    Call[_Decoratee, _Exit, typing.Self, _Decorated, _Decorator],
    base.Enter[Param, Ret, _Decoratee, _Exit, _Decorated, _Decorator],
    abc.ABC,
): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class Decorated[** Param, Ret, _Decoratee, _Exit, _Enter, _Decorator, _Future](
    Call[_Decoratee, _Exit, _Enter, typing.Self, _Decorator],
    base.Decorated[Param, Ret, _Decoratee, _Exit, _Enter, _Decorator],
    abc.ABC,
):
    decorated_by_instance: weakref.WeakKeyDictionary[
        base.Instance, typing.Self,
    ] = dataclasses.field(default_factory=weakref.WeakKeyDictionary)
    future_by_key: collections.OrderedDict[Key, _Future] = dataclasses.field(default_factory=collections.OrderedDict)

    def __get__(self, instance, owner) -> typing.Self:
        return self.decorated_by_instance.setdefault(
            instance, dataclasses.replace(
                self,
                decoratee=self.decoratee.__get__(instance, owner),
                future_by_key=collections.OrderedDict(),
            )
        )


@typing.final
@dataclasses.dataclass(frozen=True, kw_only=True)
class CooperativeExit[** Param, Ret](
    Cooperative,
    Exit[
        Param,
        Ret,
        _CooperativeDecoratee[Param, Ret],
        _CooperativeEnter[Param, Ret],
        _CooperativeDecorated[Param, Ret],
        _Decorator[Param, Ret],
        asyncio.Future[Ret],
    ],
    base.CooperativeExit[
        Param,
        Ret,
        _CooperativeDecoratee[Param, Ret],
        _CooperativeEnter[Param, Ret],
        _CooperativeDecorated[Param, Ret],
        _Decorator[Param, Ret],
    ],
):
    future: asyncio.Future[Ret] = dataclasses.field(default_factory=asyncio.Future)

    async def __call__(self, result: base.Raise | Ret) -> ():
        self.future.set_result(result)

        return tuple()


@typing.final
@dataclasses.dataclass(frozen=True, kw_only=True)
class SynchronousExit[** Param, Ret](
    Synchronous,
    Exit[
        Param,
        Ret,
        _SynchronousDecoratee[Param, Ret],
        _SynchronousEnter[Param, Ret],
        _SynchronousDecorated[Param, Ret],
        _Decorator[Param, Ret],
        concurrent.futures.Future[Ret],
    ],
    base.SynchronousExit[
        Param,
        Ret,
        _SynchronousDecoratee[Param, Ret],
        _SynchronousEnter[Param, Ret],
        _SynchronousDecorated[Param, Ret],
        _Decorator[Param, Ret],
    ],
):
    future: concurrent.futures.Future[Ret] = dataclasses.field(default_factory=concurrent.futures.Future)

    def __call__(self, result: base.Raise | Ret) -> ():
        self.future.set_result(result)

        return tuple()


@typing.final
@dataclasses.dataclass(frozen=True, kw_only=True)
class CooperativeEnter[** Param, Ret](
    Cooperative,
    Enter[
        Param,
        Ret,
        _CooperativeDecoratee[Param, Ret],
        _CooperativeExit[Param, Ret],
        _CooperativeDecorated[Param, Ret],
        _Decorator[Param, Ret],
    ],
    base.CooperativeEnter[
        Param,
        Ret,
        _CooperativeDecoratee[Param, Ret],
        _CooperativeExit[Param, Ret],
        _CooperativeDecorated[Param, Ret],
        _Decorator[Param, Ret],
    ],
):
    type _Decoratee = _CooperativeDecoratee[Param, Ret]
    type _Exit = _CooperativeExit[Param, Ret]
    type _Enter = typing.Self
    type _Decorator = _Decorator[Param, Ret]

    async def __call__(self, *args: Param.args, **kwargs: Param.kwargs) -> tuple[_Decoratee] | tuple[_Exit, _Decorator]:
        key = self.decorated.decorator.generate_key(*args, **kwargs)

        future = self.decorated.future_by_key.pop(key, None)
        while self.decorated.decorator.size <= len(self.decorated.future_by_key):
            self.decorated.future_by_key.popitem(last=False)
        if future is None:
            future = self.decorated.future_by_key[key] = asyncio.Future()
            return CooperativeExit(enter=self, future=future), self.decorated.decoratee
        else:
            self.decorated.future_by_key[key] = future
            return (lambda *_args, **_kwargs: future),


@typing.final
@dataclasses.dataclass(frozen=True, kw_only=True)
class SynchronousEnter[** Param, Ret](
    Synchronous,
    Enter[
        Param,
        Ret,
        _SynchronousDecoratee[Param, Ret],
        _SynchronousExit[Param, Ret],
        _SynchronousDecorated[Param, Ret],
        _Decorator[Param, Ret],
    ],
    base.SynchronousEnter[
        Param,
        Ret,
        _SynchronousDecoratee[Param, Ret],
        _SynchronousEnter[Param, Ret],
        _SynchronousDecorated[Param, Ret],
        _Decorator[Param, Ret],
    ],
):
    type _Decoratee = _SynchronousDecoratee[Param, Ret]
    type _Exit = _SynchronousExit[Param, Ret]
    type _Enter = typing.Self
    type _Decorator = _Decorator[Param, Ret]

    def __call__(self, *args: Param.args, **kwargs: Param.kwargs) -> tuple[_Decoratee] | tuple[_Exit, _Decorator]:
        key = self.decorated.decorator.generate_key(*args, **kwargs)

        future = self.decorated.future_by_key.pop(key, None)
        while self.decorated.decorator.size <= len(self.decorated.future_by_key):
            self.decorated.future_by_key.popitem(last=False)
        if future is None:
            future = self.decorated.future_by_key[key] = asyncio.Future()
            return SynchronousExit(enter=self, future=future), self.decorated.decoratee
        else:
            self.decorated.future_by_key[key] = future
            return (lambda *_args, **_kwargs: future.result()),


@dataclasses.dataclass(frozen=True, kw_only=True)
class CooperativeDecorated[** Param, Ret](
    Cooperative,
    Decorated[
        Param,
        Ret,
        _CooperativeDecoratee[Param, Ret],
        _CooperativeExit[Param, Ret],
        _CooperativeEnter[Param, Ret],
        _Decorator[Param, Ret],
        asyncio.Future[Ret],
    ],
    base.CooperativeDecorated[
        Param,
        Ret,
        _CooperativeDecoratee[Param, Ret],
        _CooperativeExit[Param, Ret],
        _CooperativeEnter[Param, Ret],
        _Decorator[Param, Ret],
    ],
): ...


@typing.final
@dataclasses.dataclass(frozen=True, kw_only=True)
class SynchronousDecorated[** Param, Ret](
    Synchronous,
    Decorated[
        Param,
        Ret,
        _SynchronousDecoratee[Param, Ret],
        _SynchronousExit[Param, Ret],
        _SynchronousEnter[Param, Ret],
        _Decorator[Param, Ret],
        concurrent.futures.Future[Ret],
    ],
    base.SynchronousDecorated[
        Param,
        Ret,
        _SynchronousDecoratee[Param, Ret],
        _SynchronousExit[Param, Ret],
        _SynchronousEnter[Param, Ret],
        _Decorator[Param, Ret],
    ],
): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class Decorator[** Param, Ret](
    base.Decorator[Param, Ret, CooperativeDecorated[Param, Ret], SynchronousDecorated[Param, Ret]]
):
    generate_key: GenerateKey[Param] = lambda *args, **kwargs: (tuple(args), tuple(sorted([*kwargs.items()])))
    size: int = sys.maxsize
