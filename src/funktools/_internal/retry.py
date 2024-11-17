from __future__ import annotations

import abc
import annotated_types
import dataclasses
import sys
import typing

from . import base


@dataclasses.dataclass(frozen=True, kw_only=True)
class Context[** Params, Return](
    base.Context[Params, Return],
    abc.ABC,
):
    next_enter_context: base.EnterContext[Params, Return]
    n: typing.Annotated[int, annotated_types.Ge(0)]


@dataclasses.dataclass(frozen=True, kw_only=True)
class AsyncContext[** Params, Return](
    Context[Params, Return],
    base.AsyncContext[Params, Return],
    abc.ABC,
): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class MultiContext[** Params, Return](
    Context[Params, Return],
    base.MultiContext[Params, Return],
    abc.ABC,
): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class EnterContext[** Params, Return](
    Context[Params, Return],
    base.EnterContext[Params, Return],
    abc.ABC,
):

    @abc.abstractmethod
    def __call__(
        self,
        *args: Params.args,
        **kwargs: Params.kwargs
    ) -> (ExitContext[Params, Return], base.EnterContext[Params, Return]):
        return self.exit_context_t(n=self.n, next_enter_context=self.next_enter_context), self.next_enter_context


@dataclasses.dataclass(frozen=True, kw_only=True)
class ExitContext[** Params, Return](
    Context[Params, Return],
    base.ExitContext[Params, Return],
    abc.ABC,
):

    @abc.abstractmethod
    def __call__(self, result: base.Raise | Return) -> EnterContext[Params, Return] | base.Raise | Return:
        if isinstance(result, base.Raise) and self.n > 0:
            return self.enter_context_t(n=self.n - 1, next_enter_context=self.next_enter_context)

        return result


@dataclasses.dataclass(frozen=True, kw_only=True)
class AsyncEnterContext[** Params, Return](
    EnterContext[Params, Return],
    AsyncContext[Params, Return],
    base.AsyncEnterContext[Params, Return],
):
    async def __call__(
        self,
        *args: Params.args,
        **kwargs: Params.kwargs,
    ) -> (AsyncExitContext[Params, Return], base.AsyncEnterContext[Params, Return]):
        return super().__call__(*args, **kwargs)


@dataclasses.dataclass(frozen=True, kw_only=True)
class MultiEnterContext[** Params, Return](
    EnterContext[Params, Return],
    MultiContext[Params, Return],
    base.MultiEnterContext[Params, Return],
):
    def __call__(
        self,
        *args: Params.args,
        **kwargs: Params.kwargs,
    ) -> (MultiExitContext[Params, Return], base.MultiEnterContext[Params, Return]):
        return super().__call__(*args, **kwargs)


@dataclasses.dataclass(frozen=True, kw_only=True)
class AsyncExitContext[** Params, Return](
    ExitContext[Params, Return],
    AsyncContext[Params, Return],
    base.AsyncExitContext[Params, Return],
):
    async def __call__(self, return_) -> AsyncEnterContext[Params, Return] | base.Raise | Return:
        return super().__call__(return_)


@dataclasses.dataclass(frozen=True, kw_only=True)
class MultiExitContext[** Params, Return](
    ExitContext[Params, Return],
    MultiContext[Params, Return],
    base.MultiExitContext[Params, Return],
):
    def __call__(self, return_) -> MultiEnterContext[Params, Return] | base.Raise | Return:
        return super().__call__(return_)


@dataclasses.dataclass(frozen=True, kw_only=True)
class Decorator[**Params, Return](base.Decorator[Params, Return]):
    n: typing.Annotated[int, annotated_types.Ge(0)] = sys.maxsize

    register: typing.ClassVar[base.Register] = base.Register()

    def __call__(
        self,
        decoratee: base.Decoratee[Params, Return] | base.Decorated[Params, Return],
        /,
    ) -> base.Decorated[Params, Return]:
        decoratee = super().__call__(decoratee)

        match decoratee:
            case base.AsyncDecorated():
                enter_context_t = AsyncEnterContext[Params, Return]
            case base.MultiDecorated():
                enter_context_t = MultiEnterContext[Params, Return]
            case _: assert False, 'Unreachable'  # pragma: no cover

        decorated = self.register.decorateds[decoratee.register_key] = dataclasses.replace(
            decoratee,
            enter_context=enter_context_t(next_enter_context=decoratee.enter_context, n=self.n),
        )

        return decorated
