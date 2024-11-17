from __future__ import annotations

import abc
import dataclasses
import inspect
import sys
import types
import typing

type Instance = object
type Name = typing.Annotated[str, annotated_types.Predicate(str.isidentifier)]  # noqa


@dataclasses.dataclass(frozen=True)
class Raise:
    exc_type: type[BaseException]
    exc_val: BaseException
    exc_tb: types.TracebackType


@typing.runtime_checkable
class AsyncDecoratee[** Params, Return](typing.Protocol):
    async def __call__(*args: Params.args, **kwargs: Params.kwargs) -> Return: ...


@typing.runtime_checkable
class MultiDecoratee[** Params, Return](typing.Protocol):
    def __call__(*args: Params.args, **kwargs: Params.kwargs) -> Return: ...


@typing.runtime_checkable
class Decoratee[** Params, Return](typing.Protocol):
    def __call__(*args: Params.args, **kwargs: Params.kwargs) -> typing.Awaitable[Return] | Return: ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class Base[** Params, Return](abc.ABC):
    decoratee: Decoratee[Params, Return]
    instance: Instance | None

    @property
    def async_enter_context_t(self) -> type[AsyncEnterContext[Params, Return]]:
        return inspect.getmodule(type(self)).AsyncEnterContext

    @property
    def async_exit_context_t(self) -> type[AsyncExitContext[Params, Return]]:
        return inspect.getmodule(type(self)).AsyncExitContext

    @property
    def async_decorated_t(self) -> type[AsyncDecorated[Params, Return]]:
        return inspect.getmodule(type(self)).AsyncDecorated

    @property
    def multi_enter_context_t(self) -> type[MultiEnterContext[Params, Return]]:
        return inspect.getmodule(type(self)).MultiEnterContext

    @property
    def multi_exit_context_t(self) -> type[MultiExitContext[Params, Return]]:
        return inspect.getmodule(type(self)).MultiExitContext

    @property
    def multi_decorated_t(self) -> type[MultiDecorated[Params, Return]]:
        return inspect.getmodule(type(self)).MultiDecorated


@dataclasses.dataclass(frozen=True, kw_only=True)
class AsyncBase[** Params, Return](Base[Params, Return], abc.ABC):

    @property
    def enter_context_t(self) -> type[AsyncEnterContext[Params, Return]]:
        return self.async_enter_context_t

    @property
    def exit_context_t(self) -> type[AsyncExitContext[Params, Return]]:
        return self.async_exit_context_t


@dataclasses.dataclass(frozen=True, kw_only=True)
class MultiBase[** Params, Return](Base[Params, Return], abc.ABC):

    @property
    def enter_context_t(self) -> type[MultiEnterContext[Params, Return]]:
        return self.multi_enter_context_t

    @property
    def exit_context_t(self) -> type[MultiExitContext[Params, Return]]:
        return self.multi_exit_context_t


@dataclasses.dataclass(frozen=True, kw_only=True)
class Context[** Params, Return](Base[Params, Return], abc.ABC):

    @abc.abstractmethod
    @property
    def enter_context_t(self) -> type[EnterContext[Params, Return]]: ...

    @abc.abstractmethod
    @property
    def exit_context_t(self) -> type[ExitContext[Params, Return]]: ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class AsyncContext[** Params, Return](Context[Params, Return], AsyncBase[Params, Return], abc.ABC): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class MultiContext[** Params, Return](Context[Params, Return], MultiBase[Params, Return], abc.ABC): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class EnterContext[** Params, Return](Context[Params, Return], abc.ABC): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class ExitContext[** Params, Return](Context[Params, Return], abc.ABC): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class AsyncEnterContext[** Params, Return](AsyncContext[Params, Return], EnterContext[Params, Return], abc.ABC):

    @property
    def context_t(self) -> type[AsyncEnterContext[Params, Return]]:
        return self.async_enter_context_t

    async def __call__(self, *args: Params.args, **kwargs: Params.kwargs) -> tuple[AsyncDecoratee[Params, Return]]:
        return tuple([self.decoratee])


@dataclasses.dataclass(frozen=True, kw_only=True)
class MultiEnterContext[** Params, Return](MultiContext[Params, Return], EnterContext[Params, Return], abc.ABC):

    @property
    def context_t(self) -> type[MultiEnterContext[Params, Return]]:
        return self.multi_enter_context_t

    def __call__(self, *args: Params.args, **kwargs: Params.kwargs) -> tuple[MultiDecoratee[Params, Return]]:
        return tuple([self.decoratee])


@dataclasses.dataclass(frozen=True, kw_only=True)
class AsyncExitContext[** Params, Return](AsyncContext[Params, Return], ExitContext[Params, Return], abc.ABC):

    @property
    def context_t(self) -> type[AsyncExitContext[Params, Return]]:
        return self.async_exit_context_t

    async def __call__(self, _return: Return | Raise) -> tuple[()]:
        return tuple()


@dataclasses.dataclass(frozen=True, kw_only=True)
class MultiExitContext[** Params, Return](MultiContext[Params, Return], ExitContext[Params, Return], abc.ABC):

    @property
    def context_t(self) -> type[MultiExitContext[Params, Return]]:
        return self.multi_exit_context_t

    def __call__(self, _return: Return | Raise) -> tuple[()]:
        return tuple()


@dataclasses.dataclass(frozen=True, kw_only=True)
class Decorated[** Params, Return](Context[Params, Return], abc.ABC):
    signature: inspect.Signature
    __doc__: str
    __module__: str
    __name__: str
    __qualname__: str

    @abc.abstractmethod
    @property
    def enter_context_t(self) -> type[EnterContext[Params, Return]]: ...

    @typing.overload
    async def __call__(self: AsyncDecorated[Params, Return], *args: Params.args, **kwargs: Params.kwargs) -> Return: ...

    @typing.overload
    def __call__(self: MultiDecorated[Params, Return], *args: Params.args, **kwargs: Params.kwargs) -> Return: ...

    @abc.abstractmethod
    def __call__(self): ...

    def __get__(self, instance: Instance, owner) -> typing.Self:
        return dataclasses.replace(self, instance=instance)

    @staticmethod
    def norm_kwargs(kwargs: Params.kwargs) -> Params.kwargs:
        return dict(sorted(kwargs.items()))

    def norm_args(self, args: Params.args) -> Params.args:
        return args if self.instance is None else [self.instance, *args]

    def to_enter_context(self) -> EnterContext[Params, Return]:
        return self.enter_context_t(decoratee=self.decoratee, instance=self.instance)


@dataclasses.dataclass(frozen=True, kw_only=True)
class AsyncDecorated[** Params, Return](
    Decorated[Params, Return],
    AsyncEnterContext[Params, Return],
    AsyncExitContext[Params, Return],
    abc.ABC,
):

    @property
    def enter_context_t(self) -> type[AsyncEnterContext[Params, Return]]:
        return inspect.getmodule(type(self)).AsyncEnterContext

    async def __call__(self, *args: Params.args, **kwargs: Params.kwargs) -> Return:
        args, kwargs = self.norm_args(args), self.norm_kwargs(kwargs)
        stack = [self]
        result: Raise | Return = ...

        while stack:
            try:
                match stack.pop():
                    case Decorated() as decorated:
                        stack.append(decorated.to_enter_context())
                    case EnterContext() as enter_context:
                        stack.extend(await enter_context(*args, **kwargs))
                    case ExitContext() as exit_context:
                        stack.extend(await exit_context(result))
                    case Decoratee() as decoratee:
                        result = await decoratee(*args, **kwargs)
            except Exception:  # noqa
                result = Raise(*sys.exc_info())

        if isinstance(result, Raise):
            raise result.exc_val

        return result


@dataclasses.dataclass(frozen=True, kw_only=True)
class MultiDecorated[** Params, Return](
    Decorated[Params, Return],
    MultiEnterContext[Params, Return],
    MultiExitContext[Params, Return],
    abc.ABC,
):

    @property
    def enter_context_t(self) -> type[MultiEnterContext[Params, Return]]:
        return inspect.getmodule(type(self)).MultiEnterContext

    def __call__(self, *args: Params.args, **kwargs: Params.kwargs) -> Return:
        args, kwargs = self.norm_args(args), self.norm_kwargs(kwargs)
        stack = [self.decoratee]
        result: Raise | Return = ...

        while stack:
            try:
                match stack.pop():
                    case Decorated() as decorated:
                        stack.append(decorated.enter_context_t(**dataclasses.asdict(decorated)))
                    case EnterContext() as enter_context:
                        stack.extend(enter_context(*args, **kwargs))
                    case ExitContext() as exit_context:
                        stack.extend(exit_context(result))
                    case Decoratee() as decoratee:
                        result = decoratee(*args, **kwargs)
            except Exception:  # noqa
                result = Raise(*sys.exc_info())

        if isinstance(result, Raise):
            raise result.exc_val

        return result


@dataclasses.dataclass(frozen=True, kw_only=True)
class Decorator[** Params, Return](abc.ABC):

    def __call__(
        self,
        decoratee: Decoratee[Params, Return],
        /,
    ) -> Decorated[Params, Return]:
        if inspect.iscoroutinefunction(decoratee):
            decorated_t: Decorated[Params, Return] = inspect.getmodule(type(self)).AsyncDecorated
        else:
            decorated_t: Decorated[Params, Return] = inspect.getmodule(type(self)).MultiDecorated

        decorated = decorated_t(
                decoratee=decoratee,
                instance=None,
                signature=inspect.signature(decoratee),
                __doc__=str(decoratee.__doc__),
                __module__=str(decoratee.__module__),
                __name__=str(decoratee.__name__),
                __qualname__=str(decoratee.__qualname__),
                **dataclasses.asdict(self),  # noqa
        )

        return decorated
