from __future__ import annotations

import abc
import annotated_types
import ast
import asyncio
import collections
import dataclasses
import inspect
import pathlib
import sqlite3
import textwrap
import threading
import typing

from . import base

type Key = str

type LoadsValue[Ret] = typing.Callable[[bytes], Ret]
type DumpsKey[** Param] = typing.Callable[Param, Key]
type DumpsValue[Ret] = typing.Callable[[Ret], bytes]


@dataclasses.dataclass(frozen=True, kw_only=True)
class Base[** Param, Ret](base.Base[Param, Ret], abc.ABC): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class Async[** Param, Ret](Base[Param, Ret], base.Async[Param, Ret], abc.ABC):
    lock: asyncio.Lock = dataclasses.field(default_factory=asyncio.Lock)


@dataclasses.dataclass(frozen=True, kw_only=True)
class Multi[** Param, Ret](Base[Param, Ret], base.Multi[Param, Ret], abc.ABC):
    lock: threading.Lock = dataclasses.field(default_factory=threading.Lock)


@dataclasses.dataclass(frozen=True, kw_only=True)
class Enter[** Param, Ret](base.Enter[Param, Ret], abc.ABC):
    connection: sqlite3.Connection
    dumps_key: DumpsKey[Param]
    dumps_value: DumpsValue[Ret]
    exit_context_by_key: collections.OrderedDict[Key, ExitContext[Param, Ret]]
    loads_value: LoadsValue[Ret]
    table_name: str

    def __post_init__(
        self: AsyncEnterContext[Param, Ret] | MultiEnterContext[Param, Ret],
    ) -> None:
        self.connection.execute(textwrap.dedent(f'''
            CREATE TABLE IF NOT EXISTS `{self.table_name}` (
                key STRING PRIMARY KEY NOT NULL UNIQUE,
                value STRING NOT NULL
            )
        ''').strip())

    def __call__(
        self: AsyncEnterContext[Param, Ret] | MultiEnterContext[Param, Ret],
        key: Key,
    ):
        match self.connection.execute(
            f'SELECT value FROM `{self.table_name}` WHERE key = ?', (key,)
        ).fetchall():
            case [[value]]:
                return ast.literal_eval(value)
        exit_context = self.exit_context_by_key[key] = self.exit_context_t(
            connection=self.connection,
            dumps_value=self.dumps_value,
            key=key,
            table_name=self.table_name,
        )

        return exit_context, self.next_enter_context

    def __get__(self, instance, owner):
        with self.instance_lock:
            if (enter_context := self.enter_context_by_instance.get(instance)) is None:
                enter_context = self.enter_context_by_instance[instance] = dataclasses.replace(
                    self,
                    connection=self.connection,
                    instance=instance,
                    next_enter_context=self.next_enter_context.__get__(instance, owner),
                    table_name=f'{self.table_name}__{instance}',
                )
            return enter_context


@dataclasses.dataclass(frozen=True, kw_only=True)
class Exit[** Param, Ret](base.Exit[Param, Ret], abc.ABC):
    connection: sqlite3.Connection
    dumps_value: DumpsValue[Ret]
    key: Key
    table_name: str

    @abc.abstractmethod
    def __call__(
        self: AsyncExitContext[Param, Ret] | MultiExitContext[Param, Ret],
        result: base.Raise | Ret,
    ) -> Ret:

        try:
            if isinstance(result, base.Raise):
                raise result.e
            else:
                self.connection.execute(
                    f'''INSERT INTO `{self.table_name}` (key, value) VALUES (?, ?)''',
                    (self.key, self.dumps_value(result))
                )
                return result
        finally:
            self.event.set()


@dataclasses.dataclass(frozen=True, kw_only=True)
class AsyncEnter[** Param, Ret](Async[Param, Ret], Enter[Param, Ret], base.AsyncEnter[Param, Ret]):
    exit_context_by_key: collections.OrderedDict[Key, AsyncExitContext[Param, Ret]] = dataclasses.field(
        default_factory=collections.OrderedDict
    )
    lock: asyncio.Lock = dataclasses.field(default_factory=asyncio.Lock)

    async def __call__(
        self,
        *args: Param.args,
        **kwargs: Param.kwargs,
    ) -> (AsyncExit[Param, Ret], base.AsyncEnter[Param, Ret]) | Ret:
        key = self.dumps_key(*args, **kwargs)
        async with self.lock:
            if (exit_context := self.exit_context_by_key.get(key)) is not None:
                self.lock.release()
                try:
                    await exit_context.event.wait()
                finally:
                    await self.lock.acquire()
                self.exit_context_by_key.pop(key, None)

            return super().__call__(key)


@dataclasses.dataclass(frozen=True, kw_only=True)
class MultiEnter[** Param, Ret](Multi[Param, Ret], Enter[Param, Ret], base.MultiEnter[Param, Ret]):
    exit_context_by_key: collections.OrderedDict[Key, MultiExitContext[Param, Ret]] = dataclasses.field(
        default_factory=collections.OrderedDict
    )
    lock: threading.Lock = dataclasses.field(default_factory=threading.Lock)

    @property
    def exit_context_t(self) -> type[MultiExitContext]:
        return MultiExitContext

    def __call__(
        self,
        *args: Param.args,
        **kwargs: Param.kwargs,
    ) -> tuple[MultiExit[Param, Ret], base.Decoratee[Param, Ret]] | (Ret,):
        key = self.dumps_key(*args, **kwargs)
        with self.lock:
            if (exit_context := self.exit_context_by_key.get(key)) is not None:
                self.lock.release()
                try:
                    exit_context.event.wait()
                finally:
                    self.lock.acquire()
                self.exit_context_by_key.pop(key, None)

            return super().__call__(key)


@dataclasses.dataclass(frozen=True, kw_only=True)
class AsyncExit[** Param, Ret](Async[Param, Ret], Exit[Param, Ret], base.AsyncExit[Param, Ret]):
    event: asyncio.Event = dataclasses.field(default_factory=asyncio.Event)

    async def __call__(self, result: base.Raise | Ret) -> Ret:
        return super().__call__(result)


@dataclasses.dataclass(frozen=True, kw_only=True)
class MultiExit[** Param, Ret](Multi[Param, Ret], Exit[Param, Ret], base.MultiExit[Param, Ret]):
    event: threading.Event = dataclasses.field(default_factory=threading.Event)

    def __call__(self, result: base.Raise | Ret) -> Ret:
        return super().__call__(result)


@dataclasses.dataclass(frozen=True, kw_only=True)
class Decorated[** Param, Ret](base.Decorated[Param, Ret], Base[Param, Ret], abc.ABC): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class AsyncDecorated[** Param, Ret](base.AsyncDecorated[Param, Ret], Decorated[Param, Ret]): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class MultiDecorated[** Param, Ret](base.MultiDecorated[Param, Ret], Decorated[Param, Ret]): ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class Decorator[** Param, Ret](base.Decorator[Param, Ret]):
    db_path: pathlib.Path | str = 'file::memory:?cache=shared'
    dumps_key: DumpsKey = ...
    dumps_value: DumpsValue[Ret] = repr
    duration: typing.Annotated[float, annotated_types.Ge(0.0)] | None = None
    loads_value: LoadsValue[Ret] = ast.literal_eval

    @typing.overload
    def __call__(self, decoratee: base.AsyncDecoratee[Param, Ret], /) -> AsyncDecorated[Param, Ret]: ...
    @typing.overload
    def __call__(self, decoratee: base.MultiDecoratee[Param, Ret], /) -> MultiDecorated[Param, Ret]: ...
    def __call__(self, decoratee, /):
        decoratee = super().__call__(decoratee)

        if (dumps_key := self.dumps_key) is ...:
            def dumps_key(*args, **kwargs) -> Key:
                bound = inspect.signature(decoratee).bind(*args, **kwargs)
                bound.apply_defaults()
                return repr((bound.args, tuple(sorted(bound.kwargs))))

        if inspect.iscoroutinefunction(decoratee):
            decorated_t: type[AsyncDecorated[Param, Ret]] = AsyncDecorated[Param, Ret]
        else:
            decorated_t: type[MultiDecorated[Param, Ret]] = MultiDecorated[Param, Ret]

        decorated = decorated_t(
            decoratee=decoratee,
            connection=sqlite3.connect(self.db_path, isolation_level=None),
            dumps_key=dumps_key,
            dumps_value=self.dumps_value,
            loads_value=self.loads_value,
            next_enter_context=decoratee.enter_context,
            table_name='__'.join(decoratee.register_key),
        )

        return decorated
