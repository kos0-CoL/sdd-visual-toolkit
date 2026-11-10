"""RF-01 — Gestión de requerimientos (§5.3, §44.1).

Un requerimiento es un elemento individual de lo que el usuario pide,
con su procedencia declarada. Las inferencias nunca se convierten
automáticamente en requerimientos aprobados: todo nace `pendiente`
y solo el humano lo acepta o rechaza.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

# §5.3 — clasificación de información.
EXPLICITO = "explicito"
INFERIDO = "inferido"
SUGERIDO = "sugerido"
DESCONOCIDO = "desconocido"
EXCLUIDO = "excluido"
PROCEDENCIAS = (EXPLICITO, INFERIDO, SUGERIDO, DESCONOCIDO, EXCLUIDO)

PENDIENTE = "pendiente"
ACEPTADO = "aceptado"
RECHAZADO = "rechazado"
ESTADOS = (PENDIENTE, ACEPTADO, RECHAZADO)


class RequerimientoError(ValueError):
    """Condición de aceptación violada en la gestión de requerimientos."""


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Requerimiento:
    id: str
    texto: str
    procedencia: str
    estado: str = PENDIENTE
    creado_en: str = field(default_factory=_ahora)
    actualizado_en: str = field(default_factory=_ahora)
    spec_id: str | None = None
    origen: str | None = None  # trazabilidad §39 (p. ej. ENR-001)

    def __post_init__(self) -> None:
        if not self.texto or not self.texto.strip():
            raise RequerimientoError("el texto del requerimiento no puede estar vacío")
        if self.procedencia not in PROCEDENCIAS:
            raise RequerimientoError(
                f"procedencia inválida {self.procedencia!r}; "
                f"valores: {', '.join(PROCEDENCIAS)}"
            )
        if self.estado not in ESTADOS:
            raise RequerimientoError(
                f"estado inválido {self.estado!r}; valores: {', '.join(ESTADOS)}"
            )
        self.texto = self.texto.strip()

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, datos: dict) -> "Requerimiento":
        try:
            return cls(
                id=str(datos["id"]),
                texto=str(datos["texto"]),
                procedencia=str(datos["procedencia"]),
                estado=str(datos.get("estado", PENDIENTE)),
                creado_en=str(datos.get("creado_en", "")),
                actualizado_en=str(datos.get("actualizado_en", "")),
                spec_id=datos.get("spec_id"),
                origen=datos.get("origen"),
            )
        except KeyError as error:
            raise RequerimientoError(f"registro de requerimiento incompleto: {error}") from error


class RegistroRequerimientos:
    """Colección en memoria con reglas de negocio de RF-01."""

    def __init__(self, items: list[Requerimiento] | None = None) -> None:
        self._items: list[Requerimiento] = list(items or [])

    def siguiente_id(self) -> str:
        return f"REQ-{len(self._items) + 1:03d}"

    def agregar(self, texto: str, procedencia: str) -> Requerimiento:
        req = Requerimiento(id=self.siguiente_id(), texto=texto, procedencia=procedencia)
        self._items.append(req)
        return req

    def obtener(self, req_id: str) -> Requerimiento:
        for req in self._items:
            if req.id == req_id:
                return req
        raise RequerimientoError(f"requerimiento inexistente: {req_id}")

    def listar(
        self,
        procedencia: str | None = None,
        estado: str | None = None,
    ) -> list[Requerimiento]:
        resultado = self._items
        if procedencia is not None:
            if procedencia not in PROCEDENCIAS:
                raise RequerimientoError(f"procedencia inválida: {procedencia}")
            resultado = [r for r in resultado if r.procedencia == procedencia]
        if estado is not None:
            if estado not in ESTADOS:
                raise RequerimientoError(f"estado inválido: {estado}")
            resultado = [r for r in resultado if r.estado == estado]
        return list(resultado)

    def cambiar_estado(self, req_id: str, estado: str) -> Requerimiento:
        if estado not in ESTADOS:
            raise RequerimientoError(f"estado inválido: {estado}")
        req = self.obtener(req_id)
        # §5.3: lo excluido no pertenece al alcance; no puede aceptarse
        # sin antes corregir su procedencia.
        if estado == ACEPTADO and req.procedencia == EXCLUIDO:
            raise RequerimientoError(
                f"{req_id} está marcado como excluido del alcance; "
                "cambie su procedencia antes de aceptarlo"
            )
        req.estado = estado
        req.actualizado_en = _ahora()
        return req

    def to_list(self) -> list[dict]:
        return [r.to_dict() for r in self._items]

    @classmethod
    def from_list(cls, datos: list) -> "RegistroRequerimientos":
        if not isinstance(datos, list):
            raise RequerimientoError("el archivo de requerimientos está corrupto")
        return cls([Requerimiento.from_dict(d) for d in datos])
