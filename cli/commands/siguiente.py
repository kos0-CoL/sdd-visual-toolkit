"""Comandos `toolkit siguiente` — RF-35 (§26).

Píldoras de navegación: lee tablero/árbol reales y propone la
siguiente fase, retorno y revisión como comandos CLI ejecutables.
Solo lectura: mantiene el estado y jamás auto-ejecuta una fase que
requiere aprobación humana.
"""

from __future__ import annotations

import pathlib

from cli.commands import plan as mod_plan
from cli.commands import tablero as mod_tablero
from core.navigation import render, sugerir
from state import store


def _raiz(args):
    if getattr(args, "root", None):
        return store.descubrir_raiz(pathlib.Path(args.root))
    return store.descubrir_raiz()


def despachar(args) -> int:
    raiz = _raiz(args)
    try:
        estado = mod_tablero.recopilar(raiz)
        # Plan vigente para píldoras con PLAN-ID real (§26: comandos
        # equivalentes, no decorativos).
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
        print(render(sugerir(estado)))
    except store.StoreError as error:
        print(f"⛔ {error}")
        return 1
    return 0
