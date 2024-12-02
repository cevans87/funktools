from __future__ import annotations

import abc
import dataclasses
import inspect
import logging
import typing

from . import base

Level = typing.Literal['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET']

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
    bound_arguments: inspect.BoundArguments
    err_level: Level
    logger: logging.Logger
    ok_level: Level

    @abc.abstractmethod
    def __call__(self, result: base.Raise | Ret) -> ():
        if isinstance(result, base.Raise):
            self.logger.log(
                logging.getLevelNamesMapping()[self.err_level],
                '%s raised %s',
                self.bound_arguments, result.exc_val,
            )
        else:
            self.logger.log(
                logging.getLevelNamesMapping()[self.ok_level],
                '%s -> %s',
                self.bound_arguments,
                result,
            )

        return tuple()


@dataclasses.dataclass(frozen=True, kw_only=True)
class Enter[** Param, Ret, _Decoratee, _Exit, _Decorated, _Decorator](
    Call[_Decoratee, _Exit, typing.Self, _Decorated, _Decorator],
    base.Enter[Param, Ret, _Decoratee, _Exit, _Decorated, _Decorator],
    abc.ABC,
):
    signature: inspect.Signature

    @abc.abstractmethod
    def __call__(self, *args: Param.args, **kwargs: Param.kwargs) -> tuple[_Exit, _Decoratee]:
        bound_arguments = inspect.signature(self.decorated).bind(*args, **kwargs)

        self.decorated.decorator.logger.log(
            logging.getLevelNamesMapping()[self.decorated.decorator.call_level],
            '%s',
            bound_arguments,
        )

        return self.exit_t(bound_arguments=bound_arguments), self.decorated.decoratee,


class Decorated[** Param, Ret, _Decoratee, _Exit, _Enter, _Decorator](
    Call[_Decoratee, _Exit, _Enter, typing.Self, _Decorator],
    base.Decorated[Param, Ret, _Decoratee, _Exit, _Enter, _Decorator],
    abc.ABC,
): ...


@typing.final
@dataclasses.dataclass(frozen=True, kw_only=True)
class CooperativeExit[** Param, Ret](
    Cooperative[Param, Ret],
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

    @typing.overload
    async def __call__(self, result: Ret) -> Ret: ...
    @typing.overload
    async def __call__(self, result: base.Raise) -> base.Raise: ...
    async def __call__(self, result):
        return super().__call__(result)


@typing.final
@dataclasses.dataclass(frozen=True, kw_only=True)
class SynchronousExit[** Param, Ret](
    Synchronous[Param, Ret],
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

    @typing.overload
    def __call__(self, result: Ret) -> Ret: ...
    @typing.overload
    def __call__(self, result: base.Raise) -> base.Raise: ...
    def __call__(self, result):
        return super().__call__(result)


@typing.final
@dataclasses.dataclass(frozen=True, kw_only=True)
class CooperativeEnter[** Param, Ret](
    Cooperative[Param, Ret],
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
        return super().__call__(*args, **kwargs)


@typing.final
@dataclasses.dataclass(frozen=True, kw_only=True)
class SynchronousEnter[** Param, Ret](
    Synchronous[Param, Ret],
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

    async def __call__(self, *args: Param.args, **kwargs: Param.kwargs) -> tuple[_Exit, _Decoratee]:
        return super().__call__(*args, **kwargs)


@dataclasses.dataclass(frozen=True, kw_only=True)
class CooperativeDecorated[** Param, Ret](
    Cooperative[Param, Ret],
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
    Synchronous[Param, Ret],
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
class Decorator[** Param, Ret](
    base.Decorator[Param, Ret, CooperativeDecorated[Param, Ret], SynchronousDecorated[Param, Ret]],
):
    logger: logging.Logger
    call_level: Level = 'DEBUG'
    err_level: Level = 'ERROR'
    ok_level: Level = 'INFO'
