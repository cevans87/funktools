from builtins import *
import typing as _typing

class _mixin[T]:
    def filter[U](self, func: _typing.Callable[[T], U]) -> _typing.Iterable[U]:
        return (t for t in self if func(t))

    def map[U](self, func: _typing.Callable[[T], U]) -> _typing.Iterable[U]:
        return (func(t) for t in self)

    def reduce[U](self, func: _typing.Callable[[T], U]) -> _typing.Iterable[U]:
        return (func(t) for t in self)


class list[T](_mixin[T], list[T]):
    ...
