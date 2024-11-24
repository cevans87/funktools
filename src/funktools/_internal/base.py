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
class AsyncDecoratee[** Param, Ret](typing.Protocol):
    async def __call__(*args: Param.args, **kwargs: Param.kwargs) -> Ret: ...


@typing.runtime_checkable
class MultiDecoratee[** Param, Ret](typing.Protocol):
    def __call__(*args: Param.args, **kwargs: Param.kwargs) -> Ret: ...


@typing.runtime_checkable
class Decoratee[** Param, Ret](typing.Protocol):
    def __call__(*args: Param.args, **kwargs: Param.kwargs) -> typing.Awaitable[Ret] | Ret: ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class Base[** Param, Ret](abc.ABC):
    decoratee: Decoratee[Param, Ret]

    @property
    def async_enter_t(self) -> type[AsyncEnter[Param, Ret]]:
        return inspect.getmodule(type(self)).AsyncEnter

    @property
    def multi_enter_t(self) -> type[MultiEnter[Param, Ret]]:
        return inspect.getmodule(type(self)).MultiEnter

    @property
    def async_exit_t(self) -> type[AsyncExit[Param, Ret]]:
        return inspect.getmodule(type(self)).AsyncExit

    @property
    def multi_exit_t(self) -> type[MultiExit[Param, Ret]]:
        return inspect.getmodule(type(self)).MultiExit

    @property
    def async_decorated_t(self) -> type[AsyncDecorated[Param, Ret]]:
        return inspect.getmodule(type(self)).AsyncDecorated

    @property
    def multi_decorated_t(self) -> type[MultiDecorated[Param, Ret]]:
        return inspect.getmodule(type(self)).MultiDecorated


@dataclasses.dataclass(frozen=True, kw_only=True)
class Async[** Param, Ret](Base[Param, Ret], abc.ABC):

    @property
    def enter_t(self) -> type[AsyncEnter[Param, Ret]]:
        return self.async_enter_t

    @property
    def exit_t(self) -> type[AsyncExit[Param, Ret]]:
        return self.async_exit_t


@dataclasses.dataclass(frozen=True, kw_only=True)
class Multi[** Param, Ret](Base[Param, Ret], abc.ABC):

    @property
    def enter_t(self) -> type[MultiEnter[Param, Ret]]:
        return self.multi_enter_t

    @property
    def exit_t(self) -> type[MultiExit[Param, Ret]]:
        return self.multi_exit_t


@dataclasses.dataclass(frozen=True, kw_only=True)
class Context[** Param, Ret](Base[Param, Ret], abc.ABC):
    args: Param.args
    kwargs: Param.kwargs

    @property
    @abc.abstractmethod
    def enter_t(self) -> type[Enter[Param, Ret]]: ...

    @property
    @abc.abstractmethod
    def exit_t(self) -> type[Exit[Param, Ret]]: ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class Enter[** Param, Ret](Context[Param, Ret], abc.ABC): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class Exit[** Param, Ret](Context[Param, Ret], abc.ABC):

    def __call__(self, ret: Ret) -> typing.Generator[object, object, Ret]:
        return ret


@dataclasses.dataclass(frozen=True, kw_only=True)
class AsyncEnter[** Param, Ret](Async[Param, Ret], Enter[Param, Ret], abc.ABC):

    async def __call__(self) -> tuple[Decoratee[Param, Ret]]:
        return tuple([self.decoratee])


@dataclasses.dataclass(frozen=True, kw_only=True)
class MultiEnter[** Param, Ret](Multi[Param, Ret], Enter[Param, Ret], abc.ABC):

    def __call__(self) -> tuple[Decoratee[Param, Ret]]:
        return tuple([self.decoratee])


@dataclasses.dataclass(frozen=True, kw_only=True)
class AsyncExit[** Param, Ret](Async[Param, Ret], Exit[Param, Ret], abc.ABC):

    async def __call__(self, ret: Ret) -> tuple[()]:
        return tuple()


@dataclasses.dataclass(frozen=True, kw_only=True)
class MultiExit[** Param, Ret](Multi[Param, Ret], Exit[Param, Ret], abc.ABC):

    def __call__(self, ret: Ret) -> tuple[()]:
        return tuple()


@dataclasses.dataclass(frozen=True, kw_only=True)
class Decorated[** Param, Ret](Base[Param, Ret], abc.ABC):
    __doc__: str
    __module__: str
    __name__: str
    __qualname__: str

    def __get__(self, instance: Instance, owner) -> typing.Self:
        return dataclasses.replace(self, decoratee=self.decoratee.__get__(instance, owner))

    def to_enter(self, *args: Param.args, **kwargs: Param.kwargs) -> Enter[Param, Ret]:
        return self.enter_t(args=args, decoratee=self.decoratee, kwargs=kwargs)

@dataclasses.dataclass(frozen=True, kw_only=True)
class AsyncDecorated[** Param, Ret](Async[Param, Ret], Decorated[Param, Ret], abc.ABC):

    async def __call__(self, *args: Param.args, **kwargs: Param.kwargs) -> Ret:
        result: Raise | Ret = ...
        stack = [self]
        while stack:
            try:
                match stack.pop():
                    case Decorated() as decorated:
                        stack.append(decorated.to_enter(*args, **kwargs))
                    case Enter() as enter:
                        stack.extend(await enter())
                    case Exit() as exit_:
                        stack.extend(await exit_(result))
                    case Decoratee() as decoratee:
                        result = await decoratee(*args, **kwargs)
            except Exception:  # noqa
                result = Raise(*sys.exc_info())

        if isinstance(result, Raise):
            raise result.exc_val

        return result


@dataclasses.dataclass(frozen=True, kw_only=True)
class MultiDecorated[** Param, Ret](Multi[Param, Ret], Decorated[Param, Ret], abc.ABC):

    def __call__(self, *args: Param.args, **kwargs: Param.kwargs) -> Ret:
        result: Raise | Ret = ...
        stack = [self]
        while stack:
            try:
                match stack.pop():
                    case Decorated() as decorated:
                        stack.append(decorated.to_enter(*args, **kwargs))
                    case Enter() as enter:
                        stack.extend(enter())
                    case Exit() as exit_:
                        stack.extend(exit_(result))
                    case Decoratee() as decoratee:
                        result = decoratee(*args, **kwargs)
            except Exception:  # noqa
                result = Raise(*sys.exc_info())

        if isinstance(result, Raise):
            raise result.exc_val

        return result


@dataclasses.dataclass(frozen=True, kw_only=True)
class Decorator[** Param, Ret](abc.ABC):

    def __call__(self, decoratee: Decoratee[Param, Ret], /) -> Decorated[Param, Ret]:
        if inspect.iscoroutinefunction(decoratee):
            decorated_t: AsyncDecorated[Param, Ret] = inspect.getmodule(type(self)).AsyncDecorated
        else:
            decorated_t: MultiDecorated[Param, Ret] = inspect.getmodule(type(self)).MultiDecorated

        decorated = decorated_t(
                decoratee=decoratee,
                __doc__=str(decoratee.__doc__),
                __module__=str(decoratee.__module__),
                __name__=str(decoratee.__name__),
                __qualname__=str(decoratee.__qualname__),
        )

        return decorated
