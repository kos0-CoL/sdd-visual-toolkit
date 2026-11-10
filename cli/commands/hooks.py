"""Comandos `toolkit hooks` — RF-42 (§47).

Muestra los hooks configurados por evento y cómo agregarlos.
Solo lectura: no ejecuta nada.
"""

from __future__ import annotations

import pathlib

from core.hooks import EVENTOS, listar
from state import store


def _raiz(args):
    if getattr(args, "root", None):
        return store.descubrir_raiz(pathlib.Path(args.root))
    return store.descubrir_raiz()


def despachar(args) -> int:
    raiz = _raiz(args)
    try:
        visto = listar(raiz)
    except store.StoreError as error:
        print(f"⛔ {error}")
        return 1
    print("🪝 Hooks por evento (`.specify/hooks/<evento>/` ejecutable):")
    hay = False
    for evento in EVENTOS:
        hooks = visto[evento]
        print("%s (%d):" % (evento, len(hooks)))
        for h in hooks:
            hay = True
            marca = "▶ ejecutable" if h["ejecutable"] else "○ sin +x (se omite)"
            print("   • %s — %s" % (h["nombre"], marca))
        if not hooks:
            print("   (sin hooks)")
    if not hay:
        print("Agregue un script ejecutable en `.specify/hooks/<evento>/`;")
        print("recibe SDD_EVENTO, SDD_PLAN, SDD_TAREA, SDD_RESULTADO, "
              "SDD_SUGERENCIA, SDD_ROOT.")
        print("Un hook que falla se declara y se registra, no bloquea (§47).")
    return 0
