"""RF-03 — Generación de SPEC (§6).

Documento técnico persistente y versionado con las 15 secciones de §6.2.
Todo lo que la SPEC afirma proviene de evidencia (enriquecimiento
validado + requerimientos); lo que no se sabe va a supuestos
pendientes, nunca se inventa. La aprobación es siempre humana (§6.3).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

UMBRAL_DIVISION = 15  # §6.4: más funcionalidades → recomendar dividir

QUALITY_GATES = ["clarification", "testing", "structural_validation"]


class SpecError(ValueError):
    """Condición de aceptación violada en la generación de SPEC."""


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Criterio:
    id: str
    texto: str
    req_id: str


@dataclass
class CasoPrueba:
    id: str
    texto: str
    criterio_id: str


@dataclass
class Spec:
    spec_id: str
    titulo: str
    version: str = "1.0.0"
    status: str = "draft"
    enr_origen: str | None = None
    contexto: str = ""
    problema: str = ""
    funcionales: list = field(default_factory=list)  # [(req_id, texto, estado)]
    no_funcionales: list = field(default_factory=list)  # [str]
    entidades: list = field(default_factory=list)  # [str]
    reglas: list = field(default_factory=list)  # [str]
    comportamientos: list = field(default_factory=list)  # [str]
    restricciones: list = field(default_factory=list)  # [str]
    dependencias: list = field(default_factory=list)  # [str]
    criterios: list = field(default_factory=list)  # [Criterio]
    casos: list = field(default_factory=list)  # [CasoPrueba]
    fuera_alcance: list = field(default_factory=list)  # [str]
    supuestos: list = field(default_factory=list)  # [str]
    referencias: list = field(default_factory=list)  # [str]
    created_at: str = field(default_factory=_ahora)
    updated_at: str = field(default_factory=_ahora)
    approved_at: str | None = None

    def recomienda_dividir(self) -> bool:
        """§6.4: advierte, nunca fragmenta automáticamente."""
        return len(self.funcionales) > UMBRAL_DIVISION

    def aprobar(self) -> None:
        """Solo un humano ejecuta este camino (§6.3)."""
        if self.status == "approved":
            raise SpecError(f"{self.spec_id} ya está aprobada")
        self.status = "approved"
        self.approved_at = _ahora()
        self.updated_at = self.approved_at

    def to_dict(self) -> dict:
        datos = asdict(self)
        return datos

    @classmethod
    def from_dict(cls, datos: dict) -> "Spec":
        try:
            return cls(
                spec_id=str(datos["spec_id"]),
                titulo=str(datos["titulo"]),
                version=str(datos.get("version", "1.0.0")),
                status=str(datos.get("status", "draft")),
                enr_origen=datos.get("enr_origen"),
                contexto=str(datos.get("contexto", "")),
                problema=str(datos.get("problema", "")),
                funcionales=list(datos.get("funcionales", [])),
                no_funcionales=list(datos.get("no_funcionales", [])),
                entidades=list(datos.get("entidades", [])),
                reglas=list(datos.get("reglas", [])),
                comportamientos=list(datos.get("comportamientos", [])),
                restricciones=list(datos.get("restricciones", [])),
                dependencias=list(datos.get("dependencias", [])),
                criterios=[Criterio(**c) for c in datos.get("criterios", [])],
                casos=[CasoPrueba(**c) for c in datos.get("casos", [])],
                fuera_alcance=list(datos.get("fuera_alcance", [])),
                supuestos=list(datos.get("supuestos", [])),
                referencias=list(datos.get("referencias", [])),
                created_at=str(datos.get("creado_en", datos.get("created_at", ""))),
                updated_at=str(datos.get("updated_at", "")),
                approved_at=datos.get("approved_at"),
            )
        except (KeyError, TypeError) as error:
            raise SpecError(f"registro de SPEC corrupto: {error}") from error


def _subir_version(version: str) -> str:
    partes = version.split(".")
    partes[-1] = str(int(partes[-1]) + 1)
    return ".".join(partes)


def generar_desde_enriquecimiento(
    enr, reqs: list, spec_id: str, titulo: str | None = None
) -> Spec:
    """Construye la SPEC solo con evidencia del ENR validado + sus REQ."""
    funcionales = [
        (r.id, r.texto, r.estado)
        for r in reqs
        if r.origen == enr.id and r.procedencia in ("explicito", "inferido", "sugerido")
    ]
    entidades = [i.texto for i in enr.por_seccion("entidad")]
    reglas = [i.texto for i in enr.por_seccion("regla")]
    restricciones = [i.texto for i in enr.por_seccion("restriccion")]
    exclusiones = [i.texto for i in enr.por_seccion("exclusion")]
    faltantes = [i.texto for i in enr.por_seccion("faltante")]

    no_funcionales = list(restricciones) or ["Sin definir (pendiente de clarify)"]
    dependencias = ["No declaradas (pendiente de plan)"]

    criterios = [
        Criterio(id=f"CRI-{n:03d}", texto=f"Verificar: {texto}", req_id=req_id)
        for n, (req_id, texto, _estado) in enumerate(funcionales, 1)
    ]
    casos = [
        CasoPrueba(
            id=f"CP-{n:03d}",
            texto=f"Ejecutar el flujo de {c.req_id} y comprobar: {c.texto[10:]}",
            criterio_id=c.id,
        )
        for n, c in enumerate(criterios, 1)
    ]

    titulo_final = titulo or " ".join(enr.objetivo.split()[:8])
    return Spec(
        spec_id=spec_id,
        titulo=titulo_final,
        enr_origen=enr.id,
        contexto=f"Dominio: {enr.dominio}. Idea original: «{enr.entrada}».",
        problema=f"Se necesita: {enr.objetivo}.",
        funcionales=funcionales,
        no_funcionales=no_funcionales,
        entidades=entidades,
        reglas=reglas or ["Sin reglas declaradas (pendiente de clarify)"],
        comportamientos=[f"El sistema debe: {texto}" for _, texto, _ in funcionales],
        restricciones=restricciones or ["Sin restricciones declaradas"],
        dependencias=dependencias,
        criterios=criterios,
        casos=casos,
        fuera_alcance=exclusiones or ["Sin exclusiones declaradas"],
        supuestos=faltantes or ["Sin supuestos pendientes"],
        referencias=[enr.id, *[r.id for r in reqs if r.origen == enr.id]],
    )


def render_markdown(spec: Spec) -> str:
    """Las 15 secciones de §6.2 con metadatos §6.3."""
    lineas = [
        "---",
        f"spec_id: {spec.spec_id}",
        f"spec_version: {spec.version}",
        f"status: {spec.status}",
        f'created_at: "{spec.created_at}"',
        f'updated_at: "{spec.updated_at}"',
        f"approved_at: {spec.approved_at or 'null'}",
        "quality_gates:",
        *[f"  - {g}" for g in QUALITY_GATES],
        "---",
        "",
        f"# {spec.spec_id} — {spec.titulo}",
        "",
        "## 1. Identificación y metadatos",
        f"Versión {spec.version}, estado {spec.status}, origen {spec.enr_origen or '—'}.",
        "",
        "## 2. Contexto y propósito",
        spec.contexto,
        "",
        "## 3. Problema que resuelve",
        spec.problema,
        "",
        "## 4. Requerimientos funcionales",
        *[
            f"- {req_id} ({estado}): {texto}"
            for req_id, texto, estado in spec.funcionales
        ],
        "",
        "## 5. Requerimientos no funcionales",
        *[f"- {r}" for r in spec.no_funcionales],
        "",
        "## 6. Entidades y modelos de datos",
        *[f"- {e}" for e in spec.entidades],
        "",
        "## 7. Reglas de negocio",
        *[f"- {r}" for r in spec.reglas],
        "",
        "## 8. Comportamientos esperados",
        *[f"- {c}" for c in spec.comportamientos],
        "",
        "## 9. Restricciones del entorno",
        *[f"- {r}" for r in spec.restricciones],
        "",
        "## 10. Dependencias conocidas",
        *[f"- {d}" for d in spec.dependencias],
        "",
        "## 11. Criterios de aceptación",
        *[f"- {c.id} ({c.req_id}): {c.texto}" for c in spec.criterios],
        "",
        "## 12. Casos de prueba",
        *[f"- {c.id} ({c.criterio_id}): {c.texto}" for c in spec.casos],
        "",
        "## 13. Fuera de alcance",
        *[f"- {e}" for e in spec.fuera_alcance],
        "",
        "## 14. Suposiciones pendientes",
        *[f"- {s}" for s in spec.supuestos],
        "",
        "## 15. Referencias y trazabilidad",
        *[f"- {r}" for r in spec.referencias],
        "",
    ]
    return "\n".join(lineas)
