from __future__ import annotations
import abc
import dataclasses
import typing

from . import base


@dataclasses.dataclass(frozen=True, kw_only=True)
class ContextBase[** Params, Return](
    base.ContextBase[Params, Return],
    abc.ABC,
):
    enter_context_t: typing.ClassVar[type[EnterContextBase]]
    exit_context_t: typing.ClassVar[type[ExitContextBase]]


@dataclasses.dataclass(frozen=True, kw_only=True)
class AsyncContextBase[** Params, Return](
    ContextBase[Params, Return],
    base.AsyncContextBase[Params, Return],
    abc.ABC,
):
    enter_context_t: typing.ClassVar[type[AsyncEnterContextBase]]
    exit_context_t: typing.ClassVar[type[AsyncExitContextBase]]


@dataclasses.dataclass(frozen=True, kw_only=True)
class MultiContextBase[** Params, Return](
    ContextBase[Params, Return],
    base.MultiContextBase[Params, Return],
    abc.ABC,
):
    enter_context_t: typing.ClassVar[type[MultiEnterContextBase]]
    exit_context_t: typing.ClassVar[type[MultiExitContext]]


@dataclasses.dataclass(frozen=True, kw_only=True)
class EnterContextBase[** Params, Return](
    ContextBase[Params, Return],
    base.EnterContextBase[Params, Return],
    abc.ABC,
):
    ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class AsyncEnterContextBase[** Params, Return](
    EnterContextBase[Params, Return],
    AsyncContextBase[Params, Return],
    base.AsyncEnterContextBase[Params, Return],
    abc.ABC,
):
    ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class MultiEnterContextBase[** Params, Return](
    EnterContextBase[Params, Return],
    MultiContextBase[Params, Return],
    base.MultiEnterContextBase[Params, Return],
    abc.ABC,
):
    ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class ExitContextBase[** Params, Return](
    ContextBase[Params, Return],
    base.ExitContextBase[Params, Return],
    abc.ABC,
):
    ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class AsyncExitContextBase[** Params, Return](
    ExitContextBase[Params, Return],
    AsyncContextBase[Params, Return],
    base.AsyncExitContextBaseBase[Params, Return],
):
    ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class MultiExitContext[** Params, Return](
    ExitContextBase[Params, Return],
    MultiContextBase[Params, Return],
    base.MultiExitContextBase[Params, Return],
):
    ...


AsyncContextBase.enter_context_t = AsyncEnterContextBase
MultiContextBase.enter_context_t = MultiEnterContextBase
AsyncContextBase.exit_context_t = AsyncExitContextBase
MultiContextBase.exit_context_t = MultiExitContext


@dataclasses.dataclass(frozen=True, kw_only=True)
class Decorator[**Params, Return]:

    @typing.overload
    def __call__(
        self, decoratee: base.AsyncDecoratee[Params, Return] | base.AsyncDecorated[Params, Return], /
    ) -> base.AsyncDecorated[Params, Return]: ...

    @typing.overload
    def __call__(
        self, decoratee: base.MultiDecoratee[Params, Return] | base.MultiDecorated[Params, Return], /
    ) -> base.MultiDecorated[Params, Return]: ...

    def __call__(self, decoratee):
        if not isinstance(decoratee, base.Decorated):
            decoratee = base.Decorator[Params, Return]()(decoratee)

        match decoratee:
            case base.AsyncDecorated():
                enter_context_t = AsyncEnterContextBase
            case base.MultiDecorated():
                enter_context_t = MultiEnterContextBase
            case _: assert False, 'Unreachable'

        enter_context: EnterContextBase[Params, Return] = enter_context_t()

        decorated: base.Decorated[Params, Return] = dataclasses.replace(
            decoratee, enter_contexts=tuple([enter_context, *decoratee.enter_contexts])
        )

        decorated.register.decorateds[decorated.register_key] = decorated

        return decorated
