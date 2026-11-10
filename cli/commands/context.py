"""Comandos `toolkit context` — RF-14 (§14)."""

from __future__ import annotations

import pathlib

from cli.commands import clarify as mod_clarify
from cli.commands import plan as mod_plan
from cli.commands import specify as mod_specify
from cli.commands import tasks as mod_tasks
from core import context as ctx
from core.journal import historial
from core.pin import decisiones_aprobadas, generar_pin
from core.recover import diagnosticar, formatear
from state import store


def _raiz(args):
    if getattr(args, "root", None):
        return store.descubrir_raiz(pathlib.Path(args.root))
    return store.descubrir_raiz()


def _localizar(raiz, task_id: str):
    for plan_id in mod_plan._indice(raiz):
        _info, tareas = mod_tasks._cargar_tareas(raiz, plan_id)
        for t in tareas:
            if t.id == task_id:
                plan = mod_plan._cargar_plan(raiz, plan_id)
                return plan, t
    raise ctx.ContextError(f"tarea inexistente: {task_id}")


def despachar(args) -> int:
    if args.modo not in ctx.MODOS:
        print(f"⛔ modo inválido {args.modo!r}; valores: {', '.join(ctx.MODOS)}")
        return 1
    if not args.texto:
        print("⛔ indique el TASK-ID")
        return 1
    raiz = _raiz(args)
    try:
        plan, tarea = _localizar(raiz, args.texto)
        spec = mod_specify._cargar_spec(raiz, plan.spec_id)
        if args.modo == "requerimientos":
            ruta = raiz / store.SPECIFY_DIR / store.REQUERIMIENTOS_FILE
            reqs = store.leer_json(ruta) if ruta.exists() else []
            from core.requirements import Requerimiento  # noqa: PLC0415
            print(ctx.requerimientos(
                spec, [Requerimiento.from_dict(d) for d in reqs]))
        elif args.modo == "arquitectura":
            print(ctx.arquitectura(plan))
        elif args.modo == "implementacion":
            _preg, hist = mod_clarify._preguntas_de(raiz, spec.spec_id)
            pin = generar_pin(plan, spec, tarea, decisiones_aprobadas(hist))
            print(ctx.implementacion(tarea, pin, raiz))
        elif args.modo == "pruebas":
            print(ctx.pruebas(tarea, historial(raiz, plan.plan_id)))
        else:
            _info, tareas = mod_tasks._cargar_tareas(raiz, plan.plan_id)
            spec_d = {"funcionales": spec.funcionales}
            print(ctx.recuperacion(formatear(
                diagnosticar(raiz, plan.plan_id, spec_d, tareas))))
    except (ctx.ContextError, store.StoreError) as error:
        print(f"⛔ {error}")
        return 1
    return 0
