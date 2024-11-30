from __future__ import annotations

import abc
import annotated_types
import dataclasses
import sys
import typing

from . import base


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
class Exit[** Param, Ret, _Decoratee, _Enter, _Decorated, _Decorator](
    Call[_Decoratee, typing.Self, _Enter, _Decorated, _Decorator],
    base.Exit[Param, Ret, _Decoratee, _Enter, _Decorated, _Decorator],
    abc.ABC,
):

    def __call__(self, result: base.Raise | Ret) -> tuple[_Decorator] | tuple[base.Raise | Ret]:
        if self.enter.n_retried < self.enter.decorated.decorator.n and isinstance(result, base.Raise):
            return dataclasses.replace(self.enter, n_retried=self.enter.n_retried + 1),

        return result,


@dataclasses.dataclass(frozen=True, kw_only=True)
class Enter[** Param, Ret, _Decoratee, _Exit, _Decorated, _Decorator](
    Call[_Decoratee, _Exit, typing.Self, _Decorated, _Decorator],
    base.Enter[Param, Ret, _Decoratee, _Exit, _Decorated, _Decorator],
    abc.ABC,
):
    n_retried: int = 0

    def __call__(self, *args: Param.args, **kwargs: Param.kwargs) -> tuple[_Exit, _Decoratee]:
        return self.exit_t(enter=self), self.decorated.decoratee,


class Decorated[** Param, Ret, _Decoratee, _Exit, _Enter, _Decorator](
    Call[_Decoratee, _Exit, _Enter, typing.Self, _Decorator],
    base.Decorated[Param, Ret, _Decoratee, _Exit, _Enter, _Decorator],
    abc.ABC,
): ...


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

    async def __call__(self, result: base.Raise | Ret) -> tuple[_Decorator] | tuple[base.Raise | Ret]:
        return super().__call__(result)


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

    def __call__(self, result: base.Raise | Ret) -> tuple[_Decorator] | tuple[base.Raise | Ret]:
        return super().__call__(result)


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

    async def __call__(self, *args: Param.args, **kwargs: Param.kwargs) -> tuple[_Exit, _Decoratee]:
        return super().__call__()


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

    def __call__(self, *args: Param.args, **kwargs: Param.kwargs) -> tuple[_Exit, _Decoratee]:
        return super().__call__()


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
class Decorator[**Param, Ret](
    base.Decorator[Param, Ret, CooperativeDecorated[Param, Ret], SynchronousDecorated[Param, Ret]],
):
    n: typing.Annotated[int, annotated_types.Ge(0)] = sys.maxsize
