"""RF-02 — Enriquecimiento inicial (§5).

Transforma una idea breve en una descripción estructurada: objetivo,
entidades, funcionalidades, inferencias, faltante y fuera de alcance.
Cada elemento lleva su procedencia (§5.3) y su cita textual (§39).

Motor determinístico v0.1 (sin modelo externo): heurísticas explícitas
sobre el texto + base de conocimiento por dominio. Todo lo inferido
nace pendiente de validación humana (§5.5); nada se aprueba solo.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

from core.requirements import (
    ACEPTADO,
    DESCONOCIDO,
    EXCLUIDO,
    EXPLICITO,
    INFERIDO,
    PENDIENTE,
    SUGERIDO,
)

PENDIENTE_VALIDACION = "pendiente_validacion"
VALIDADO = "validado"


class EnriquecimientoError(ValueError):
    """Condición de aceptación violada en el enriquecimiento."""


# --- Base de conocimiento por dominio (v0.1, explícita y ampliable) --------

DOMINIOS = {
    "comercio": {
        "claves": (
            "kiosco", "kiosko", "tienda", "almacén", "almacen", "comercio",
            "inventario", "stock", "ventas", "mostrador", "verdulería",
        ),
        "entidades": ("Productos", "Inventario", "Ventas", "Movimientos de stock", "Caja"),
        "funcionalidades": (
            "Visualización de productos",
            "Consulta de existencias",
            "Registro de ventas",
            "Actualización de inventario",
            "Búsqueda de productos",
        ),
        "mejoras": (
            "Alertas de stock mínimo",
            "Lectura de códigos de barras",
            "Cierre de caja",
            "Reportes de ventas",
        ),
        "exclusiones": (
            "Gestión de franquicias",
            "Múltiples sucursales",
            "Integración con pasarelas de pago",
            "Sistemas de crédito para clientes",
        ),
    },
    "turnos": {
        "claves": ("turno", "reserva", "cita", "agenda", "consultorio", "paciente"),
        "entidades": ("Clientes", "Turnos", "Agenda", "Profesionales"),
        "funcionalidades": (
            "Reserva de turnos",
            "Cancelación de turnos",
            "Consulta de agenda",
            "Registro de clientes",
        ),
        "mejoras": ("Recordatorios de turnos", "Lista de espera"),
        "exclusiones": ("Facturación electrónica", "Múltiples sedes"),
    },
}

STACKS_CONOCIDOS = (
    "python", "java", "php", "node", "javascript", "typescript", "react",
    "angular", "vue", "django", "flask", "laravel", "postgres", "mysql",
    "sqlite", "excel", "access",
)

_M_EXPLICITO = re.compile(
    r"\b(debe|deben|tiene que|tienen que|necesito|necesita|necesitan|"
    r"quiero|permite|permitir|registra|registrar|muestra|mostrar|"
    r"genera|generar|gestiona|gestionar|controla|controlar|"
    r"consulta|consultar|busca|buscar)\b",
    re.IGNORECASE,
)
_M_SUGERIDO = re.compile(
    r"\b(quizás|quizas|tal vez|podría|podria|sería bueno|seria bueno|"
    r"opcional|si es posible|estaría bueno|estaria bueno)\b",
    re.IGNORECASE,
)
_M_EXCLUSION = re.compile(
    r"\b(no quiero|no necesito|no incluye|no incluir|fuera del alcance|"
    r"excepto|excluyendo)\b",
    re.IGNORECASE,
)
_M_SIN_CONEXION = re.compile(r"\bsin\s+(internet|conexi[oó]n)\b", re.IGNORECASE)
_M_OBJETIVO = re.compile(
    r"^\s*(quiero|necesito|necesitamos|queremos)\s+(que\s+)?", re.IGNORECASE
)
_M_ACTORES = re.compile(
    r"\b(usuario|cliente|vendedor|emplead|admin|encargad|dueñ|dueño)\w*\b",
    re.IGNORECASE,
)
_M_PERSISTENCIA = re.compile(
    r"\b(archivo|base de datos|excel|planilla|papel|cuaderno|sistema actual)\b",
    re.IGNORECASE,
)
_M_REGLA = re.compile(
    r"\b(solo|solamente|[uú]nicamente|siempre que|descuento|impuesto|iva|"
    r"cuando .* entonces)\b",
    re.IGNORECASE,
)


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class ItemEnriquecido:
    item_id: str
    seccion: str  # objetivo|entidad|funcionalidad|mejora|faltante|exclusion|regla|restriccion
    texto: str
    procedencia: str
    cita: str = ""


@dataclass
class Enriquecimiento:
    id: str
    entrada: str  # cita textual íntegra de la idea original
    objetivo: str
    dominio: str
    items: list[ItemEnriquecido] = field(default_factory=list)
    estado: str = PENDIENTE_VALIDACION
    creado_en: str = field(default_factory=_ahora)
    validado_en: str | None = None

    def por_seccion(self, seccion: str) -> list[ItemEnriquecido]:
        return [i for i in self.items if i.seccion == seccion]

    def quitar(self, item_ids: list[str]) -> list[ItemEnriquecido]:
        """El usuario poda elementos antes de validar (§5.5)."""
        if self.estado == VALIDADO:
            raise EnriquecimientoError(f"{self.id} ya fue validado; no se puede podar")
        pedidos = set(item_ids)
        conocidos = {i.item_id for i in self.items}
        desconocidos = pedidos - conocidos
        if desconocidos:
            raise EnriquecimientoError(
                f"elementos inexistentes en {self.id}: {', '.join(sorted(desconocidos))}"
            )
        quitados = [i for i in self.items if i.item_id in pedidos]
        self.items = [i for i in self.items if i.item_id not in pedidos]
        return quitados

    def validar(self, registro_req) -> list:
        """Validación humana (§5.5): lo explícito nace aceptado, el resto
        nace pendiente para revisión. Registra el origen para trazabilidad."""
        from core.requirements import RegistroRequerimientos  # noqa: PLC0415

        if self.estado == VALIDADO:
            raise EnriquecimientoError(f"{self.id} ya fue validado")
        if not isinstance(registro_req, RegistroRequerimientos):
            raise EnriquecimientoError("se requiere el registro de requerimientos")
        creados = []
        for item in self.items:
            if item.seccion == "objetivo":
                continue  # el objetivo vive en la SPEC, no es un REQ
            procedencia = item.procedencia
            req = registro_req.agregar(f"[{self.id}/{item.item_id}] {item.texto}", procedencia)
            req.origen = self.id
            if procedencia == EXPLICITO:
                registro_req.cambiar_estado(req.id, ACEPTADO)
            creados.append(req)
        self.estado = VALIDADO
        self.validado_en = _ahora()
        return creados

    def to_dict(self) -> dict:
        datos = asdict(self)
        return datos

    @classmethod
    def from_dict(cls, datos: dict) -> "Enriquecimiento":
        try:
            items = [ItemEnriquecido(**i) for i in datos.get("items", [])]
            return cls(
                id=str(datos["id"]),
                entrada=str(datos["entrada"]),
                objetivo=str(datos["objetivo"]),
                dominio=str(datos.get("dominio", "general")),
                items=items,
                estado=str(datos.get("estado", PENDIENTE_VALIDACION)),
                creado_en=str(datos.get("creado_en", "")),
                validado_en=datos.get("validado_en"),
            )
        except (KeyError, TypeError) as error:
            raise EnriquecimientoError(
                f"registro de enriquecimiento corrupto: {error}"
            ) from error


def _detectar_dominio(texto: str) -> str:
    bajo = texto.lower()
    for dominio, info in DOMINIOS.items():
        if any(clave in bajo for clave in info["claves"]):
            return dominio
    return "general"


def _oraciones(texto: str) -> list[str]:
    partes = re.split(r"[.\n;]+", texto)
    return [p.strip(" \t") for p in partes if p.strip(" \t")]


def analizar(texto: str, enr_id: str = "ENR-000") -> Enriquecimiento:
    """Aplica §5.2 + §5.3 + §5.6 sobre la idea del usuario."""
    if not texto or not texto.strip():
        raise EnriquecimientoError("la idea inicial no puede estar vacía")
    original = " ".join(texto.split())
    oraciones = _oraciones(original)
    if not oraciones:
        raise EnriquecimientoError("la idea inicial no puede estar vacía")

    dominio = _detectar_dominio(original)
    objetivo = _M_OBJETIVO.sub("", oraciones[0]).strip().capitalize()

    items: list[ItemEnriquecido] = []
    contadores: dict[str, int] = {}

    def _agregar(seccion: str, texto_item: str, procedencia: str, cita: str = "") -> None:
        contadores[seccion] = contadores.get(seccion, 0) + 1
        prefijo = {
            "objetivo": "OBJ", "entidad": "ENT", "funcionalidad": "FUN",
            "mejora": "MEJ", "faltante": "FAL", "exclusion": "EXC",
            "regla": "REG", "restriccion": "RES",
        }[seccion]
        items.append(
            ItemEnriquecido(
                item_id=f"{prefijo}-{contadores[seccion]}",
                seccion=seccion,
                texto=texto_item.strip().capitalize(),
                procedencia=procedencia,
                cita=cita,
            )
        )

    _agregar("objetivo", objetivo, EXPLICITO, cita=oraciones[0])

    # Funcionalidades / exclusiones / sugerencias dichas por el usuario.
    for oracion in oraciones[1:]:
        if "?" in oracion:
            _agregar("faltante", oracion, DESCONOCIDO, cita=oracion)
        elif _M_EXCLUSION.search(oracion):
            _agregar("exclusion", oracion, EXCLUIDO, cita=oracion)
        elif _M_SUGERIDO.search(oracion):
            _agregar("mejora", oracion, SUGERIDO, cita=oracion)
        elif _M_EXPLICITO.search(oracion):
            _agregar("funcionalidad", oracion, EXPLICITO, cita=oracion)
        if _M_REGLA.search(oracion):
            _agregar("regla", oracion, INFERIDO, cita=oracion)

    # Conocimiento del dominio: entidades y base funcional (inferido),
    # mejoras típicas (sugerido) y exclusiones habituales (excluido).
    if dominio in DOMINIOS:
        info = DOMINIOS[dominio]
        for entidad in info["entidades"]:
            _agregar("entidad", entidad, INFERIDO)
        for func in info["funcionalidades"]:
            _agregar("funcionalidad", func, INFERIDO)
        for mejora in info["mejoras"]:
            _agregar("mejora", mejora, SUGERIDO)
        for exc in info["exclusiones"]:
            _agregar("exclusion", exc, EXCLUIDO)

    # Stack: respetar el conocido, nunca inventarlo (§5.6).
    stacks = sorted({s for s in STACKS_CONOCIDOS if s in original.lower()})
    if stacks:
        _agregar(
            "restriccion",
            f"Stack declarado: {', '.join(stacks)}",
            EXPLICITO,
            cita=original,
        )
    else:
        _agregar(
            "faltante",
            "Stack tecnológico sin definir (pendiente de aclaración)",
            DESCONOCIDO,
        )

    # Información típicamente faltante.
    if not _M_ACTORES.search(original):
        _agregar("faltante", "¿Quiénes usarán el sistema? (roles y permisos)", DESCONOCIDO)
    if dominio != "general" and not _M_PERSISTENCIA.search(original):
        _agregar(
            "faltante",
            "¿Dónde se guardan los datos hoy? (archivo, planilla, base de datos)",
            DESCONOCIDO,
        )
    if _M_SIN_CONEXION.search(original):
        _agregar("restriccion", "Debe funcionar sin internet", EXPLICITO, cita=original)

    return Enriquecimiento(
        id=enr_id, entrada=original, objetivo=objetivo, dominio=dominio, items=items
    )


class RegistroEnriquecimientos:
    def __init__(self, items: list[Enriquecimiento] | None = None) -> None:
        self._items: list[Enriquecimiento] = list(items or [])

    def siguiente_id(self) -> str:
        """El mayor de los existentes + 1: borrar uno del medio no repite IDs."""
        numeros = [int(enr.id.split("-")[-1]) for enr in self._items
                   if enr.id.split("-")[-1].isdigit()]
        return f"ENR-{max(numeros, default=0) + 1:03d}"

    def agregar(self, texto: str) -> Enriquecimiento:
        enr = analizar(texto, self.siguiente_id())
        self._items.append(enr)
        return enr

    def obtener(self, enr_id: str) -> Enriquecimiento:
        for enr in self._items:
            if enr.id == enr_id:
                return enr
        raise EnriquecimientoError(f"enriquecimiento inexistente: {enr_id}")

    def listar(self) -> list[Enriquecimiento]:
        return list(self._items)

    def quitar(self, enr_id: str) -> Enriquecimiento:
        """Saca un enriquecimiento que quedó sin elementos al podarlo."""
        enr = self.obtener(enr_id)
        self._items = [e for e in self._items if e.id != enr_id]
        return enr

    def to_list(self) -> list[dict]:
        return [e.to_dict() for e in self._items]

    @classmethod
    def from_list(cls, datos: list) -> "RegistroEnriquecimientos":
        if not isinstance(datos, list):
            raise EnriquecimientoError("el archivo de enriquecimientos está corrupto")
        return cls([Enriquecimiento.from_dict(d) for d in datos])
