from __future__ import annotations

import abc
import builtins
import dataclasses
import inspect
import sys
import types
import typing


class Exception(Exception): ...  # noqa

@typing.runtime_checkable
class Decoratee[** Param, Ret](typing.Protocol):
    @typing.overload
    async def __call__(*args: Param.args, **kwargs: Param.kwargs) -> Ret: ...
    @typing.overload
    def __call__(*args: Param.args, **kwargs: Param.kwargs) -> Ret: ...
    def __call__(*args, **kwargs): ...

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
class Base[
    _CooperativeExit,
    _SynchronousExit,
    _CooperativeEnter,
    _SynchronousEnter,
    _CooperativeDecorated,
    _SynchronousDecorated,
    _Decorator,
](
    abc.ABC
):

    @property
    def cooperative_decoratee_t(self) -> type[CooperativeDecoratee]:
        return CooperativeDecoratee

    @property
    def synchronous_decoratee_t(self) -> type[SynchronousDecoratee]:
        return SynchronousDecoratee

    @property
    def cooperative_exit_t(self) -> type[_CooperativeExit]:
        return inspect.getmodule(type(self)).CooperativeExit

    @property
    def synchronous_exit_t(self) -> type[_SynchronousExit]:
        return inspect.getmodule(type(self)).SynchronousExit

    @property
    def cooperative_enter_t(self) -> type[_CooperativeEnter]:
        return inspect.getmodule(type(self)).CooperativeEnter

    @property
    def synchronous_enter_t(self) -> type[_SynchronousEnter]:
        return inspect.getmodule(type(self)).SynchronousEnter

    @property
    def cooperative_decorated_t(self) -> type[_CooperativeDecorated]:
        return inspect.getmodule(type(self)).CooperativeDecorated

    @property
    def synchronous_decorated_t(self) -> type[_SynchronousDecorated]:
        return inspect.getmodule(type(self)).SynchronousDecorated

    @property
    def decorator_t(self) -> type[_Decorator]:
        return inspect.getmodule(type(self)).Decorator


@dataclasses.dataclass(frozen=True, kw_only=True)
class Call[Decoratee, Exit, Enter, Decorated, Decorator](Base, abc.ABC):

    @property
    @abc.abstractmethod
    def decoratee_t(self) -> type[Decoratee]: ...

    @property
    @abc.abstractmethod
    def exit_t(self) -> type[Exit]: ...

    @property
    @abc.abstractmethod
    def enter_t(self) -> type[Enter]: ...

    @property
    @abc.abstractmethod
    def decorated_t(self) -> type[Decorated]: ...

    @typing.overload
    @abc.abstractmethod
    async def __call__(self, *args, **kwargs): ...
    @typing.overload
    @abc.abstractmethod
    def __call__(self, *args, **kwargs): ...
    @abc.abstractmethod
    def __call__(self, *args, **kwargs): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class Cooperative[Decoratee, Exit, Enter, Decorated, Decorator](
    Call[Decoratee, Exit, Enter, Decorated, Decorator],
    abc.ABC,
):

    @property
    def decoratee_t(self) -> type[Decoratee]:
        return self.cooperative_decoratee_t

    @property
    def exit_t(self) -> type[Exit]:
        return self.cooperative_exit_t

    @property
    def enter_t(self) -> type[Enter]:
        return self.cooperative_enter_t

    @property
    def decorated_t(self) -> type[Decorated]:
        return self.cooperative_decorated_t

    @abc.abstractmethod
    async def __call__(self, *args, **kwargs): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class Synchronous[Decoratee, Exit, Enter, Decorated, Decorator](
    Call[Decoratee, Exit, Enter, Decorated, Decorator],
    abc.ABC,
):

    @property
    def decoratee_t(self) -> type[Decoratee]:
        return self.synchronous_decoratee_t

    @property
    def exit_t(self) -> type[Exit]:
        return self.synchronous_exit_t

    @property
    def enter_t(self) -> type[Enter]:
        return self.synchronous_enter_t

    @property
    def decorated_t(self) -> type[Decorated]:
        return self.synchronous_decorated_t

    @abc.abstractmethod
    def __call__(self, *args, **kwargs): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class Exit[** Param, Ret, _Decoratee, _Enter, _Decorated, _Decorator](
    Call[_Decoratee, typing.Self, _Enter, _Decorated, _Decorator],
    abc.ABC,
):
    enter: _Enter

    @typing.overload
    @abc.abstractmethod
    async def __call__(self, result: Ret | Raise) -> ...: ...
    @typing.overload
    @abc.abstractmethod
    def __call__(self, result: Ret | Raise) -> ...: ...
    @abc.abstractmethod
    def __call__(self, *args, **kwargs): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class Enter[** Param, Ret, _Decoratee, _Exit, _Decorated, _Decorator](
    Call[_Decoratee, _Exit, typing.Self, _Decorated, _Decorator],
    abc.ABC,
):
    decorated: _Decorated

    @typing.overload
    @abc.abstractmethod
    async def __call__(self, *args: Param.args, **kwargs: Param.kwargs) -> ...: ...
    @typing.overload
    @abc.abstractmethod
    def __call__(self, *args: Param.args, **kwargs: Param.kwargs) -> ...: ...
    @abc.abstractmethod
    def __call__(self, *args, **kwargs): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class Decorated[** Param, Ret, _Decoratee, _Exit, _Enter, _Decorator](
    Call[_Decoratee, _Exit, _Enter, typing.Self, _Decorator],
    abc.ABC,
):
    __doc__: str
    __module__: str
    __name__: str
    __qualname__: str
    __signature__: inspect.Signature
    decoratee: _Decoratee
    decorator: _Decorator

    def __get__(self, instance: Instance, owner) -> typing.Self:
        return dataclasses.replace(self, decoratee=self.decoratee.__get__(instance, owner))


@dataclasses.dataclass(frozen=True, kw_only=True)
class CooperativeExit[
    ** Param,
    Ret,
    _Decoratee,
    _Enter,
    _Decorated,
    _Decorator,
](
    Cooperative[_Decoratee, typing.Self, _Enter, _Decorated, _Decorator],
    Exit[Param, Ret, _Decoratee, _Enter, _Decorated, _Decorator],
    abc.ABC,
):
    async def __call__(self, result: Raise | Ret) -> ():
        return tuple()


@dataclasses.dataclass(frozen=True, kw_only=True)
class SynchronousExit[
    ** Param,
    Ret,
    _Decoratee,
    _Enter,
    _Decorated,
    _Decorator,
](
    Synchronous[_Decoratee, typing.Self, _Enter, _Decorated, _Decorator],
    Exit[Param, Ret, _Decoratee, _Enter, _Decorated, _Decorator],
    abc.ABC,
):

    def __call__(self, result: Raise | Ret) -> ():
        return tuple()


@dataclasses.dataclass(frozen=True, kw_only=True)
class CooperativeEnter[** Param, Ret, _Decoratee, _Exit, _Decorated, _Decorator](
    Cooperative[_Decoratee, _Exit, typing.Self, _Decorated, _Decorator],
    Enter[Param, Ret, _Decoratee, _Exit, _Decorated, _Decorator],
    abc.ABC,
):
    async def __call__(self, *args: Param.args, **kwargs: Param.kwargs) -> (CooperativeDecoratee[Param, Ret],):
        return tuple([self.decorated.decoratee])


@dataclasses.dataclass(frozen=True, kw_only=True)
class SynchronousEnter[** Param, Ret, _Decoratee, _Exit, _Decorated, _Decorator](
    Synchronous[_Decoratee, _Exit, typing.Self, _Decorated, _Decorator],
    Enter[Param, Ret, _Decoratee, _Exit, _Decorated, _Decorator],
    abc.ABC,
):
    def __call__(self, *args: Param.args, **kwargs: Param.kwargs) -> (SynchronousDecoratee[Param, Ret],):
        return tuple([self.decorated.decoratee])


@dataclasses.dataclass(frozen=True, kw_only=True)
class CooperativeDecorated[** Param, Ret, _Decoratee, _Exit, _Enter, _Decorator](
    Cooperative[_Decoratee, _Exit, _Enter, typing.Self, _Decorator],
    Decorated[Param, Ret, _Decoratee, _Exit, _Enter, _Decorator],
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
            except builtins.Exception:  # noqa
                result = Raise(*sys.exc_info())

        if isinstance(result, Raise):
            raise result.exc_val

        return result


@dataclasses.dataclass(frozen=True, kw_only=True)
class SynchronousDecorated[** Param, Ret, _Decoratee, _Exit, _Enter, _Decorator](
    Synchronous[_Decoratee, _Exit, _Enter, typing.Self, _Decorator],
    Decorated[Param, Ret, _Decoratee, _Exit, _Enter, _Decorator],
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
            except builtins.Exception:  # noqa
                result = Raise(*sys.exc_info())

        if isinstance(result, Raise):
            raise result.exc_val

        return result


@dataclasses.dataclass(frozen=True, kw_only=True)
class Decorator[** Param, Ret, _CooperativeDecorated, _SynchronousDecorated](Base, abc.ABC):

    @typing.overload
    def __call__[** Param, Ret](self, decoratee: CooperativeDecoratee[Param, Ret], /) -> _CooperativeDecorated: ...
    @typing.overload
    def __call__[** Param, Ret](self, decoratee: SynchronousDecoratee[Param, Ret], /) -> _SynchronousDecorated: ...
    def __call__(self, decoratee, /):
        return (
            self.cooperative_decorated_t
            if inspect.iscoroutinefunction(decoratee) else
            self.synchronous_decorated_t
        )(
            __doc__=str(decoratee.__doc__),
            __module__=str(decoratee.__module__),
            __name__=str(decoratee.__name__),
            __qualname__=str(decoratee.__qualname__),
            __signature__=inspect.signature(decoratee),
            decoratee=decoratee,
            decorator=self,
        )


