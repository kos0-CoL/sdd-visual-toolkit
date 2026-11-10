"""Entidades de §6: productos, ventas y caja."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Producto:
    nombre: str
    precio: float
    stock: int = 0


@dataclass
class LineaVenta:
    producto: Producto
    cantidad: int


@dataclass
class Venta:
    lineas: list[LineaVenta] = field(default_factory=list)

    def total(self) -> float:
        raise NotImplementedError("pendiente de implementar")


@dataclass
class Movimiento:
    producto: Producto
    delta: int


class Caja:
    def __init__(self) -> None:
        self.saldo = 0.0

    def cobrar(self, venta: Venta) -> float:
        raise NotImplementedError("pendiente de implementar")
