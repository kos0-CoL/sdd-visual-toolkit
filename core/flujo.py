"""El flujo SDD como datos para la capa visual (§29).

Cada fase del árbol de estados se presenta con lo que el panel necesita ver:
su estado real, el artefacto que deja y la skill del agente que la ejecuta.
Si el artefacto no existe o la fase no tiene skill, se declara `None` y el
IDE muestra «—»: nada se inventa.
"""

from __future__ import annotations

from pathlib import Path

# fase → (skill, plantilla del artefacto). `{spec}` y `{plan}` se rellenan con
# los identificadores reales del proyecto; sin ellos la plantilla no casa y el
# artefacto queda declarado como inexistente.
FASES = (
    ("Enriquecimiento", "sdd-enrich", ".specify/requerimientos.json"),
    ("Especificación", "sdd-specify", "specs/{spec}.md"),
    ("Aclaraciones", "sdd-clarify", ".specify/clarifications.json"),
    ("Arquitectura", "sdd-plan", "planes/{plan}.md"),
    ("Tareas", "sdd-tasks", "tareas/{plan}.md"),
    ("Análisis", "sdd-analyze", "informes/{plan}.md"),
    ("Implementación", "sdd-build", ".specify/memory/current_task.json"),
    ("Pruebas", "sdd-test", ".specify/execution_history.jsonl"),
    ("Recuperación", None, ".specify/checkpoints"),
)

DATOS = {fase: (skill, plantilla) for fase, skill, plantilla in FASES}


def _comandos(spec: str, plan: str, tarea: str) -> dict[str, str | None]:
    """El comando con el que se avanza cada fase; `None` si falta el dato.

    `enrich` y `rollback` piden texto que el panel no puede escribir, así que
    se dejan sin comando en vez de ofrecer uno que fallaría.
    """
    return {
        "Enriquecimiento": None,
        "Especificación": f"specify --show {spec}" if spec else None,
        "Aclaraciones": f"clarify {spec}" if spec else None,
        "Arquitectura": f"plan {spec}" if spec else None,
        "Tareas": f"tasks {plan}" if plan else None,
        "Análisis": f"analyze {plan}" if plan else None,
        "Implementación": f"build {plan}" if plan else None,
        "Pruebas": f"test {tarea}" if tarea else None,
        "Recuperación": None,
    }


def flujo(raiz, nodos, estado: dict) -> list[dict]:
    """Una fila por fase, en el orden del árbol (§21)."""
    raiz = Path(raiz)
    spec = str(estado.get("spec_id") or "")
    plan = str(estado.get("plan_id") or "")
    tarea = str(estado.get("tarea_actual") or "")
    comandos = _comandos(spec, plan, tarea)
    filas: list[dict] = []
    for fase, estado_fase in nodos:
        skill, plantilla = DATOS.get(fase, (None, None))
        relativa = None
        if plantilla:
            relativa = plantilla.format(spec=spec or "SPEC-001",
                                        plan=plan or "PLAN-001")
        artefacto = relativa if relativa and (raiz / relativa).exists() else None
        filas.append({
            "fase": fase,
            "estado": estado_fase,
            "skill": skill,
            "artefacto": artefacto,
            "comando": comandos.get(fase),
        })
    return filas
