from __future__ import annotations

import abc
import annotated_types
import asyncio
import dataclasses
import sys
import threading
import typing
import weakref

from . import base

type Condition = asyncio.Condition | threading.Condition
type Penalty = typing.Annotated[float, annotated_types.Gt(0.0)]
type Time = typing.Annotated[float, annotated_types.Gt(0.0)]

type _CooperativeCondition = asyncio.Condition
type _SynchronousCondition = threading.Condition
type _CooperativeDecoratee[** Param, Ret] = base.CooperativeDecoratee[Param, Ret]
type _SynchronousDecoratee[** Param, Ret] = base.SynchronousDecoratee[Param, Ret]
type _CooperativeExit[** Param, Ret] = CooperativeExit[Param, Ret]
type _SynchronousExit[** Param, Ret] = SynchronousExit[Param, Ret]
type _CooperativeEnter[** Param, Ret] = CooperativeEnter[Param, Ret]
type _SynchronousEnter[** Param, Ret] = SynchronousEnter[Param, Ret]
type _CooperativeDecorated[** Param, Ret] = CooperativeDecorated[Param, Ret]
type _SynchronousDecorated[** Param, Ret] = SynchronousDecorated[Param, Ret]
type _Decorator[** Param, Ret] = Decorator[Param, Ret]


class Exception(base.Exception): ...  # noqa


@dataclasses.dataclass(kw_only=True)
class State:
    cap_running: int = 1
    num_running: int = 0
    num_waiting: int = 0


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
class Call[_Decoratee, _Exit, _Enter, _Decorated, _Decorator, _Condition](
    Base,
    base.Call[_Decoratee, _Exit, _Enter, _Decorated, _Decorator],
    abc.ABC,
):
    @property
    @abc.abstractmethod
    def condition_t(self) -> type[_Condition]: ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class Cooperative[** Param, Ret](
    Call[
        base.CooperativeDecoratee[Param, Ret],
        _CooperativeExit[Param, Ret],
        _CooperativeEnter[Param, Ret],
        _CooperativeDecorated[Param, Ret],
        _Decorator[Param, Ret],
        _CooperativeCondition,
    ],
    base.Cooperative[
        base.CooperativeDecoratee[Param, Ret],
        _CooperativeExit[Param, Ret],
        _CooperativeEnter[Param, Ret],
        _CooperativeDecorated[Param, Ret],
        _Decorator[Param, Ret],
    ],
    abc.ABC,
):
    @property
    def condition_t(self) -> type[_CooperativeCondition]:
        return asyncio.Condition


@dataclasses.dataclass(frozen=True, kw_only=True)
class Synchronous[** Param, Ret](
    Call[
        base.SynchronousDecoratee[Param, Ret],
        _SynchronousExit[Param, Ret],
        _SynchronousEnter[Param, Ret],
        _SynchronousDecorated[Param, Ret],
        _Decorator[Param, Ret],
        _SynchronousCondition,
    ],
    base.Synchronous[
        base.SynchronousDecoratee[Param, Ret],
        _SynchronousExit[Param, Ret],
        _SynchronousEnter[Param, Ret],
        _SynchronousDecorated[Param, Ret],
        _Decorator[Param, Ret],
    ],
    abc.ABC,
):
    @property
    def condition_t(self) -> type[_SynchronousCondition]:
        return threading.Condition


@dataclasses.dataclass(frozen=True, kw_only=True)
class Exit[** Param, Ret, _Decoratee, _Enter, _Decorated, _Decorator, _Condition](
    Call[_Decoratee, typing.Self, _Enter, _Decorated, _Decorator, _Condition],
    base.Exit[Param, Ret, _Decoratee, _Enter, _Decorated, _Decorator],
    abc.ABC,
): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class Enter[** Param, Ret, _Decoratee, _Exit, _Decorated, _Decorator, _Condition](
    Call[_Decoratee, _Exit, typing.Self, _Decorated, _Decorator, _Condition],
    base.Enter[Param, Ret, _Decoratee, _Exit, _Decorated, _Decorator],
    abc.ABC,
):
    def __call__(self, *args: Param.args, **kwargs: Param.kwargs) -> tuple[_Exit, _Decoratee]:
        return self.exit_t(enter=self), self.decorated.decoratee,


@dataclasses.dataclass(frozen=True, kw_only=True)
class Decorated[** Param, Ret, _Decoratee, _Exit, _Enter, _Decorator, _Condition](
    Call[_Decoratee, _Exit, _Enter, typing.Self, _Decorator, _Condition],
    base.Decorated[Param, Ret, _Decoratee, _Exit, _Enter, _Decorator],
    abc.ABC,
):
    condition: _Condition
    decorated_by_instance: weakref.WeakKeyDictionary[
        base.Instance, typing.Self,
    ] = dataclasses.field(default_factory=weakref.WeakKeyDictionary)
    state: State = dataclasses.field(default_factory=State)

    def __get__(self, instance, owner) -> typing.Self:
        return decorated if (decorated := self.decorated_by_instance.get(instance)) is not None else (
            self.decorated_by_instance.setdefault(
                instance, dataclasses.replace(
                    self,
                    condition=self.condition_t(),
                    decoratee=self.decoratee.__get__(instance, owner),
                    state=State(),
                )
            )
        )


@typing.final
@dataclasses.dataclass(frozen=True, kw_only=True)
class CooperativeExit[** Param, Ret](
    Exit[
        Param,
        Ret,
        _CooperativeDecoratee[Param, Ret],
        _CooperativeEnter[Param, Ret],
        _CooperativeDecorated[Param, Ret],
        _Decorator[Param, Ret],
        _CooperativeCondition,
    ],
    Cooperative[Param, Ret],
    base.CooperativeExit[
        Param,
        Ret,
        _CooperativeDecoratee[Param, Ret],
        _CooperativeEnter[Param, Ret],
        _CooperativeDecorated[Param, Ret],
        _Decorator[Param, Ret],
    ],
):
    async def __call__(self, result: base.Raise | Ret) -> ():
        state = self.enter.decorated.state
        async with self.enter.decorated.condition:
            if isinstance(result, base.Raise) and state.num_running <= state.cap_running:
                state.cap_running //= 2
            elif (
                not isinstance(result, base.Raise)
                and state.num_running == state.cap_running < self.enter.decorated.decorator.max_running
            ):
                state.cap_running += 1
            state.num_running -= 1

            if 0 < (n := state.cap_running - state.num_running):
                self.enter.decorated.condition.notify(n=n)

        return tuple()


@typing.final
@dataclasses.dataclass(frozen=True, kw_only=True)
class SynchronousExit[** Param, Ret](
    Exit[
        Param,
        Ret,
        _SynchronousDecoratee[Param, Ret],
        _SynchronousEnter[Param, Ret],
        _SynchronousDecorated[Param, Ret],
        _Decorator[Param, Ret],
        _SynchronousCondition,
    ],
    Synchronous[Param, Ret],
    base.SynchronousExit[
        Param,
        Ret,
        _SynchronousDecoratee[Param, Ret],
        _SynchronousEnter[Param, Ret],
        _SynchronousDecorated[Param, Ret],
        _Decorator[Param, Ret],
    ],
):

    def __call__(self, result: base.Raise | Ret) -> ():
        state = self.enter.decorated.state
        with self.enter.decorated.condition:
            if isinstance(result, base.Raise) and state.num_running <= state.cap_running:
                state.cap_running //= 2
            elif (
                not isinstance(result, base.Raise)
                and state.num_running == state.cap_running < self.enter.decorated.decorator.max_running
            ):
                state.cap_running += 1
            state.num_running -= 1

            if 0 < (n := state.cap_running - state.num_running):
                self.enter.decorated.condition.notify(n=n)

        return tuple()


@dataclasses.dataclass(frozen=True, kw_only=True)
class CooperativeEnter[** Param, Ret](
    Enter[
        Param,
        Ret,
        _CooperativeDecoratee[Param, Ret],
        _CooperativeExit[Param, Ret],
        _CooperativeDecorated[Param, Ret],
        _Decorator[Param, Ret],
        _CooperativeCondition,
    ],
    Cooperative[Param, Ret],
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

    async def __call__(self, *args: Param.args, **kwargs: Param.kwargs) -> tuple[_Exit, _Decoratee]:
        state = self.decorated.state
        async with self.decorated.condition:
            if state.num_waiting >= self.decorated.decorator.max_waiting:
                raise Exception(f'Exceeded {self.decorated.decorator.max_waiting=}.')
            elif 0 < state.num_waiting or state.cap_running <= state.num_running:
                state.num_waiting += 1
                await self.decorated.condition.wait_for(lambda: state.num_running < state.cap_running)
                state.num_waiting -= 1
            self.decorated.state.num_running += 1

        return self.exit_t(enter=self), self.decorated.decoratee,


@typing.final
@dataclasses.dataclass(frozen=True, kw_only=True)
class SynchronousEnter[** Param, Ret](
    Enter[
        Param,
        Ret,
        _SynchronousDecoratee[Param, Ret],
        _SynchronousExit[Param, Ret],
        _SynchronousDecorated[Param, Ret],
        _Decorator[Param, Ret],
        _SynchronousCondition,
    ],
    Synchronous[Param, Ret],
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

    def __call__(self, *args: Param.args, **kwargs: Param.kwargs) -> tuple[_Exit, _Decoratee]:
        state = self.decorated.state
        with self.decorated.condition:
            if state.num_waiting >= self.decorated.decorator.max_waiting:
                raise Exception(f'Exceeded {self.decorated.decorator.max_waiting=}.')
            elif 0 < state.num_waiting or state.cap_running <= state.num_running:
                state.num_waiting += 1
                self.decorated.condition.wait_for(lambda: state.num_running < state.cap_running)
                state.num_waiting -= 1
            self.decorated.state.num_running += 1

        return self.exit_t(enter=self), self.decorated.decoratee,


@dataclasses.dataclass(frozen=True, kw_only=True)
class CooperativeDecorated[** Param, Ret](
    Decorated[
        Param,
        Ret,
        _CooperativeDecoratee[Param, Ret],
        _CooperativeExit[Param, Ret],
        _CooperativeEnter[Param, Ret],
        _Decorator[Param, Ret],
        _CooperativeCondition,
    ],
    Cooperative[Param, Ret],
    base.CooperativeDecorated[
        Param,
        Ret,
        _CooperativeDecoratee[Param, Ret],
        _CooperativeExit[Param, Ret],
        _CooperativeEnter[Param, Ret],
        _Decorator[Param, Ret],
    ],
):
    condition: _CooperativeCondition = dataclasses.field(default_factory=asyncio.Condition)


@typing.final
@dataclasses.dataclass(frozen=True, kw_only=True)
class SynchronousDecorated[** Param, Ret](
    Decorated[
        Param,
        Ret,
        _SynchronousDecoratee[Param, Ret],
        _SynchronousExit[Param, Ret],
        _SynchronousEnter[Param, Ret],
        _Decorator[Param, Ret],
        _SynchronousCondition,
    ],
    Synchronous[Param, Ret],
    base.SynchronousDecorated[
        Param,
        Ret,
        _SynchronousDecoratee[Param, Ret],
        _SynchronousExit[Param, Ret],
        _SynchronousEnter[Param, Ret],
        _Decorator[Param, Ret],
    ],
):
    condition: _SynchronousCondition = dataclasses.field(default_factory=threading.Condition)


@dataclasses.dataclass(frozen=True, kw_only=True)
class Decorator[** Param, Ret](
    base.Decorator[Param, Ret, _CooperativeDecorated[Param, Ret], _SynchronousDecorated[Param, Ret]],
):
    # How many callees are allowed through concurrently before additional callees become waiters.
    max_running: typing.Annotated[int, annotated_types.Gt(0)] = sys.maxsize

    # How many callees are allowed through or to wait concurrently before additional callees are rejected.
    max_waiting: typing.Annotated[int, annotated_types.Gt(0)] = sys.maxsize
