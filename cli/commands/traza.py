"""Comandos `toolkit traza` — RF-29 (§39)."""

from __future__ import annotations

import pathlib

from cli.commands import plan as mod_plan
from cli.commands import specify as mod_specify
from cli.commands import tasks as mod_tasks
from core.journal import historial
from core.plan import PlanError
from core.spec import SpecError
from core.tasks import TasksError
from core.trace import matriz
from state import store


def _raiz(args):
    if getattr(args, "root", None):
        return store.descubrir_raiz(pathlib.Path(args.root))
    return store.descubrir_raiz()


def despachar(args) -> int:
    raiz = _raiz(args)
    try:
        if not args.texto:
            print("⛔ indique el SPEC-ID")
            return 1
        spec = mod_specify._cargar_spec(raiz, args.texto)
        pares = []
        for plan_id, info in mod_plan._indice(raiz).items():
            if info.get("spec_id") == spec.spec_id:
                plan = mod_plan._cargar_plan(raiz, plan_id)
                _info, tareas = mod_tasks._cargar_tareas(raiz, plan_id)
                pares.append((plan, tareas))
        print(matriz(spec, pares, historial(raiz), raiz))
    except (PlanError, SpecError, TasksError, store.StoreError) as error:
        print(f"⛔ {error}")
        return 1
    return 0
