"""Comandos `toolkit validate` — RF-18 (§48)."""

from __future__ import annotations

import pathlib

from cli.commands.context import _localizar
from cli.commands.specify import _cargar_spec
from core.journal import historial
from core.validate import ValidateError, validar
from state import store


def _raiz(args):
    if getattr(args, "root", None):
        return store.descubrir_raiz(pathlib.Path(args.root))
    return store.descubrir_raiz()


def despachar(args) -> int:
    if not args.texto:
        print("⛔ indique el TASK-ID")
        return 1
    raiz = _raiz(args)
    try:
        plan, tarea = _localizar(raiz, args.texto)
        spec = _cargar_spec(raiz, plan.spec_id)
        reporte = validar(raiz, tarea, plan, spec,
                          historial(raiz, plan.plan_id),
                          nota=args.nota or "")
        print(reporte["resumen"])
        return 0 if reporte["veredicto"] == "VALIDADO" else 1
    except (ValidateError, store.StoreError) as error:
        print(f"⛔ {error}")
        return 1
    return 0
