"""Comandos `toolkit reporte` — RF-26 (§18.4)."""

from __future__ import annotations

import pathlib

from cli.commands.context import _localizar
from core.report import informe, tabla
from state import store


def _raiz(args):
    if getattr(args, "root", None):
        return store.descubrir_raiz(pathlib.Path(args.root))
    return store.descubrir_raiz()


def despachar(args) -> int:
    raiz = _raiz(args)
    try:
        if args.history:
            print(tabla(raiz, args.history, ultimas=args.n or 0))
            return 0
        if not args.texto:
            print("⛔ indique el TASK-ID o use --history PLAN-ID")
            return 1
        plan, _tarea = _localizar(raiz, args.texto)
        print(informe(raiz, plan.plan_id, args.texto))
    except store.StoreError as error:
        print(f"⛔ {error}")
        return 1
    return 0
