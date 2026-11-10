"""Comandos `toolkit ast` — RF-17 (§17)."""

from __future__ import annotations

import pathlib

from cli.commands.context import _localizar
from cli.commands.pin import asegurar_baseline
from core.astcheck import AstCheckError, comparar
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
        _plan, tarea = _localizar(raiz, args.texto)
        baseline, parcial = asegurar_baseline(raiz, tarea)
        resultado = comparar(tarea, baseline, raiz)
        print(resultado["resumen"])
        if parcial:
            print("⚠️ sin línea base previa: verificación parcial.")
        return 0 if resultado["veredicto"] != "RECHAZADO" else 1
    except (AstCheckError, store.StoreError) as error:
        print(f"⛔ {error}")
        return 1
    return 0
