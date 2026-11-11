"""Comandos `toolkit export` — RF-38 (§29-30, §32).

Foto JSON máquina del mismo estado central que usan tablero, árbol
y navegación. La consumen adaptadores externos (IDE, MCP) sin
duplicar estado. Solo lectura.
"""

from __future__ import annotations

import pathlib

from cli.commands import arbol as mod_arbol
from cli.commands import plan as mod_plan
from cli.commands import tablero as mod_tablero
from core import agent_commands
from core.export import documento, render
from core.flujo import flujo as construir_flujo
from core.navigation import sugerir
from state import store


def _raiz(args):
    if getattr(args, "root", None):
        return store.descubrir_raiz(pathlib.Path(args.root))
    return store.descubrir_raiz()


def despachar(args) -> int:
    raiz = _raiz(args)
    try:
        estado = mod_tablero.recopilar(raiz)
        spec_id = estado.get("spec_id")
        if spec_id and "PLAN-" not in str(estado.get("proxima") or ""):
            try:
                planes = [(pid, info)
                          for pid, info in mod_plan._indice(raiz).items()
                          if info.get("spec_id") == spec_id]
                if planes:
                    estado["plan_id"] = sorted(p for p, _i in planes)[-1]
            except Exception:  # noqa: BLE001 — sin índice, se declara
                pass
        nodos, transiciones = mod_arbol.nodos(raiz)
        print(render(documento(estado, nodos, transiciones,
                               sugerir(estado),
                               construir_flujo(raiz, nodos, estado),
                               agent_commands.rutas_muertas(raiz))))
    except store.StoreError as error:
        print(f"⛔ {error}")
        return 1
    return 0
