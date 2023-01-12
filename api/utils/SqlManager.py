from abc import ABC, abstractmethod

from typing import Iterable, Any

import aiosqlite


class SqlManager(ABC):
    @abstractmethod
    async def execute(self, sql: str, parameters: Iterable | None = None):
        pass

    @abstractmethod
    async def execute_many(self, sql: str, parameters: Iterable[Iterable]):
        pass

    @abstractmethod
    async def fetch_one(self) -> aiosqlite.Row | Any:
        pass

    @abstractmethod
    async def fetch_all(self) -> Iterable[aiosqlite.Row]:
        pass


class SqliteManager(SqlManager):
    def __init__(self, db: aiosqlite.Connection):
        self._db = db
        self.cursor: aiosqlite.Cursor | None = None

    def __del__(self):
        self.cursor.close()

    async def execute(self, sql: str, parameters: Iterable | None = None):
        self.cursor = await self._db.execute(sql, parameters)
        await self._db.commit()

    async def execute_many(self, sql: str, parameters: Iterable[Iterable]):
        self.cursor = await self._db.executemany(sql, parameters)
        await self._db.commit()

    async def fetch_one(self) -> aiosqlite.Row | Any:
        result = await self.cursor.fetchone()
        await self.cursor.close()
        self.cursor = None
        return result

    async def fetch_all(self) -> Iterable[aiosqlite.Row]:
        result = await self.cursor.fetchall()
        await self.cursor.close()
        self.cursor = None
        return result
