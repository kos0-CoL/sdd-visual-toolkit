"""RF-06 — Desglose en tareas (§9).

Unidades pequeñas, secuenciales y comprobables derivadas del plan.
Cada tarea cita su SPEC, sus archivos, sus pruebas y sus dependencias;
sin plan validado no hay tareas (§26).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

PENDIENTE = "pendiente"


class TasksError(ValueError):
    """Condición de aceptación violada en el desglose."""


@dataclass
class Tarea:
    id: str
    descripcion: str
    objetivo: str
    archivos: list = field(default_factory=list)
    dependencias: list = field(default_factory=list)  # TASK-IDs previos
    precondiciones: list = field(default_factory=list)
    resultado: str = ""
    criterio: str = ""
    pruebas: list = field(default_factory=list)
    estado: str = PENDIENTE
    intentos: int = 0
    refs: list = field(default_factory=list)  # REQ-IDs / § SPEC

    def to_dict(self) -> dict:
        return {
            "id": self.id, "descripcion": self.descripcion, "objetivo": self.objetivo,
            "archivos": self.archivos, "dependencias": self.dependencias,
            "precondiciones": self.precondiciones, "resultado": self.resultado,
            "criterio": self.criterio, "pruebas": self.pruebas,
            "estado": self.estado, "intentos": self.intentos, "refs": self.refs,
        }

    @classmethod
    def from_dict(cls, datos: dict) -> "Tarea":
        try:
            return cls(
                id=str(datos["id"]),
                descripcion=str(datos.get("descripcion", "")),
                objetivo=str(datos["objetivo"]),
                archivos=list(datos.get("archivos", [])),
                dependencias=list(datos.get("dependencias", [])),
                precondiciones=list(datos.get("precondiciones", [])),
                resultado=str(datos.get("resultado", "")),
                criterio=str(datos.get("criterio", "")),
                pruebas=list(datos.get("pruebas", [])),
                estado=str(datos.get("estado", PENDIENTE)),
                intentos=int(datos.get("intentos", 0)),
                refs=list(datos.get("refs", [])),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise TasksError(f"tarea corrupta: {error}") from error


def _slug(texto: str) -> str:
    base = "".join(c if c.isalnum() else " " for c in texto.lower()).split()
    return "_".join(base[:4]) or "modulo"


def _archivos_para(paso_refs: list, plan) -> list[str]:
    """Propuesta determinista de archivos (Gate 3 exige identificarlos).
    Se marca como propuesta: el humano la confirma al implementar."""
    archivos: list[str] = []
    for ruta in plan.modificables:
        if not ruta.startswith("(") and ruta not in archivos:
            archivos.append(ruta)
    if not archivos:
        semilla = paso_refs[0] if paso_refs else "general"
        nombre = _slug(semilla.replace("§6:", "").replace("§", "sec"))
        archivos = [f"src/{nombre}.py", f"tests/test_{nombre}.py"]
    elif not any(a.startswith("tests/") or "test" in a for a in archivos):
        archivos = archivos + [f"tests/test_{_slug(paso_refs[0] if paso_refs else 'g')}.py"]
    return archivos


def generar_desde_plan(plan, spec, inicio: int = 1) -> list["Tarea"]:
    """Un plan-paso → una tarea (el paso ya es atómico por derivación §8.5).
    Cadena secuencial: cada tarea depende de la anterior (§9.4)."""
    casos_por_req: dict[str, list] = {}
    for caso in spec.casos:
        cri = next((c for c in spec.criterios if c.id == caso.criterio_id), None)
        if cri is not None:
            casos_por_req.setdefault(cri.req_id, []).append(caso.id)
    criterios_por_req = {c.req_id: c for c in spec.criterios}

    tareas: list[Tarea] = []
    n = inicio
    for paso in plan.orden:
        tid = f"TASK-{n:03d}"
        req_refs = [r for r in paso.refs if r.startswith("REQ-")]
        criterios = [criterios_por_req[r] for r in req_refs if r in criterios_por_req]
        pruebas = [cp for r in req_refs for cp in casos_por_req.get(r, [])]
        criterio_txt = "; ".join(f"{c.id}: {c.texto}" for c in criterios) or (
            f"Criterio de {paso.refs[0]}: completar «{paso.titulo}» "
            "según su sección SPEC"
        )
        if not pruebas:
            pruebas = [f"CP-{tid} (crear con la implementación)"]
        tareas.append(Tarea(
            id=tid,
            descripcion=paso.titulo,
            objetivo=f"{paso.titulo}. {paso.detalle}".strip(),
            archivos=_archivos_para(paso.refs, plan),
            dependencias=[tareas[-1].id] if tareas else [],
            precondiciones=(
                [f"{tareas[-1].id} completada y verificada"] if tareas
                else [f"{plan.plan_id} validado (Quality Gate 2)"]
            ),
            resultado=f"«{paso.titulo}» funcionando y verificado según su criterio.",
            criterio=criterio_txt,
            pruebas=pruebas,
            refs=list(paso.refs),
        ))
        n += 1
    return tareas


def verificar_gate3(tareas: list[Tarea]) -> list[str]:
    """Problemas de Quality Gate 3 (§9.5). Vacío = superado."""
    problemas: list[str] = []
    ids = {t.id for t in tareas}
    for t in tareas:
        if not t.refs:
            problemas.append(f"{t.id} sin relación con la SPEC")
        if not t.criterio.strip():
            problemas.append(f"{t.id} sin criterio de aceptación")
        if not t.archivos:
            problemas.append(f"{t.id} sin archivos objetivo")
        if not t.pruebas:
            problemas.append(f"{t.id} sin pruebas previstas")
        for dep in t.dependencias:
            if dep not in ids:
                problemas.append(f"{t.id} depende de {dep}, que no existe")
    # Ciclos en la cadena de dependencias.
    visitadas: set[str] = set()
    def _alcanza(origen: str, destino: str, vistas: set[str]) -> bool:
        if origen == destino:
            return True
        t = next((x for x in tareas if x.id == origen), None)
        if t is None or origen in vistas:
            return False
        return any(_alcanza(d, destino, vistas | {origen}) for d in t.dependencias)
    for t in tareas:
        for dep in t.dependencias:
            if _alcanza(dep, t.id, set()):
                problemas.append(f"ciclo de dependencias: {t.id} ↔ {dep}")
    return sorted(set(problemas))


def render_markdown(tareas: list[Tarea], plan_id: str, spec_id: str) -> str:
    lineas = [
        "---",
        f"plan: {plan_id}",
        f"spec: {spec_id}",
        f"tareas: {len(tareas)}",
        "---",
        "",
        f"# Tareas de {plan_id} ({spec_id})",
        "",
    ]
    for t in tareas:
        lineas += [
            f"## {t.id} — {t.descripcion}",
            "",
            f"Objetivo: {t.objetivo}",
            "",
            f"Archivos (propuestos): {', '.join(t.archivos)}",
            "",
            f"Dependencias: {', '.join(t.dependencias) or 'ninguna (primera tarea)'}.",
            "",
            f"Precondiciones: {'; '.join(t.precondiciones)}.",
            "",
            f"Resultado esperado: {t.resultado}",
            "",
            f"Criterio de aceptación: {t.criterio}",
            "",
            f"Pruebas asociadas: {', '.join(t.pruebas)}.",
            "",
            f"Estado: {t.estado} | Intentos: {t.intentos} | REFs: {', '.join(t.refs)}.",
            "",
        ]
    return "\n".join(lineas)
