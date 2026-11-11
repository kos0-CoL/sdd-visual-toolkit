"""Comandos `toolkit status` — RF-36 (§31).

Consulta de estado en una sola llamada: panel general (RF-31) +
navegación por píldoras (RF-35). Solo lectura, mismo estado central
que la interfaz visual.
"""

from __future__ import annotations

import pathlib

from cli.commands import plan as mod_plan
from cli.commands import tablero as mod_tablero
from core import agent_commands
from core.board import render as render_tablero
from core.navigation import render as render_nav
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
        print(render_tablero(estado))
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
        print()
        print(render_nav(sugerir(estado)))
        _avisar_skills(raiz)
    except store.StoreError as error:
        print(f"⛔ {error}")
        return 1
    return 0


def _avisar_skills(raiz) -> None:
    """Aviso al final, no una línea por archivo: si el toolkit se movió, las
    skills ejecutan una ruta muerta y el agente falla sin explicación."""
    muertas = agent_commands.rutas_muertas(raiz)
    if not muertas:
        return
    total = sum(muertas.values())
    print()
    print(f"⚠️ COMANDOS DE BARRA DESACTUALIZADOS: {total} archivo(s) apuntan "
          "a una ruta que ya no existe")
    for ruta, cuantos in sorted(muertas.items()):
        print(f"   {cuantos} archivo(s) → {ruta}")
    print("   regenere con `toolkit comandos`; `toolkit comandos --verificar` "
          "lo detalla")
