"""RF-07 — Análisis de consistencia (§10).

Cruza SPEC + plan + tareas solo con evidencia. Genera informe con
severidad y acción recomendada. Gate 4: las críticas bloquean, las
advertencias quedan registradas (§10.4).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from core.clarify import raices

CRITICA = "critica"
ADVERTENCIA = "advertencia"

# §8.4: tocarlos requiere autorización adicional explícita.
PROTEGIDOS = {
    ".specify", "specs", ".git", "pyproject.toml", "package.json",
    "requirements.txt", "go.mod", "Cargo.toml", "Gemfile",
}


class AnalyzeError(ValueError):
    """Condición de aceptación violada en el análisis."""


@dataclass
class Problema:
    id: str
    severidad: str  # critica | advertencia
    artefactos: list = field(default_factory=list)
    evidencia: str = ""
    explicacion: str = ""
    accion: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id, "severidad": self.severidad,
            "artefactos": self.artefactos, "evidencia": self.evidencia,
            "explicacion": self.explicacion, "accion": self.accion,
        }

    @classmethod
    def from_dict(cls, datos: dict) -> "Problema":
        try:
            return cls(
                id=str(datos["id"]), severidad=str(datos["severidad"]),
                artefactos=list(datos.get("artefactos", [])),
                evidencia=str(datos.get("evidencia", "")),
                explicacion=str(datos.get("explicacion", "")),
                accion=str(datos.get("accion", "")),
            )
        except (KeyError, TypeError) as error:
            raise AnalyzeError(f"problema corrupto: {error}") from error


def _es_protegido(ruta: str) -> bool:
    partes = set(Path(ruta).parts)
    return bool(partes & PROTEGIDOS)


def analizar(plan, spec, tareas: list, raiz_proyecto: Path) -> list[Problema]:
    """Aplica las 9 comprobaciones de §10.2. Sin evidencia no hay problema."""
    problemas: list[Problema] = []
    n = 0

    def agregar(severidad: str, artefactos: list, evidencia: str,
               explicacion: str, accion: str) -> None:
        nonlocal n
        n += 1
        problemas.append(Problema(
            id=f"INC-{n:03d}", severidad=severidad, artefactos=artefactos,
            evidencia=evidencia, explicacion=explicacion, accion=accion))

    refs_tareas = {r for t in tareas for r in t.refs}
    reqs_tareas = {r for r in refs_tareas if r.startswith("REQ-")}
    ids_tareas = {t.id for t in tareas}

    # 1. Requerimientos sin tareas.
    for req_id, texto, estado in spec.funcionales:
        if estado == "aceptado" and req_id not in reqs_tareas:
            agregar(CRITICA, [req_id, plan.plan_id],
                    f"{req_id} aceptado pero ninguna tarea lo cita en sus REFs",
                    "El requerimiento aceptado nunca se implementaría.",
                    f"Agregue una tarea para {req_id} o descarte el requerimiento con clarify.")

    # 2. Tareas sin requerimientos.
    for t in tareas:
        if not t.refs:
            agregar(CRITICA, [t.id],
                    f"{t.id} no tiene REFs a la SPEC",
                    "Trabajo sin trazabilidad: posible funcionalidad inventada (§8.6).",
                    "Vincule la tarea a la SPEC o elimínela.")
        elif not reqs_tareas_norm(t):
            agregar(ADVERTENCIA, [t.id],
                    f"{t.id} cita {t.refs} pero ningún REQ-XXX directo",
                    "Trazabilidad indirecta (sección SPEC, no requerimiento).",
                    "Si la tarea implementa un REQ, cite su ID; si no, justifíquelo.")

    # 3. Criterios de aceptación sin pruebas reales.
    for t in tareas:
        if any("crear con la implementación" in p for p in t.pruebas):
            agregar(ADVERTENCIA, [t.id],
                    f"{t.id} prevé pruebas que aún no existen",
                    "El criterio existe pero su prueba se creará después, no antes.",
                    "Al implementar, escriba la prueba primero si es posible.")

    # 4. Dependencias incompatibles (apuntan fuera de la cadena o hacia adelante).
    orden = {t.id: i for i, t in enumerate(tareas)}
    for t in tareas:
        for dep in t.dependencias:
            if dep not in ids_tareas:
                agregar(CRITICA, [t.id],
                        f"{t.id} depende de {dep}, que no existe",
                        "La tarea nunca podría ejecutarse (§9.4).",
                        "Corrija la dependencia a una tarea existente.")
            elif orden[dep] >= orden[t.id]:
                agregar(CRITICA, [t.id],
                        f"{t.id} depende de {dep}, posterior en el orden",
                        "Dependencia hacia adelante: imposible de satisfacer.",
                        "Reordene las tareas o invierta la dependencia.")

    # 5. Modificaciones fuera de alcance.
    for ruta in plan.modificables:
        for excl in spec.fuera_alcance:
            limpia = ruta.replace("/", " ").replace(".", " ").replace("_", " ")
            toks_m, toks_e = raices(limpia), raices(excl)
            compartidas = {a for a in toks_m for b in toks_e
                           if a == b and len(a) >= 4}
            if len(compartidas) >= 2:
                agregar(CRITICA, [ruta],
                        f"«{ruta}» comparte tema ({', '.join(sorted(compartidas))}) con exclusión «{excl}»",
                        "El plan tocaría algo declarado fuera de alcance (§6.5).",
                        "Saque el archivo del plan o revise el alcance con clarify.")

    # 6. Archivos protegidos involucrados.
    for t in tareas:
        for ruta in t.archivos:
            if _es_protegido(ruta):
                agregar(CRITICA, [t.id, ruta],
                        f"{t.id} modifica {ruta}, archivo protegido",
                        "Requiere autorización adicional (§8.4); el build no debe tocarlo solo.",
                        "Confirme la autorización humana o cambie el archivo objetivo.")

    # 7. Conflictos con arquitectura existente.
    intactos = set(plan.intactos)
    for ruta in plan.modificables:
        if ruta in intactos or ruta in set(plan.reutilizables):
            agregar(CRITICA, [ruta],
                    f"«{ruta}» es modificable e intacto/reutilizable a la vez",
                    "El plan se contradice sobre este componente.",
                    "Decida un rol único para el archivo y regenere el plan.")

    # 8. Cambios de interfaz pública.
    raiz = Path(raiz_proyecto)
    codigo = [r for r in plan.hallazgos.get("codigo", [])]
    for ruta in plan.modificables:
        if not ruta.endswith(".py"):
            continue
        modulo = Path(ruta).stem
        if len(modulo) < 3:
            continue
        importadores = []
        for otro in codigo:
            if otro == ruta:
                continue
            try:
                texto = (raiz / otro).read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if f"import {modulo}" in texto or f"from {modulo}" in texto:
                importadores.append(otro)
        if importadores:
            agregar(ADVERTENCIA, [ruta, *importadores],
                    f"«{ruta}» es importado por {', '.join(importadores)}",
                    "Modificarlo puede cambiar una interfaz pública usada por otros módulos.",
                    "Conserve firmas y comportamiento público; agregue prueba de regresión.")

    # 9. Riesgos de regresión (desde los riesgos del plan).
    for riesgo in plan.riesgos:
        if riesgo.startswith("Sin riesgos"):
            continue
        agregar(ADVERTENCIA, [plan.plan_id],
                f"Riesgo del plan: {riesgo}",
                "Condición que puede romper lo existente al implementar.",
                "Mitigue el riesgo antes o durante la primera tarea afectada.")

    return problemas


def reqs_tareas_norm(t) -> list[str]:
    return [r for r in t.refs if r.startswith("REQ-")]


def render_markdown(problemas: list[Problema], plan_id: str, spec_id: str) -> str:
    criticas = sum(1 for p in problemas if p.severidad == CRITICA)
    lineas = [
        "---",
        f"plan: {plan_id}",
        f"spec: {spec_id}",
        f"problemas: {len(problemas)} (criticas: {criticas})",
        "---",
        "",
        f"# Informe de consistencia — {plan_id} ({spec_id})",
        "",
        ("Sin inconsistencias detectadas con la evidencia disponible."
         if not problemas else
         f"Hallazgos: {len(problemas)} ({criticas} crítica(s))."),
        "",
    ]
    for p in problemas:
        marca = "🔴" if p.severidad == CRITICA else "🟡"
        lineas += [
            f"## {p.id} {marca} {p.severidad.upper()}",
            "",
            f"Artefactos: {', '.join(p.artefactos)}.",
            "",
            f"Evidencia: {p.evidencia}",
            "",
            f"Explicación: {p.explicacion}",
            "",
            f"Acción recomendada: {p.accion}",
            "",
        ]
    return "\n".join(lineas)
