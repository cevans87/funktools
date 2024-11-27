from __future__ import annotations

import abc
import dataclasses
import inspect
import sys
import types
import typing


@typing.runtime_checkable
class Decoratee[** Param, Ret](typing.Protocol):
    def __call__(*args: Param.args, **kwargs: Param.kwargs) -> typing.Awaitable[Ret] | Ret: ...
    def __get__(self, instance: Instance, owner) -> typing.Self: ...


@typing.runtime_checkable
class CooperativeDecoratee[** Param, Ret](typing.Protocol):
    async def __call__(*args: Param.args, **kwargs: Param.kwargs) -> Ret: ...
    def __get__(self, instance: Instance, owner) -> typing.Self: ...


@typing.runtime_checkable
class SynchronousDecoratee[** Param, Ret](typing.Protocol):
    def __call__(*args: Param.args, **kwargs: Param.kwargs) -> Ret: ...
    def __get__(self, instance: Instance, owner) -> typing.Self: ...


type Instance = object
type Name = typing.Annotated[str, annotated_types.Predicate(str.isidentifier)]  # noqa


@dataclasses.dataclass(frozen=True)
class Raise:
    exc_type: type[BaseException]
    exc_val: BaseException
    exc_tb: types.TracebackType


@dataclasses.dataclass(frozen=True, kw_only=True)
class Base(abc.ABC):

    @property
    def cooperative_decorated_t(self) -> type[CooperativeDecorated]:
        return inspect.getmodule(type(self)).CooperativeDecorated

    @property
    def synchronous_decorated_t(self) -> type[SynchronousDecorated]:
        return inspect.getmodule(type(self)).SynchronousDecorated

    @property
    def cooperative_enter_t(self) -> type[CooperativeEnter]:
        return inspect.getmodule(type(self)).CooperativeEnter

    @property
    def synchronous_enter_t(self) -> type[SynchronousEnter]:
        return inspect.getmodule(type(self)).SynchronousEnter

    @property
    def cooperative_exit_t(self) -> type[CooperativeExit]:
        return inspect.getmodule(type(self)).CooperativeExit

    @property
    def synchronous_exit_t(self) -> type[SynchronousExit]:
        return inspect.getmodule(type(self)).SynchronousExit


@dataclasses.dataclass(frozen=True, kw_only=True)
class Cooperative(Base, abc.ABC):

    @property
    def decorated_t(self) -> type[CooperativeDecorated]:
        return self.cooperative_decorated_t

    @property
    def enter_t(self) -> type[CooperativeEnter]:
        return self.cooperative_enter_t

    @property
    def exit_t(self) -> type[CooperativeExit]:
        return self.cooperative_exit_t

    @abc.abstractmethod
    async def __call__(self, *args, **kwargs): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class Synchronous(Base, abc.ABC):

    @property
    def decorated_t(self) -> type[SynchronousDecorated]:
        return self.synchronous_decorated_t

    @property
    def enter_t(self) -> type[SynchronousEnter]:
        return self.synchronous_enter_t

    @property
    def exit_t(self) -> type[SynchronousExit]:
        return self.synchronous_exit_t

    @abc.abstractmethod
    def __call__(self, *args, **kwargs): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class Exit[** Param, Ret, Decoratee, Exit, Enter, Decorated, Decorator](Base, abc.ABC):
    enter: Enter


@dataclasses.dataclass(frozen=True, kw_only=True)
class CooperativeExit[
    ** Param,
    Ret,
    Enter,
    Decorated,
    Decorator,
](
    Cooperative,
    Exit[
        Param,
        Ret,
        CooperativeDecoratee[Param, Ret],
        typing.Self,
        Enter,
        Decorated,
        Decorator,
    ],
    abc.ABC,
):
    async def __call__(self, result: Raise | Ret) -> ():
        return tuple()


@dataclasses.dataclass(frozen=True, kw_only=True)
class SynchronousExit[
    ** Param,
    Ret,
    Enter,
    Decorated,
    Decorator,
](
    Synchronous,
    Exit[
        Param,
        Ret,
        SynchronousDecoratee[Param, Ret],
        typing.Self,
        Enter,
        Decorated,
        Decorator,
    ],
    abc.ABC,
):

    def __call__(self, result: Raise | Ret) -> ():
        return tuple()


@dataclasses.dataclass(frozen=True, kw_only=True)
class Enter[** Param, Ret, Decoratee, Exit, Enter, Decorated, Decorator](Base, abc.ABC):
    decorated: Decorated


@dataclasses.dataclass(frozen=True, kw_only=True)
class CooperativeEnter[
    ** Param,
    Ret,
    Decorated,
    Decorator,
](
    Cooperative,
    Enter[
        Param,
        Ret,
        CooperativeDecoratee[Param, Ret],
        CooperativeExit[Param, Ret, typing.Self, Decorated, Decorator],
        typing.Self,
        Decorated,
        Decorator,
    ],
    abc.ABC,
):
    async def __call__(self, *args: Param.args, **kwargs: Param.kwargs) -> (CooperativeDecoratee[Param, Ret],):
        return tuple([self.decorated.decoratee])


@dataclasses.dataclass(frozen=True, kw_only=True)
class SynchronousEnter[** Param, Ret, Decorated, Decorator](
    Synchronous,
    Enter[
        Param,
        Ret,
        SynchronousDecoratee[Param, Ret],
        SynchronousExit[Param, Ret, typing.Self, Decorated, Decorator],
        typing.Self,
        Decorated,
        Decorator,
    ],
    abc.ABC,
):
    def __call__(self, *args: Param.args, **kwargs: Param.kwargs) -> (SynchronousDecoratee[Param, Ret],):
        return tuple([self.decorated.decoratee])


@dataclasses.dataclass(frozen=True, kw_only=True)
class Decorated[** Param, Ret, Decoratee, Exit, Enter, Decorated, Decorator](Base, abc.ABC):
    __doc__: str
    __module__: str
    __name__: str
    __qualname__: str
    decoratee: Decoratee
    decorator: Decorator

    @property
    @abc.abstractmethod
    def decorated_t(self) -> type[Decorated]: ...

    @property
    @abc.abstractmethod
    def enter_t(self) -> type[Enter]: ...

    @property
    @abc.abstractmethod
    def exit_t(self) -> type[Exit]: ...

    def __get__(self, instance: Instance, owner) -> typing.Self:
        return dataclasses.replace(self, decoratee=self.decoratee.__get__(instance, owner))


@dataclasses.dataclass(frozen=True, kw_only=True)
class CooperativeDecorated[** Param, Ret, Decorator](
    Cooperative,
    Decorated[
        Param,
        Ret,
        CooperativeDecoratee[Param, Ret],
        CooperativeExit[Param, Ret, CooperativeEnter[Param, Ret, typing.Self, Decorator], typing.Self, Decorator],
        CooperativeEnter[Param, Ret, typing.Self, Decorator],
        typing.Self,
        Decorator,
    ],
    abc.ABC,
):

    @typing.final
    async def __call__(self, *args: Param.args, **kwargs: Param.kwargs) -> Ret:
        result: Raise | Ret = ...
        stack = [self]
        while stack:
            try:
                match stack.pop():
                    case Decorated() as decorated:
                        stack.append(decorated.enter_t(decorated=decorated))
                    case Enter() as enter:
                        stack.extend(await enter(*args, **kwargs))
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
class SynchronousDecorated[** Param, Ret, Decorator](
    Synchronous,
    Decorated[
        Param,
        Ret,
        SynchronousDecoratee[Param, Ret],
        SynchronousExit[Param, Ret, SynchronousEnter[Param, Ret, typing.Self, Decorator], typing.Self, Decorator],
        SynchronousEnter[Param, Ret, typing.Self, Decorator],
        typing.Self,
        Decorator,
    ],
    abc.ABC,
):

    @typing.final
    def __call__(self, *args: Param.args, **kwargs: Param.kwargs) -> Ret:
        result: Raise | Ret = ...
        stack = [self]
        while stack:
            try:
                match stack.pop():
                    case Decorated() as decorated:
                        stack.append(decorated.enter_t(decorated=decorated))
                    case Enter() as enter:
                        stack.extend(enter(*args, **kwargs))
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
class Decorator[** Param, Ret, CooperativeDecorated, SynchronousDecorated](
    Base,
    abc.ABC,
):

    @typing.overload
    def __call__[** Param, Ret](self, decoratee: CooperativeDecoratee[Param, Ret], /) -> CooperativeDecorated: ...
    @typing.overload
    def __call__[** Param, Ret](self, decoratee: SynchronousDecoratee[Param, Ret], /) -> SynchronousDecorated: ...
    def __call__[** Param, Ret](self, decoratee, /):
        return (
            self.cooperative_decorated_t[Param, Ret, typing.Self]
            if inspect.iscoroutinefunction(decoratee) else
            self.synchronous_decorated_t[Param, Ret, typing.Self]
        )(
            __doc__=str(decoratee.__doc__),
            __module__=str(decoratee.__module__),
            __name__=str(decoratee.__name__),
            __qualname__=str(decoratee.__qualname__),
            decoratee=decoratee,
            decorator=self,
        )


