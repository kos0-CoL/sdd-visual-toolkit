"""Comandos `toolkit checkpoint` — RF-12 (§13.4, §35)."""

from __future__ import annotations

import pathlib

from core.checkpoints import CheckpointError, cargar, formatear, listar
from state import store


def _raiz(args):
    if getattr(args, "root", None):
        return store.descubrir_raiz(pathlib.Path(args.root))
    return store.descubrir_raiz()


def despachar(args) -> int:
    raiz = _raiz(args)
    try:
        if args.show:
            punto = cargar(raiz, args.show)
            if punto is None:
                print(f"📭 Sin checkpoint para {args.show}: "
                      "la tarea no se completó todavía.")
                return 0
            print(formatear(punto))
            return 0
        if args.list is not None:
            puntos = listar(raiz, args.list)
            if not puntos:
                print(f"📭 Sin checkpoints en {args.list} todavía.")
                return 0
            for p in puntos:
                marca = "✅" if p.get("pruebas_ok") else "❌"
                print(f"{marca} {p['tarea']} ({p.get('fecha')}) → "
                      f"siguiente: {p.get('proxima') or '—'}")
            return 0
        print("⛔ indique el TASK-ID con --show o el PLAN-ID con --list")
        return 1
    except (CheckpointError, store.StoreError) as error:
        print(f"⛔ {error}")
        return 1
    return 0
