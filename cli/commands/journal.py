"""Comandos `toolkit journal` — RF-11 (§13)."""

from __future__ import annotations

import json
import pathlib

from core.journal import JournalError, historial, leer_estado, resumen
from state import store


def _raiz(args):
    if getattr(args, "root", None):
        return store.descubrir_raiz(pathlib.Path(args.root))
    return store.descubrir_raiz()


def despachar(args) -> int:
    raiz = _raiz(args)
    try:
        if args.state:
            estado = leer_estado(raiz)
            if estado is None:
                print("Sin estado registrado todavía (§13: nada ejecutado).")
                return 0
            print(json.dumps(estado, ensure_ascii=False, indent=2))
            return 0
        if args.history:
            for e in historial(raiz, args.history, ultimos=args.n or 0):
                print(f"{e.get('fecha')} [{e.get('evento')}] {e.get('tarea')}"
                      + (f" — {e.get('nota')}" if e.get("nota") else ""))
            return 0
        if not args.texto:
            print("⛔ indique el PLAN-ID o use --history/--state")
            return 1
        print(resumen(raiz, args.texto))
    except (JournalError, store.StoreError) as error:
        print(f"⛔ {error}")
        return 1
    return 0
