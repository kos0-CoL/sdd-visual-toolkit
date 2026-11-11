"""Comandos `toolkit restricciones` — RF-33 (§23).

Panel lateral con las restricciones de la SPEC activa y, con TASK-ID,
qué archivos de la tarea se están verificando contra las fronteras.
Todo sale de SPEC, plan y clarify reales.
"""

from __future__ import annotations

import pathlib

from cli.commands import clarify as mod_clarify
from cli.commands import context as mod_context
from cli.commands import plan as mod_plan
from cli.commands import specify as mod_specify
from cli.commands import tablero as mod_tablero
from cli.commands import tasks as mod_tasks
from core.context import ContextError
from core.plan import PlanError
from core.restrictions import clasificar, render
from core.spec import SpecError
from state import store


def _raiz(args):
    if getattr(args, "root", None):
        return store.descubrir_raiz(pathlib.Path(args.root))
    return store.descubrir_raiz()


def _decisiones(raiz, spec_id: str) -> list:
    try:
        preguntas, _hist = mod_clarify._preguntas_de(raiz, spec_id)
    except Exception:  # noqa: BLE001 — sin clarify, se declara
        return []
    return ["%s → %s" % (p.id, p.respuesta) for p in preguntas
            if p.respuesta and p.estado == "respondida"]


def _panel_spec(raiz, spec) -> tuple[str, list]:
    try:
        planes = [(pid, info)
                  for pid, info in mod_plan._indice(raiz).items()
                  if info.get("spec_id") == spec.spec_id]
    except Exception:  # noqa: BLE001 — sin índice, se declara
        planes = []
    modificables, intactos, reutilizables = [], [], []
    if planes:
        plan = mod_plan._cargar_plan(raiz, sorted(p for p, _i in planes)[-1])
        modificables = list(plan.modificables) + list(plan.creables)
        intactos = list(plan.intactos)
        reutilizables = list(plan.reutilizables)
    secciones = [
        ("⛔", "Fuera de alcance", list(spec.fuera_alcance)),
        ("🔒", "Archivos protegidos (intactos)",
         intactos or (["(sin plan: sin fronteras)"] if not planes else [])),
        ("✏️", "Archivos modificables",
         modificables or (["(sin plan: sin fronteras)"]
                          if not planes else [])),
        ("🔌", "Interfaces protegidas (reutilizar intactas)",
         reutilizables or (["(sin plan: sin fronteras)"]
                           if not planes else [])),
        ("📏", "Reglas de negocio", list(spec.reglas)),
        ("⚙️", "Restricciones técnicas", list(spec.restricciones)),
        ("✅", "Decisiones aprobadas en clarify",
         _decisiones(raiz, spec.spec_id)),
    ]
    return ("Panel de restricciones %s" % spec.spec_id, secciones)


def despachar(args) -> int:
    raiz = _raiz(args)
    try:
        texto = (args.texto or "").strip()
        tarea_ctx = None
        if texto.startswith("TASK-"):
            plan, tarea = mod_context._localizar(raiz, texto)
            spec = mod_specify._cargar_spec(raiz, plan.spec_id)
            _titulo, secciones = _panel_spec(raiz, spec)
            plan_obj = mod_plan._cargar_plan(raiz, plan.plan_id)
            modifs = list(plan_obj.modificables) + list(plan_obj.creables)
            tarea_ctx = {
                "id": tarea.id,
                "archivos": [(a, clasificar(a, modifs,
                                            list(plan_obj.intactos)))
                              for a in tarea.archivos]}
            titulo = "Panel de restricciones %s — %s" % (spec.spec_id,
                                                         tarea.id)
        else:
            spec_id = texto or mod_tablero.recopilar(raiz).get("spec_id")
            if not spec_id:
                print("⛔ sin SPEC todavía; genere una con la pipeline")
                return 1
            spec = mod_specify._cargar_spec(raiz, spec_id)
            titulo, secciones = _panel_spec(raiz, spec)
        print(render(titulo, secciones, tarea_ctx))
    except (ContextError, PlanError, SpecError, store.StoreError) as error:
        print(f"⛔ {error}")
        return 1
    return 0
