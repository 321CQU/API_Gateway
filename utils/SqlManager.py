from abc import ABC, abstractmethod
from typing import Iterable, Any
from contextlib import asynccontextmanager

import aiosqlite

from utils.Exceptions import _321CQUException
from utils.AbstractSql import AbstractConnection, AbstractAioCursor
from utils.Settings import ConfigHandler, BASE_DIR

__all__ = ['SqlManager', 'SqliteManager']


class SqlManager(ABC):
    """
    基于该类实现数据库调用依赖注入，同时支持单元测试时注入mock数据库
    实现该类请支持execute自动提交
    """

    @abstractmethod
    async def connect(self) -> AbstractConnection:
        pass

    @abstractmethod
    async def execute(self, sql: str, parameters: Iterable[Any] = None) -> AbstractAioCursor:
        pass

    @abstractmethod
    async def executemany(
            self, sql: str, parameters: Iterable[Iterable[Any]]
    ) -> AbstractAioCursor:
        pass


class SqliteManager(SqlManager):
    def __init__(self):
        self.connect_args = (str(BASE_DIR) + ConfigHandler().get_config('DatabaseSetting', 'dev_path'),)

    @asynccontextmanager
    async def connect(self, ignore_error: bool = True) -> aiosqlite.Connection:
        async with aiosqlite.connect(*self.connect_args) as db:
            try:
                yield db
            except aiosqlite.OperationalError as e:
                await db.rollback()
                if not ignore_error:
                    raise _321CQUException(error_info='数据库异常: ' + e.sqlite_errorname)
            finally:
                await db.commit()

    @asynccontextmanager
    async def execute(self, sql: str, parameters: Iterable[Any] = None, ignore_error: bool = True) -> aiosqlite.Cursor:
        async with self.connect(ignore_error=ignore_error) as db:
            async with db.execute(sql, parameters) as cursor:
                yield cursor

    @asynccontextmanager
    async def executemany(
            self, sql: str, parameters: Iterable[Iterable[Any]], ignore_error: bool = True
    ) -> aiosqlite.Cursor:
        async with self.connect(ignore_error=ignore_error) as db:
            async with db.executemany(sql, parameters) as cursor:
                yield cursor

