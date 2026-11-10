"""Comandos `toolkit rollback` — RF-16 (§16)."""

from __future__ import annotations

import pathlib

from core.journal import registrar
from core.rollback import RollbackError, listar, restaurar
from state import store


def _raiz(args):
    if getattr(args, "root", None):
        return store.descubrir_raiz(pathlib.Path(args.root))
    return store.descubrir_raiz()


def despachar(args) -> int:
    raiz = _raiz(args)
    try:
        if args.list:
            tomas = listar(raiz, args.list)
            if not tomas:
                print(f"📭 Sin snapshots para {args.list}.")
                return 0
            for n in tomas:
                print(f"snapshot {args.list}/{n}")
            return 0
        if args.restore:
            carpeta = restaurar(raiz, args.restore, args.n)
            try:
                plan_id = _plan_de(raiz, args.restore)
                registrar(raiz, plan_id,
                          {"tarea": args.restore, "evento": "rollback",
                           "nota": f"restauración manual desde {carpeta.name}"})
            except store.StoreError:
                pass
            print(f"↩ {args.restore} restaurada desde snapshot {carpeta.name} "
                  "(solo sus archivos; lo ajeno intacto, §16).")
            return 0
        print("⛔ indique el TASK-ID con --list o --restore")
        return 1
    except (RollbackError, store.StoreError) as error:
        print(f"⛔ {error}")
        return 1
    return 0


def _plan_de(raiz, task_id: str) -> str:
    from cli.commands import plan as mod_plan  # noqa: PLC0415
    from cli.commands import tasks as mod_tasks  # noqa: PLC0415

    for plan_id in mod_plan._indice(raiz):
        _info, tareas = mod_tasks._cargar_tareas(raiz, plan_id)
        if any(t.id == task_id for t in tareas):
            return plan_id
    raise RollbackError(f"ningún plan contiene {task_id}")
