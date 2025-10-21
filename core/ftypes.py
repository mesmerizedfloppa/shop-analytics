# core/ftypes.py
# Functional small types: Maybe and Either
# Designed for immutability, simple API and backwards-compatibility with earlier code.

from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Generic, Optional, TypeVar, Union

T = TypeVar("T")
U = TypeVar("U")
L = TypeVar("L")
R = TypeVar("R")

# Maybe (optional value)


@dataclass(frozen=True)
class Maybe(Generic[T]):
    """
    Простая Maybe-обёртка (Option).
    Используем Maybe.some(value) или Maybe.nothing().
    Поддерживает map, bind, get_or_else, is_some/is_none.
    """

    value: Optional[T]

    # factories
    @staticmethod
    def some(value: T) -> "Maybe[T]":
        return Maybe(value)

    @staticmethod
    def nothing() -> "Maybe[None]":
        return Maybe(None)

    # compatibility: construction must work with frozen dataclass
    def __init__(self, value: Optional[T]):
        object.__setattr__(self, "value", value)

    # predicates
    def is_some(self) -> bool:
        return self.value is not None

    def is_none(self) -> bool:
        return self.value is None

    # functor / monad-ish operations
    def map(self, fn: Callable[[T], U]) -> "Maybe[U]":
        return Maybe.some(fn(self.value)) if self.is_some() else Maybe.nothing()

    def bind(self, fn: Callable[[T], "Maybe[U]"]) -> "Maybe[U]":
        return fn(self.value) if self.is_some() else Maybe.nothing()

    # extractor
    def get_or_else(self, default: U) -> T | U:
        return self.value if self.is_some() else default

    def __repr__(self) -> str:
        return f"Some({self.value})" if self.is_some() else "Nothing"


# Either (Left / Right)


@dataclass(frozen=True)
class Either(Generic[L, R]):
    """
    Either<L, R> — левая ветвь обычно представляет ошибку (is_left=True),
    правая — успешное значение (is_left=False).

    Фабрики: Either.left(val), Either.right(val)
    Методы: map, bind, get_or_else, is_left (атрибут), is_right (свойство)
    """

    is_left: bool
    value: Union[L, R]

    # factories
    @staticmethod
    def left(value: L) -> "Either[L, R]":
        return Either(True, value)

    @staticmethod
    def right(value: R) -> "Either[L, R]":
        return Either(False, value)

    # frozen init
    def __init__(self, is_left: bool, value: Union[L, R]):
        object.__setattr__(self, "is_left", is_left)
        object.__setattr__(self, "value", value)

    # compatibility helpers
    @property
    def is_right(self) -> bool:
        return not self.is_left

    # functor / monad-ish operations (operate on Right)
    def map(self, fn: Callable[[R], U]) -> "Either[L, U]":
        return Either.right(fn(self.value)) if not self.is_left else self  # type: ignore[return-value]

    def bind(self, fn: Callable[[R], "Either[L, U]"]) -> "Either[L, U]":
        return fn(self.value) if not self.is_left else self  # type: ignore[return-value]

    # extractor: returns Right value or default (when Left)
    def get_or_else(self, default: U) -> R | U:
        return self.value if not self.is_left else default  # type: ignore[return-value]

    def __repr__(self) -> str:
        return f"Left({self.value})" if self.is_left else f"Right({self.value})"
