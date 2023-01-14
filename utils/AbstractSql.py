from abc import abstractmethod, ABC
from typing import Iterable, Optional, Any

__all__ = ['AbstractRow', 'AbstractConnection', 'AbstractAioCursor']


class AbstractRow(ABC):
    # no doc
    @abstractmethod
    def keys(self, *args, **kwargs):  # real signature unknown
        """ Returns the keys of the row. """
        pass


class AbstractAioCursor(ABC):
    @abstractmethod
    async def execute(self, sql: str, parameters: Iterable[Any] = None) -> "AbstractAioCursor":
        pass

    @abstractmethod
    async def executemany(
            self, sql: str, parameters: Iterable[Iterable[Any]]
    ) -> "AbstractAioCursor":
        pass

    @abstractmethod
    async def fetchone(self) -> Optional[AbstractRow]:
        pass

    @abstractmethod
    async def fetchmany(self, size: int = None) -> Iterable[AbstractRow]:
        pass

    @abstractmethod
    async def fetchall(self) -> Iterable[AbstractRow]:
        pass

    @abstractmethod
    async def close(self) -> None:
        pass


class AbstractConnection(ABC):
    @abstractmethod
    async def cursor(self) -> AbstractAioCursor:
        pass

    @abstractmethod
    async def commit(self) -> None:
        pass

    @abstractmethod
    async def rollback(self) -> None:
        pass

    @abstractmethod
    async def close(self) -> None:
        pass

    @abstractmethod
    async def execute(self, sql: str, parameters: Iterable[Any] = None) -> AbstractAioCursor:
        pass

    @abstractmethod
    async def executemany(
            self, sql: str, parameters: Iterable[Iterable[Any]]
    ) -> AbstractAioCursor:
        pass
