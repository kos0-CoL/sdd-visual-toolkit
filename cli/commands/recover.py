"""Comandos `toolkit recover` — RF-13 (§13.6)."""

from __future__ import annotations

import pathlib

from cli.commands import plan as mod_plan
from cli.commands import specify as mod_specify
from cli.commands import tasks as mod_tasks
from core.journal import JournalError, leer_estado
from core.recover import RecoverError, diagnosticar, formatear
from core.tasks import TasksError
from state import store


def _raiz(args):
    if getattr(args, "root", None):
        return store.descubrir_raiz(pathlib.Path(args.root))
    return store.descubrir_raiz()


def despachar(args) -> int:
    raiz = _raiz(args)
    try:
        plan_id = args.texto
        if plan_id is None:
            estado = leer_estado(raiz)
            if estado is None:
                print("📭 Sin journal: no hay ejecución que recuperar.")
                return 0
            plan_id = estado["plan_id"]
        _info, tareas = mod_tasks._cargar_tareas(raiz, plan_id)
        try:
            plan = mod_plan._cargar_plan(raiz, plan_id)
            spec = mod_specify._cargar_spec(raiz, plan.spec_id)
            spec_d = {"spec_id": spec.spec_id, "funcionales": spec.funcionales}
        except (store.StoreError, KeyError, AttributeError):
            spec_d = None
        print(formatear(diagnosticar(raiz, plan_id, spec_d, tareas)))
    except (RecoverError, JournalError, TasksError, store.StoreError) as error:
        print(f"⛔ {error}")
        return 1
    return 0
