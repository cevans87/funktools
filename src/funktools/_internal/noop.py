from __future__ import annotations

import abc
import dataclasses

from . import base


@dataclasses.dataclass(frozen=True, kw_only=True)
class Base[** Param, Ret](base.Base[Param, Ret], abc.ABC): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class Context[** Param, Ret](Base[Param, Ret], base.Context[Param, Ret], abc.ABC): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class Async[** Param, Ret](base.Async[Param, Ret], Context[Param, Ret], abc.ABC): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class Multi[** Param, Ret](base.Multi[Param, Ret], Context[Param, Ret], abc.ABC): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class Enter[** Param, Ret](base.Enter[Param, Ret], Context[Param, Ret], abc.ABC): ...

@dataclasses.dataclass(frozen=True, kw_only=True)
class Exit[** Param, Ret](base.Exit[Param, Ret], Context[Param, Ret], abc.ABC): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class AsyncEnter[** Param, Ret](base.AsyncEnter[Param, Ret], Async[Param, Ret], Enter[Param, Ret]): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class MultiEnter[** Param, Ret](base.MultiEnter[Param, Ret], Multi[Param, Ret], Enter[Param, Ret]): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class AsyncExit[** Param, Ret](base.AsyncExit[Param, Ret], Async[Param, Ret], Exit[Param, Ret]): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class MultiExit[** Param, Ret](base.MultiExit[Param, Ret], Multi[Param, Ret], Exit[Param, Ret]): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class Decorated[** Param, Ret](base.Decorated[Param, Ret], Base[Param, Ret], abc.ABC): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class AsyncDecorated[** Param, Ret](base.AsyncDecorated[Param, Ret], Decorated[Param, Ret]): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class MultiDecorated[** Param, Ret](base.MultiDecorated[Param, Ret], Decorated[Param, Ret]): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class Decorator[** Param, Ret](base.Decorator[Param, Ret]): ...
