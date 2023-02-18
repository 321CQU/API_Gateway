from typing import Iterable, Any
from contextlib import asynccontextmanager

import aiosqlite

from _321CQU.tools import Singleton
from _321CQU.sql_helper import SqlManager

from utils.Exceptions import _321CQUException
from utils.Settings import ConfigManager, BASE_DIR

__all__ = ['SqlManager', 'SqliteManager']


class SqliteManager(metaclass=Singleton):
    def __init__(self):
        self.connect_args = (str(BASE_DIR) + ConfigManager().get_config('DatabaseSetting', 'dev_path'),)

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

