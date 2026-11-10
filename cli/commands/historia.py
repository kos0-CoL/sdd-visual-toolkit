"""Comandos `toolkit historia` — RF-30 (§44.30)."""

from __future__ import annotations

import pathlib

from cli.commands.context import _localizar
from core.history import relato
from core.journal import historial
from state import store


def _raiz(args):
    if getattr(args, "root", None):
        return store.descubrir_raiz(pathlib.Path(args.root))
    return store.descubrir_raiz()


def despachar(args) -> int:
    raiz = _raiz(args)
    try:
        if not args.texto:
            print("⛔ indique el TASK-ID")
            return 1
        plan, _tarea = _localizar(raiz, args.texto)
        print(relato(historial(raiz, plan.plan_id), args.texto))
    except store.StoreError as error:
        print(f"⛔ {error}")
        return 1
    return 0
