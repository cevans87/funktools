from __future__ import annotations

import abc
import annotated_types
import dataclasses
import inspect
import sys
import typing

from . import base


@dataclasses.dataclass(frozen=True, kw_only=True)
class Base[** Param, Ret](base.Base[Param, Ret], abc.ABC):
    n: typing.Annotated[int, annotated_types.Ge(0)]


@dataclasses.dataclass(frozen=True, kw_only=True)
class Context[** Param, Ret](Base[Param, Ret], base.Context[Param, Ret], abc.ABC): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class Async[** Param, Ret](Base[Param, Ret], base.Async[Param, Ret], abc.ABC): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class Multi[** Param, Ret](Base[Param, Ret], base.Multi[Param, Ret], abc.ABC): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class Enter[** Param, Ret](Context[Param, Ret], base.Enter[Param, Ret], abc.ABC): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class Exit[** Param, Ret](Context[Param, Ret], base.Exit[Param, Ret], abc.ABC):

    def __call__(self, result: base.Raise | Ret) -> tuple[Enter[Param, Ret]] | tuple[base.Raise | Ret]:
        if self.n > 0 and isinstance(result, base.Raise):
            return tuple([self.enter_t(args=self.args, decoratee=self.decoratee, kwargs=self.kwargs, n=self.n - 1)])

        return tuple([result])


@dataclasses.dataclass(frozen=True, kw_only=True)
class AsyncEnter[** Param, Ret](Async[Param, Ret], Enter[Param, Ret], base.AsyncEnter[Param, Ret]):

    async def __call__(self) -> tuple[AsyncExit[Param, Ret], base.AsyncDecoratee[Param, Ret]]:
        return tuple([
            self.exit_t(args=self.args, decoratee=self.decoratee, kwargs=self.kwargs, n=self.n),
            self.decoratee,
        ])


@dataclasses.dataclass(frozen=True, kw_only=True)
class MultiEnter[** Param, Ret](Multi[Param, Ret], Enter[Param, Ret], base.MultiEnter[Param, Ret]):

    def __call__(self) -> tuple[MultiExit[Param, Ret], base.MultiDecoratee[Param, Ret]]:
        return tuple([
            self.exit_t(args=self.args, decoratee=self.decoratee, kwargs=self.kwargs, n=self.n),
            self.decoratee,
        ])


@dataclasses.dataclass(frozen=True, kw_only=True)
class AsyncExit[** Param, Ret](Async[Param, Ret], Exit[Param, Ret], base.AsyncExit[Param, Ret]):

    async def __call__(self, result: base.Raise | Ret) -> tuple[AsyncEnter[Param, Ret]] | tuple[base.Raise | Ret]:
        return super().__call__(result)


@dataclasses.dataclass(frozen=True, kw_only=True)
class MultiExit[** Param, Ret](Multi[Param, Ret], Exit[Param, Ret], base.MultiExit[Param, Ret]):

    def __call__(self, result: base.Raise | Ret) -> tuple[Enter[Param, Ret]] | tuple[base.Raise | Ret]:
        return super().__call__(result)


@dataclasses.dataclass(frozen=True, kw_only=True)
class Decorated[** Param, Ret](Base[Param, Ret], base.Decorated[Param, Ret], abc.ABC):

    def to_enter(self, *args: Param.args, **kwargs: Param.kwargs) -> Enter[Param, Ret]:
        return self.enter_t(args=args, decoratee=self.decoratee, kwargs=kwargs, n=self.n)

@dataclasses.dataclass(frozen=True, kw_only=True)
class AsyncDecorated[** Param, Ret](Decorated[Param, Ret], base.AsyncDecorated[Param, Ret]): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class MultiDecorated[** Param, Ret](Decorated[Param, Ret], base.MultiDecorated[Param, Ret]): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class Decorator[**Param, Ret](base.Decorator[Param, Ret]):
    n: typing.Annotated[int, annotated_types.Ge(0)] = sys.maxsize

    def __call__(self, decoratee: base.Decoratee[Param, Ret], /) -> Decorated[Param, Ret]:
        if inspect.iscoroutinefunction(decoratee):
            decorated_t: AsyncDecorated[Param, Ret] = AsyncDecorated
        else:
            decorated_t: MultiDecorated[Param, Ret] = MultiDecorated

        decorated = decorated_t(
            decoratee=decoratee,
            n=self.n,
            __doc__=str(decoratee.__doc__),
            __module__=str(decoratee.__module__),
            __name__=str(decoratee.__name__),
            __qualname__=str(decoratee.__qualname__),
        )

        return decorated
