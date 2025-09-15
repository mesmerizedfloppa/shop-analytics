from dataclasses import dataclass
from typing import Optional, Tuple, Dict


@dataclass(frozen=True)
class Category:
    id: str
    name: str
    parent_id: Optional[str] = None


@dataclass(frozen=True)
class Product:
    id: str
    title: str
    price: int  # копейки
    category_id: str
    tags: Tuple[str, ...]


@dataclass(frozen=True)
class User:
    id: str
    name: str
    tier: str  # "regular" | "vip"


@dataclass(frozen=True)
class Cart:
    id: str
    user_id: str
    items: Tuple[Tuple[str, int], ...]


@dataclass(frozen=True)
class Order:
    id: str
    user_id: str
    items: Tuple[Tuple[str, int], ...]
    total: int
    ts: str
    status: str


@dataclass(frozen=True)
class Payment:
    id: str
    order_id: str
    amount: int
    ts: str
    method: str


@dataclass(frozen=True)
class Event:
    id: str
    ts: str
    name: str
    payload: Dict


@dataclass(frozen=True)
class Discount:
    id: str
    code: str
    percent: int
    conditions: Dict
