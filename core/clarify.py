"""RF-04 — Clarificación interactiva (§7).

Detecta ambigüedades con evidencia (nunca inventa preguntas sobre lo ya
definido), las presenta contextualizadas y aplica cada respuesta humana
actualizando la SPEC y registrando qué cambió (§7.4).
"""

from __future__ import annotations

import unicodedata
from dataclasses import asdict, dataclass, field

RESPONDIDA = "respondida"
PENDIENTE = "pendiente"
OMITIDA = "omitida"

INDEFINIDAS = {
    "todavia no lo se",
    "no lo se",
    "ns/nc",
    "no se",
    "pendiente",
}


def normalizar(texto: str) -> str:
    sin_acentos = "".join(
        c for c in unicodedata.normalize("NFD", texto) if not unicodedata.combining(c)
    )
    return sin_acentos.lower()


def es_indefinida(respuesta: str) -> bool:
    return normalizar(respuesta).strip() in INDEFINIDAS


STOPWORDS = {
    "el", "la", "los", "las", "un", "una", "de", "del", "en", "y", "o", "que",
    "se", "con", "por", "para", "al", "su", "sus", "este", "esta", "debe",
    "deben", "sin", "no",
}


def raices(texto: str) -> set[str]:
    """Tokens significativos: minúsculas, sin acentos, sin stopwords,
    con plural recortado. La familia (registrar/registro) se resuelve
    en _emparentadas por prefijo común."""
    raices_ = set()
    for palabra in normalizar(texto).split():
        palabra = "".join(c for c in palabra if c.isalnum())
        if len(palabra) < 4 or palabra in STOPWORDS:
            continue
        for sufijo in ("es", "s"):
            if palabra.endswith(sufijo) and len(palabra) - len(sufijo) >= 4:
                palabra = palabra[: -len(sufijo)]
                break
        raices_.add(palabra)
    return raices_


def _emparentadas(a: str, b: str) -> bool:
    if a == b:
        return True
    if len(a) < 5 or len(b) < 5:
        return False
    if a.startswith(b) or b.startswith(a):
        return True
    prefijo = 0
    for x, y in zip(a, b):
        if x != y:
            break
        prefijo += 1
    return prefijo >= 6


class ClarifyError(ValueError):
    """Condición de aceptación violada en clarificación."""


@dataclass
class Pregunta:
    id: str
    kind: str  # contradiccion | supuesto | rnf | regla | dependencia | confirmar_req | entidad_datos
    texto: str
    contexto: str
    tipo: str = "libre"  # libre | opciones
    opciones: list = field(default_factory=list)
    ref: str = ""
    estado: str = PENDIENTE
    respuesta: str | None = None
    esencial: bool = False  # si es prioritaria para el modo esencial (3-7 preguntas)

    def clave(self) -> str:
        return f"{self.kind}::{self.ref}"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, datos: dict) -> "Pregunta":
        try:
            return cls(
                id=str(datos["id"]),
                kind=str(datos["kind"]),
                texto=str(datos["texto"]),
                contexto=str(datos.get("contexto", "")),
                tipo=str(datos.get("tipo", "libre")),
                opciones=list(datos.get("opciones", [])),
                ref=str(datos.get("ref", "")),
                estado=str(datos.get("estado", PENDIENTE)),
                respuesta=datos.get("respuesta"),
                esencial=bool(datos.get("esencial", False)),
            )
        except (KeyError, TypeError) as error:
            raise ClarifyError(f"pregunta corrupta: {error}") from error


def detectar(spec, reqs: list, existentes: list[Pregunta] | None = None) -> list[Pregunta]:
    """Genera preguntas solo sobre lo no definido. Nunca repite una ya hecha
    (§7.4): las existentes se conservan con su estado."""
    previas = {p.clave(): p for p in (existentes or [])}
    nuevas: list[Pregunta] = []

    def agregar(kind: str, ref: str, texto: str, contexto: str,
               tipo: str = "libre", opciones: list | None = None,
               esencial: bool = False) -> None:
        clave = f"{kind}::{ref}"
        if clave in previas:
            return
        nuevas.append(
            Pregunta(
                id="",  # se numera al consolidar
                kind=kind,
                texto=texto,
                contexto=contexto,
                tipo=tipo,
                opciones=opciones or [],
                ref=ref,
                esencial=esencial,
            )
        )

    # §7.2: reglas de negocio contradictorias (funcional vs exclusión).
    for req_id, ftexto, _estado in spec.funcionales:
        for excl in spec.fuera_alcance:
            toks_f, toks_e = raices(ftexto), raices(excl)
            compartidas = {
                a for a in toks_f for b in toks_e if _emparentadas(a, b)
            }
            if len(compartidas) >= 1 and len(toks_f & toks_e) + len(compartidas) >= 2:
                detalle = ", ".join(sorted(compartidas))
                agregar(
                    "contradiccion",
                    f"{req_id}::{excl}",
                    f"«{ftexto}» comparte tema ({detalle}) con algo fuera de alcance: «{excl}». ¿Está dentro o fuera?",
                    f"Posible contradicción entre {req_id} y §13 Fuera de alcance.",
                    tipo="opciones",
                    opciones=["Dentro del alcance", "Fuera del alcance", "Todavía no lo sé"],
                )

    # §7.2: supuestos pendientes (faltantes del ENR).
    for i, sup in enumerate(spec.supuestos):
        if sup.startswith("✓"):
            continue
        agregar("supuesto", sup, f"Pendiente de aclarar: {sup}",
                "§14 Suposiciones pendientes.",
                esencial=(i == 0))  # el primer supuesto es esencial

    # Placeholders sin definir (§7.2: decisiones técnicas / dependencias).
    if spec.no_funcionales == ["Sin definir (pendiente de clarify)"]:
        agregar("rnf", "rnf", "¿Hay algún requerimiento no funcional (rendimiento, seguridad, disponibilidad)?",
                "§5 sin definir.", esencial=True)
    if spec.reglas == ["Sin reglas declaradas (pendiente de clarify)"]:
        agregar("regla", "regla", "¿Hay alguna regla de negocio (precios, descuentos, permisos)?",
                "§7 sin definir.")
    if spec.dependencias == ["No declaradas (pendiente de plan)"]:
        agregar("dependencia", "dependencia", "¿El sistema depende de algo externo (hardware, servicio, planilla actual)?",
                "§10 sin definir.", esencial=True)

    # §7.2: requerimientos incompletos (pendientes de validación).
    for req_id, ftexto, estado in spec.funcionales:
        if estado != "aceptado":
            agregar(
                "confirmar_req",
                req_id,
                f"¿Se confirma este requerimiento? «{ftexto}»",
                f"{req_id} está en estado {estado}.",
                tipo="opciones",
                opciones=["Confirmar", "Descartar", "Todavía no lo sé"],
            )

    # §7.2: tipos de datos ambiguos (entidades sin atributos).
    for ent in spec.entidades:
        if "(" not in ent:
            agregar("entidad_datos", ent, f"¿Qué datos guarda «{ent}»?",
                    "§6 Entidades sin atributos definidos.")

    return nuevas


def consolidar(existentes: list[Pregunta], nuevas: list[Pregunta]) -> list[Pregunta]:
    """Une conservando estados; numera solo las realmente nuevas."""
    todas = list(existentes)
    usados = {p.id for p in todas}
    n = len(todas) + 1
    for p in nuevas:
        while f"CLA-{n:03d}" in usados:
            n += 1
        p.id = f"CLA-{n:03d}"
        usados.add(p.id)
        todas.append(p)
        n += 1
    return todas


def pendientes(preguntas: list[Pregunta]) -> list[Pregunta]:
    return [p for p in preguntas if p.estado == PENDIENTE]


def responder(pregunta: Pregunta, respuesta: str, spec, registro_req) -> str:
    """Aplica una respuesta humana: actualiza la SPEC y devuelve qué cambió
    (§7.4). Nunca inventa contenido: solo registra lo que el humano dijo."""
    if pregunta.estado != PENDIENTE:
        raise ClarifyError(f"{pregunta.id} ya fue contestada; no se repite (§7.4)")
    respuesta = respuesta.strip()
    if not respuesta:
        raise ClarifyError("respuesta vacía; use --skip para omitir explícitamente")
    if pregunta.tipo == "opciones" and respuesta.isdigit():
        indice = int(respuesta) - 1
        if 0 <= indice < len(pregunta.opciones):
            respuesta = pregunta.opciones[indice]
    pregunta.respuesta = respuesta
    pregunta.estado = RESPONDIDA

    kind, ref = pregunta.kind, pregunta.ref
    if es_indefinida(respuesta):
        return f"{pregunta.id}: sin definir por ahora; se conserva como pendiente de futuro"

    if kind == "supuesto":
        spec.supuestos = [s for s in spec.supuestos if s != ref]
        spec.supuestos.append(f"✓ Aclarado ({pregunta.id}): {ref} → {respuesta}")
        return f"{pregunta.id}: supuesto resuelto y movido a aclarados"

    if kind in ("rnf", "regla", "dependencia"):
        destino = {"rnf": "no_funcionales", "regla": "reglas",
                   "dependencia": "dependencias"}[kind]
        actual = getattr(spec, destino)
        if len(actual) == 1 and "pendiente" in actual[0]:
            setattr(spec, destino, [f"{respuesta} ({pregunta.id})"])
        else:
            actual.append(f"{respuesta} ({pregunta.id})")
        return f"{pregunta.id}: § actualizada con lo declarado por el humano"

    if kind == "entidad_datos":
        spec.entidades = [
            f"{e} (datos: {respuesta})" if e == ref else e for e in spec.entidades
        ]
        return f"{pregunta.id}: entidad «{ref}» ahora con atributos declarados"

    if kind == "confirmar_req":
        req = next((r for r in registro_req.listar() if r.id == ref), None)
        if respuesta == "Descartar":
            if req is not None:
                registro_req.cambiar_estado(req.id, "rechazado")
            spec.funcionales = [f for f in spec.funcionales if f[0] != ref]
            spec.criterios = [c for c in spec.criterios if c.req_id != ref]
            vivos = {c.id for c in spec.criterios}
            spec.casos = [c for c in spec.casos if c.criterio_id in vivos]
            return f"{pregunta.id}: {ref} descartado y excluido"
        if req is not None:
            registro_req.cambiar_estado(req.id, "aceptado")
        spec.funcionales = [
            (i, t, "aceptado") if i == ref else (i, t, e)
            for i, t, e in spec.funcionales
        ]
        return f"{pregunta.id}: {ref} confirmado como aceptado"

    if kind == "contradiccion":
        req_id, _, excl = ref.partition("::")
        if respuesta == "Dentro del alcance":
            spec.fuera_alcance = [e for e in spec.fuera_alcance if e != excl]
            return f"{pregunta.id}: «{excl}» sale de fuera de alcance; {req_id} prevalece"
        spec.funcionales = [f for f in spec.funcionales if f[0] != req_id]
        vivos = {c.id for c in spec.criterios if c.req_id != req_id}
        spec.criterios = [c for c in spec.criterios if c.req_id != req_id]
        spec.casos = [c for c in spec.casos if c.criterio_id in vivos]
        req = next((r for r in registro_req.listar() if r.id == req_id), None)
        if req is not None:
            registro_req.cambiar_estado(req.id, "rechazado")
        return f"{pregunta.id}: {req_id} excluido; prevalece fuera de alcance"

    return f"{pregunta.id}: respuesta registrada sin cambios estructurales"
